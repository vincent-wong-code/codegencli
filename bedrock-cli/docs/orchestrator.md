# orchestrator.py

Coordinates the multi-agent workflow triggered by `/multi`. Responsible for planning, fan-out, and result synthesis.

## Flow

```
user task
  │
  ▼
_plan_task()          — one blocking LLM call → JSON task list
  │
  ▼
asyncio fan-out       — one sub-agent coroutine per task, all started simultaneously
  │
  ▼
asyncio.Queue         — all agent event streams drain into a single queue
  │                     events are yielded to the caller as they arrive
  ▼
_merge_results()      — one blocking LLM call → synthesised final response
```

## `_plan_task(user_task) -> dict`

Calls the orchestrator model with the user's task. The model returns a JSON object:

```json
{
  "summary": "Brief description of the approach",
  "tasks": [
    {"agent": "architect", "task": "..."},
    {"agent": "coder",     "task": "..."}
  ]
}
```

The orchestrator prompt (`prompts/orchestrator.txt`) instructs the model to return only JSON. Markdown fences are stripped before parsing as a safety measure.

## `_merge_results(plan, results, user_task) -> str`

Concatenates all agent outputs into a single prompt and asks the model to synthesise them into a coherent response. The merge prompt explicitly asks for key decisions, important code, and a summary of what was accomplished.

## `run_parallel_agents(user_task) -> AsyncGenerator[dict, None]`

Top-level entry point called from `main.py`. Yields the same event shapes as `run_sub_agent`, plus two orchestrator-specific events:

| `type` | Extra keys | Description |
|---|---|---|
| `status` | `text` | Informational message (planning, merging) |
| `plan` | `plan` | The parsed task plan from `_plan_task` |
| `merged` | `text` | The final synthesised response |
| `error` | `text` | Emitted if the orchestrator returns no tasks |

## Queue-based fan-in

Each sub-agent runs in its own `asyncio.Task`. Every event it emits is put onto a shared `asyncio.Queue`. The main loop reads from the queue and yields events until it receives the `None` sentinel, which is pushed after the last agent finishes. This approach keeps the caller's rendering logic simple — it sees a single stream of labelled events regardless of how many agents are running.
