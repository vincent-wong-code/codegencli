# Bedrock CLI — Project Handoff Prompt

Paste this entire file as your first message in a new chat to continue this project.

---

I'm building a Claude Code-style CLI in Python that runs on Amazon Bedrock. The project is complete and working. I need your help continuing it.

## What it does

- A REPL CLI that lets you talk to LLMs on Amazon Bedrock with tool use (bash, file read/write, list files)
- Single-agent mode: just type a prompt, the agent streams a response and can call tools in a loop
- Multi-agent mode (`/multi <task>`): an orchestrator LLM decomposes the task, fans out to specialist sub-agents (architect, coder, tester, reviewer) running in parallel via `asyncio`, then merges results
- Each agent uses a different Bedrock model, configured in `config.py`
- All code is comment-free; explanations live in `docs/*.md`

## Project layout

```
bedrock-cli/
├── main.py              REPL loop, rendering, command dispatch
├── agent.py             Single-agent streaming loop (sync generator)
├── sub_agent.py         Async sub-agent used by the orchestrator
├── orchestrator.py      Multi-agent fan-out, planning, result merge
├── tools.py             Tool schemas in Bedrock Converse API format
├── executor.py          Tool implementations (bash, read_file, write_file, list_files)
├── config.py            AGENT_MODELS map + model_for() + tuning constants
├── system_prompt.txt    System prompt for single-agent mode (supports {cwd})
├── prompts/
│   ├── orchestrator.txt
│   ├── architect.txt
│   ├── coder.txt
│   ├── tester.txt
│   └── reviewer.txt
└── docs/
    ├── architecture.md
    ├── config.md
    ├── agent.md
    ├── sub_agent.md
    ├── orchestrator.md
    ├── executor.md
    ├── tools.md
    └── main.md
```

## Complete source code

### config.py
```python
import os

AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
SYSTEM_PROMPT_FILE = "system_prompt.txt"
MAX_TOKENS = 4096
TEMPERATURE = 0

DEFAULT_MODEL = "anthropic.claude-3-5-sonnet-20241022-v2:0"

AGENT_MODELS = {
    "orchestrator": "anthropic.claude-3-5-sonnet-20241022-v2:0",
    "architect":    "anthropic.claude-3-5-sonnet-20241022-v2:0",
    "coder":        "anthropic.claude-3-5-sonnet-20241022-v2:0",
    "tester":       "anthropic.claude-3-haiku-20240307-v1:0",
    "reviewer":     "anthropic.claude-3-5-sonnet-20241022-v2:0",
}


def model_for(agent_name: str) -> str:
    return AGENT_MODELS.get(agent_name, DEFAULT_MODEL)
```

### tools.py
```python
TOOLS = [
    {
        "toolSpec": {
            "name": "bash",
            "description": "Run a shell command and return stdout/stderr",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "command": {"type": "string"},
                        "timeout": {"type": "integer", "default": 30}
                    },
                    "required": ["command"]
                }
            }
        }
    },
    {
        "toolSpec": {
            "name": "read_file",
            "description": "Read a file's contents",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"}
                    },
                    "required": ["path"]
                }
            }
        }
    },
    {
        "toolSpec": {
            "name": "write_file",
            "description": "Write or overwrite a file",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "content": {"type": "string"}
                    },
                    "required": ["path", "content"]
                }
            }
        }
    },
    {
        "toolSpec": {
            "name": "list_files",
            "description": "List files in a directory",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "default": "."},
                        "pattern": {"type": "string"}
                    }
                }
            }
        }
    }
]
```

### executor.py
```python
import subprocess
import os
import glob


def execute_tool(name: str, inputs: dict) -> str:
    try:
        if name == "bash":
            result = subprocess.run(
                inputs["command"],
                shell=True,
                capture_output=True,
                text=True,
                timeout=inputs.get("timeout", 30),
            )
            return (result.stdout + result.stderr)[:8000] or "(no output)"

        if name == "read_file":
            path = os.path.expanduser(inputs["path"])
            with open(path) as f:
                return f.read()[:20000]

        if name == "write_file":
            path = os.path.expanduser(inputs["path"])
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            with open(path, "w") as f:
                f.write(inputs["content"])
            return f"Written {len(inputs['content'])} bytes to {path}"

        if name == "list_files":
            path = inputs.get("path", ".")
            pattern = inputs.get("pattern", "*")
            files = glob.glob(os.path.join(path, "**", pattern), recursive=True)
            return "\n".join(files[:100])

    except Exception as e:
        return f"ERROR: {e}"
```

### agent.py
```python
import json
import os
from typing import Generator

import boto3

from config import MAX_TOKENS, TEMPERATURE, SYSTEM_PROMPT_FILE, DEFAULT_MODEL
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
            modelId=DEFAULT_MODEL,
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
```

### sub_agent.py
```python
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
```

### orchestrator.py
```python
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
```

### main.py
```python
import asyncio
import os

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from agent import run_agent_streaming
from orchestrator import run_parallel_agents

console = Console()
session = PromptSession(history=FileHistory(os.path.expanduser("~/.mybedrockcli_history")))

AGENT_COLORS = {
    "architect": "cyan",
    "coder":     "green",
    "tester":    "yellow",
    "reviewer":  "magenta",
}

TOOL_ICONS = {
    "bash":       "🖥 ",
    "read_file":  "📖",
    "write_file": "✏️ ",
    "list_files": "📂",
}


def agent_tag(name: str) -> str:
    color = AGENT_COLORS.get(name, "white")
    return f"[{color}][{name.upper()}][/{color}]"


async def run_multi(user_input: str):
    console.print()
    async for event in run_parallel_agents(user_input):
        if event["type"] == "status":
            console.print(f"\n[dim]⟳ {event['text']}[/dim]")

        elif event["type"] == "plan":
            plan = event["plan"]
            console.print(f"\n[bold]Plan:[/bold] {plan['summary']}")
            for t in plan["tasks"]:
                color = AGENT_COLORS.get(t["agent"], "white")
                console.print(f"  [{color}]•[/{color}] [{color}]{t['agent']}[/{color}]: {t['task']}")
            console.print()

        elif event["type"] == "text":
            console.print(f"{agent_tag(event['agent'])} ", end="", highlight=False)
            console.print(event["text"], end="", highlight=False)

        elif event["type"] == "tool_start":
            icon = TOOL_ICONS.get(event["name"], "🔧")
            args = ", ".join(f"{k}={repr(v)[:60]}" for k, v in event["input"].items())
            console.print(f"\n  {agent_tag(event['agent'])} {icon} [bold]{event['name']}[/bold]({args})")

        elif event["type"] == "tool_result":
            preview = event["result"].strip()[:200]
            console.print(f"  {agent_tag(event['agent'])} [dim]↳ {preview}[/dim]")

        elif event["type"] == "done":
            model = event.get("model", "")
            model_short = model.split("/")[-1] if "/" in model else model.split(".")[-1]
            console.print(f"\n  {agent_tag(event['agent'])} [dim]✓ done ({model_short})[/dim]\n")

        elif event["type"] == "merged":
            console.print(Panel(
                Markdown(event["text"]),
                title="[bold green]Final merged result[/bold green]",
                border_style="green",
            ))

        elif event["type"] == "error":
            console.print(f"[red]Error: {event['text']}[/red]")

    console.print()


def run_single(user_input: str, history: list) -> list:
    console.print()
    gen = run_agent_streaming(user_input, history)
    try:
        while True:
            event = next(gen)
            if event["type"] == "text":
                console.print(event["text"], end="", highlight=False)
            elif event["type"] == "tool_start":
                icon = TOOL_ICONS.get(event["name"], "🔧")
                args = "  ".join(
                    f"[cyan]{k}[/cyan]=[yellow]{repr(v)[:80]}[/yellow]"
                    for k, v in event["input"].items()
                )
                console.print(f"\n  {icon} [bold]{event['name']}[/bold]  {args}", highlight=False)
            elif event["type"] == "tool_result":
                console.print(f"  [dim]↳ {event['result'].strip()[:300]}[/dim]")
            elif event["type"] == "done":
                break
    except StopIteration as e:
        history = e.value
    console.print("\n")
    return history


def main():
    console.print(Panel.fit(
        "[bold cyan]🤖 My Bedrock CLI[/bold cyan]\n"
        "[dim]Single agent: just type  •  Multi-agent: prefix with [bold]/multi[/bold][/dim]",
    ))
    console.print("[dim]/exit  /clear  /history  /multi <task>[/dim]\n")

    history = []

    while True:
        try:
            user_input = session.prompt("❯ ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Bye![/dim]")
            break

        if not user_input:
            continue
        if user_input in ("/exit", "/quit"):
            break
        if user_input == "/clear":
            history = []
            console.print("[dim]Context cleared.[/dim]\n")
            continue
        if user_input == "/history":
            console.print(f"[dim]{len(history)} messages in context[/dim]\n")
            continue
        if user_input.startswith("/multi "):
            asyncio.run(run_multi(user_input[7:].strip()))
        else:
            history = run_single(user_input, history)


if __name__ == "__main__":
    main()
```

## Design conventions to maintain

- No comments in Python files. All explanations go in `docs/<filename>.md`
- Every new module gets a matching doc file
- New tools: add schema to `tools.py`, handler to `executor.py`, entry to `TOOL_ICONS` in `main.py`
- New agents: add to `AGENT_MODELS` in `config.py`, add colour to `AGENT_COLORS` in `main.py`, create `prompts/<agent_name>.txt`
- All streaming is expressed as typed event dicts — producers yield, consumers render
- Blocking Bedrock/IO calls inside async functions always go through `loop.run_in_executor`

## Dependencies

```
boto3
rich
prompt_toolkit
```

## What I want to work on next

[REPLACE THIS LINE with what you want to build — e.g. "Add a web search tool", "Add memory/persistence", "Package as a pip-installable CLI", "Add a web UI", etc.]
