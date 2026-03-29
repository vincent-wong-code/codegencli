import json
import os
from typing import Generator

import boto3

from config import MODEL_ID, MAX_TOKENS, TEMPERATURE, SYSTEM_PROMPT_FILE
from executor import execute_tool
from tools import TOOLS


def load_system_prompt() -> str:
    path = os.path.join(os.path.dirname(__file__), SYSTEM_PROMPT_FILE)
    with open(path) as f:
        return f.read().format(cwd=os.getcwd())


def run_agent_streaming(user_message: str, history: list) -> Generator[dict, None, list]:
    client = boto3.client("bedrock-runtime", region_name=os.environ.get("AWS_REGION", "us-east-1"))
    system = [{"text": load_system_prompt()}]
    history.append({"role": "user", "content": [{"text": user_message}]})

    while True:
        stream = client.converse_stream(
            modelId=MODEL_ID,
            system=system,
            messages=history,
            toolConfig={"tools": TOOLS},
            inferenceConfig={"maxTokens": MAX_TOKENS, "temperature": TEMPERATURE},
        )

        accumulated_text = ""
        tool_uses = {}
        current_tool_id = None
        stop_reason = None

        for event in stream["stream"]:
            if "contentBlockDelta" in event:
                delta = event["contentBlockDelta"]["delta"]
                if "text" in delta:
                    accumulated_text += delta["text"]
                    yield {"type": "text", "text": delta["text"]}
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
            yield {"type": "done"}
            return history

        tool_results = []
        for tool_id, td in tool_uses.items():
            name = td["name"]
            inputs = json.loads(td["input_str"] or "{}")
            yield {"type": "tool_start", "name": name, "input": inputs}
            result = execute_tool(name, inputs)
            yield {"type": "tool_result", "name": name, "result": result}
            tool_results.append({"toolUseId": tool_id, "content": [{"text": result}]})

        history.append({
            "role": "user",
            "content": [{"toolResult": r} for r in tool_results],
        })
