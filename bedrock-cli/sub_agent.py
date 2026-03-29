import asyncio
import json
import os
from typing import AsyncGenerator

import boto3

from config import MAX_TOKENS, TEMPERATURE, model_for
from executor import execute_tool
from tools import TOOLS


def _load_prompt(agent_name: str) -> str:
    path = os.path.join(os.path.dirname(__file__), "prompts", f"{agent_name}.txt")
    with open(path) as f:
        return f.read().format(cwd=os.getcwd())


def _invoke_bedrock_stream(messages: list, system: list, model_id: str) -> dict:
    client = boto3.client("bedrock-runtime", region_name=os.environ.get("AWS_REGION", "us-east-1"))
    return client.converse_stream(
        modelId=model_id,
        system=system,
        messages=messages,
        toolConfig={"tools": TOOLS},
        inferenceConfig={"maxTokens": MAX_TOKENS, "temperature": TEMPERATURE},
    )


async def run_sub_agent(agent_name: str, task: str, context: str = "") -> AsyncGenerator[dict, None]:
    model_id = model_for(agent_name)
    system = [{"text": _load_prompt(agent_name)}]
    user_content = f"{context}\n\nYour task:\n{task}" if context else task
    history = [{"role": "user", "content": [{"text": user_content}]}]
    full_response = ""
    loop = asyncio.get_event_loop()

    while True:
        response = await loop.run_in_executor(
            None, lambda h=history, s=system: _invoke_bedrock_stream(h, s, model_id)
        )

        accumulated_text = ""
        tool_uses = {}
        current_tool_id = None
        stop_reason = None

        for event in response["stream"]:
            if "contentBlockDelta" in event:
                delta = event["contentBlockDelta"]["delta"]
                if "text" in delta:
                    accumulated_text += delta["text"]
                    full_response += delta["text"]
                    yield {"type": "text", "agent": agent_name, "text": delta["text"]}
                elif "toolUse" in delta and current_tool_id:
                    tool_uses[current_tool_id]["input_str"] += delta["toolUse"].get("input", "")

            elif "contentBlockStart" in event:
                block = event["contentBlockStart"]["start"]
                if "toolUse" in block:
                    current_tool_id = block["toolUse"]["toolUseId"]
                    tool_uses[current_tool_id] = {
                        "name": block["toolUse"]["name"],
                        "input_str": "",
                    }

            elif "messageStop" in event:
                stop_reason = event["messageStop"]["stopReason"]

        content_blocks = []
        if accumulated_text:
            content_blocks.append({"text": accumulated_text})
        for tool_id, td in tool_uses.items():
            content_blocks.append({
                "toolUse": {
                    "toolUseId": tool_id,
                    "name": td["name"],
                    "input": json.loads(td["input_str"] or "{}"),
                }
            })
        history.append({"role": "assistant", "content": content_blocks})

        if stop_reason == "end_turn" or not tool_uses:
            yield {"type": "done", "agent": agent_name, "model": model_id, "result": full_response}
            return

        tool_results = []
        for tool_id, td in tool_uses.items():
            name = td["name"]
            inputs = json.loads(td["input_str"] or "{}")
            yield {"type": "tool_start", "agent": agent_name, "name": name, "input": inputs}
            result = await loop.run_in_executor(None, lambda n=name, i=inputs: execute_tool(n, i))
            yield {"type": "tool_result", "agent": agent_name, "name": name, "result": result}
            tool_results.append({"toolUseId": tool_id, "content": [{"text": result}]})

        history.append({
            "role": "user",
            "content": [{"toolResult": r} for r in tool_results],
        })
