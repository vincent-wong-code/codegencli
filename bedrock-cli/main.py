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
