# Architecture

## Project layout

```
bedrock-cli/
├── main.py              Entry point, REPL loop, terminal rendering
├── agent.py             Single-agent streaming loop
├── sub_agent.py         Async sub-agent (used by orchestrator)
├── orchestrator.py      Multi-agent fan-out and result synthesis
├── tools.py             Tool schemas (Bedrock Converse API format)
├── executor.py          Tool implementations (bash, file I/O)
├── config.py            Model ID, region, and tuning constants
├── system_prompt.txt    System prompt for single-agent mode
├── prompts/
│   ├── orchestrator.txt Decomposition instructions
│   ├── architect.txt
│   ├── coder.txt
│   ├── tester.txt
│   └── reviewer.txt
└── docs/                One markdown file per source file
```

## Request lifecycle — single agent

```
main.py          agent.py              Bedrock
  │                │                     │
  │ run_single()   │                     │
  │───────────────►│                     │
  │                │ converse_stream()   │
  │                │────────────────────►│
  │                │◄── text deltas ─────│
  │◄── text events─│                     │
  │                │◄── tool_use block ──│
  │                │ execute_tool()      │
  │                │──────┐              │
  │                │◄─────┘              │
  │                │ converse_stream()   │
  │                │────────────────────►│
  │                │◄── end_turn ────────│
  │◄── done event ─│                     │
```

## Request lifecycle — multi agent

```
main.py        orchestrator.py     sub_agent.py (×N, parallel)
  │               │                     │
  │ run_multi()   │                     │
  │──────────────►│                     │
  │               │ _plan_task()        │
  │               │ (1 LLM call)        │
  │               │                     │
  │               │ asyncio fan-out     │
  │               │────────────────────►│ agent 1
  │               │────────────────────►│ agent 2
  │               │────────────────────►│ agent N
  │               │                     │
  │               │◄── events (queue) ──│ (interleaved)
  │◄── events ────│                     │
  │               │ _merge_results()    │
  │               │ (1 LLM call)        │
  │◄── merged ────│                     │
```

## Event system

All streaming is expressed as typed dicts. Producers (agent loops) yield events; consumers (main.py) render them. No shared state, no callbacks.

Core event types: `text`, `tool_start`, `tool_result`, `done`  
Orchestrator-only types: `status`, `plan`, `merged`, `error`

Each event from a sub-agent includes an `agent` key so the renderer can colour-code output by agent.

## Concurrency model

The Bedrock SDK is synchronous. Parallelism is achieved by running each blocking `converse_stream` call inside `asyncio.get_event_loop().run_in_executor(None, ...)`, which dispatches to the default `ThreadPoolExecutor`. No explicit thread management is required.
