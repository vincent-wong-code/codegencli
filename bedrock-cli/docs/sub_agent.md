# sub_agent.py

Async variant of the agent loop, designed to run multiple agents concurrently via `asyncio`.

## `run_sub_agent(agent_name, task, context="") -> AsyncGenerator[dict, None]`

Behaves identically to `run_agent_streaming` but is an `async` generator. Each sub-agent gets its own Bedrock client instance, its own conversation history, and its own system prompt loaded from `prompts/<agent_name>.txt`.

Each sub-agent resolves its model at startup by calling `model_for(agent_name)` from `config.py`. The resolved model ID is held for the entire agent lifetime and included in the final `done` event so the UI can display which model each agent used.

### Why async?

Bedrock's Python SDK is synchronous. Rather than spawning threads, each blocking `converse_stream` call is offloaded to the default thread pool via `loop.run_in_executor(None, ...)`. This lets `asyncio.gather` run multiple agents in parallel without the overhead of managing threads manually.

### Yielded event shapes

| `type` | Extra keys | Description |
|---|---|---|
| `text` | `agent`, `text` | Streamed token |
| `tool_start` | `agent`, `name`, `input` | Tool about to execute |
| `tool_result` | `agent`, `name`, `result` | Tool result |
| `done` | `agent`, `model`, `result` | Agent finished; `model` is the resolved Bedrock model ID |

### System prompt loading

`_load_prompt(agent_name)` reads `prompts/<agent_name>.txt` and formats `{cwd}`. The file is read once per agent invocation.

### Blocking call isolation

Both `_invoke_bedrock_stream` (the network call) and `execute_tool` (potentially slow shell commands) are wrapped in `run_in_executor` so they never block the event loop.
