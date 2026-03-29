# Bedrock CLI

A Claude Code-style CLI powered by Amazon Bedrock with single-agent and parallel multi-agent modes.

## Setup

```bash
pip install -r requirements.txt
export AWS_REGION=us-east-1   # or your region
```

Ensure your AWS credentials have `bedrock:InvokeModel` permission.

## Run

```bash
python main.py
```

## Usage

| Input | Behaviour |
|---|---|
| Any text | Single-agent mode — streams a response, can call tools |
| `/multi <task>` | Multi-agent mode — orchestrator fans out to parallel specialist agents |
| `/clear` | Reset conversation history |
| `/history` | Show message count in current context |
| `/exit` | Quit |

## Configuration

Edit `config.py` to change models per agent:

```python
AGENT_MODELS = {
    "orchestrator": "anthropic.claude-3-5-sonnet-20241022-v2:0",
    "architect":    "anthropic.claude-3-5-sonnet-20241022-v2:0",
    "coder":        "anthropic.claude-3-5-sonnet-20241022-v2:0",
    "tester":       "anthropic.claude-3-haiku-20240307-v1:0",
    "reviewer":     "anthropic.claude-3-5-sonnet-20241022-v2:0",
}
```

## Project layout

```
bedrock-cli/
├── main.py              Entry point and REPL
├── agent.py             Single-agent streaming loop
├── sub_agent.py         Async sub-agent for parallel execution
├── orchestrator.py      Multi-agent coordination
├── tools.py             Tool schemas (Bedrock Converse API format)
├── executor.py          Tool implementations
├── config.py            Model assignments and constants
├── system_prompt.txt    Single-agent system prompt
├── requirements.txt
├── prompts/             Per-agent system prompts
│   ├── orchestrator.txt
│   ├── architect.txt
│   ├── coder.txt
│   ├── tester.txt
│   └── reviewer.txt
└── docs/                One markdown doc per source file
    ├── architecture.md
    ├── config.md
    ├── agent.md
    ├── sub_agent.md
    ├── orchestrator.md
    ├── executor.md
    ├── tools.md
    └── main.md
```

## Adding a new tool

1. Add a `toolSpec` entry to `tools.py`
2. Add a handler branch to `executor.py`
3. Add an icon to `TOOL_ICONS` in `main.py`

## Adding a new agent

1. Add to `AGENT_MODELS` in `config.py`
2. Add a colour to `AGENT_COLORS` in `main.py`
3. Create `prompts/<agent_name>.txt`
