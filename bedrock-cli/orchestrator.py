import asyncio
import json
import os
import re
from typing import AsyncGenerator

import boto3

from config import MAX_TOKENS, model_for
from sub_agent import run_sub_agent


def _load_orchestrator_prompt() -> str:
    path = os.path.join(os.path.dirname(__file__), "prompts", "orchestrator.txt")
    with open(path) as f:
        return f.read().format(cwd=os.getcwd())


def _plan_task(user_task: str) -> dict:
    client = boto3.client("bedrock-runtime", region_name=os.environ.get("AWS_REGION", "us-east-1"))
    response = client.converse(
        modelId=model_for("orchestrator"),
        system=[{"text": _load_orchestrator_prompt()}],
        messages=[{"role": "user", "content": [{"text": user_task}]}],
        inferenceConfig={"maxTokens": MAX_TOKENS, "temperature": 0},
    )
    raw = response["output"]["message"]["content"][0]["text"]
    raw = re.sub(r"```json|```", "", raw).strip()
    return json.loads(raw)


async def _merge_results(plan: dict, results: dict, user_task: str) -> str:
    client = boto3.client("bedrock-runtime", region_name=os.environ.get("AWS_REGION", "us-east-1"))
    parts = [f"Original task: {user_task}\n\nPlan summary: {plan['summary']}\n"]
    for agent_name, result in results.items():
        parts.append(f"--- {agent_name.upper()} OUTPUT ---\n{result}\n")
    merge_prompt = "\n".join(parts) + (
        "\nSynthesize the above agent outputs into a single, clear, actionable response for the user. "
        "Highlight key decisions, show important code, and summarize what was done."
    )
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(None, lambda: client.converse(
        modelId=model_for("orchestrator"),
        system=[{"text": "You are a helpful assistant that synthesizes multi-agent outputs clearly."}],
        messages=[{"role": "user", "content": [{"text": merge_prompt}]}],
        inferenceConfig={"maxTokens": 4096, "temperature": 0},
    ))
    return response["output"]["message"]["content"][0]["text"]


async def run_parallel_agents(user_task: str) -> AsyncGenerator[dict, None]:
    yield {"type": "status", "text": "Planning task decomposition..."}
    plan = _plan_task(user_task)
    yield {"type": "plan", "plan": plan}

    tasks_spec = plan.get("tasks", [])
    if not tasks_spec:
        yield {"type": "error", "text": "Orchestrator returned no tasks."}
        return

    results = {}
    queue = asyncio.Queue()
    active = len(tasks_spec)

    async def drain(agent_name: str, task: str):
        nonlocal active
        async for event in run_sub_agent(agent_name, task):
            await queue.put(event)
            if event["type"] == "done":
                results[agent_name] = event["result"]
        active -= 1
        if active == 0:
            await queue.put(None)

    agent_runners = [
        asyncio.create_task(drain(t["agent"], t["task"]))
        for t in tasks_spec
    ]

    while True:
        event = await queue.get()
        if event is None:
            break
        yield event

    await asyncio.gather(*agent_runners)

    yield {"type": "status", "text": "Merging agent outputs..."}
    merged = await _merge_results(plan, results, user_task)
    yield {"type": "merged", "text": merged}
