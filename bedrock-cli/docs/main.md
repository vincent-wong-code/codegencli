# main.py

Entry point and rendering layer. Handles the REPL loop, command dispatch, and all terminal output.

## Commands

| Input | Behaviour |
|---|---|
| `/exit` or `/quit` | Exits the CLI |
| `/clear` | Resets the conversation history |
| `/history` | Prints the number of messages in the current context |
| `/multi <task>` | Runs the task through the parallel multi-agent orchestrator |
| anything else | Runs the single-agent loop |

## `run_single(user_input, history) -> list`

Drives `run_agent_streaming`, rendering each event type:

- `text` — printed immediately as it streams, no newline buffering
- `tool_start` — tool name + arguments printed with an icon prefix
- `tool_result` — first 300 characters of the result, dimmed
- `done` — exits the loop

Returns the updated `history` list for the next turn.

## `run_multi(user_input)`

Drives `run_parallel_agents`, rendering each event type:

- `status` — dimmed spinner-style line
- `plan` — summary + colour-coded agent task list
- `text` — prefixed with a colour-coded `[AGENT]` tag
- `tool_start` / `tool_result` — same as single, but also tagged with agent name
- `done` — per-agent completion marker
- `merged` — rendered as a Rich `Panel` with Markdown inside

## Agent colours

| Agent | Colour |
|---|---|
| architect | cyan |
| coder | green |
| tester | yellow |
| reviewer | magenta |

## Conversation history

History is maintained in `main()` as a plain list and passed into `run_single` each turn. The multi-agent path does not share history with single-agent turns — each `/multi` invocation is stateless.

Prompt history (arrow-key recall) is persisted to `~/.mybedrockcli_history` via `prompt_toolkit.FileHistory`.
