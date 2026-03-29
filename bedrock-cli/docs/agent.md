# agent.py

Single-agent loop with streaming. Used for normal (non-`/multi`) turns.

## `load_system_prompt() -> str`

Reads `system_prompt.txt` and interpolates `{cwd}` at call-time so the model always knows the current working directory. The file is re-read on every turn, so edits take effect without restarting the CLI.

## `run_agent_streaming(user_message, history) -> Generator[dict, None, list]`

A Python generator implementing the agent loop:

```
user message → stream LLM → yield text tokens
                           → if tool_use: execute tools → feed results → loop
                           → if end_turn: yield done, return updated history
```

### Yielded event shapes

| `type` | Extra keys | Description |
|---|---|---|
| `text` | `text` | A streamed text token from the model |
| `tool_start` | `name`, `input` | A tool call is about to execute |
| `tool_result` | `name`, `result` | The tool finished; result will be fed back |
| `done` | — | The model has finished its turn |

The generator returns `history` via `StopIteration.value`. Callers capture it with:

```python
try:
    while True:
        event = next(gen)
        ...
except StopIteration as e:
    history = e.value
```

### Streaming mechanics

`converse_stream` emits three relevant event types:

- `contentBlockStart` — opens a new block; if it's `toolUse`, records the tool ID and name.
- `contentBlockDelta` — carries either a `text` delta or a partial `toolUse.input` JSON string.
- `messageStop` — signals `stopReason` (`end_turn` or `tool_use`).

Tool input JSON arrives as a streaming string and is accumulated until `messageStop`, then parsed once with `json.loads`.
