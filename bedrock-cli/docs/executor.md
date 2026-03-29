# executor.py

Implements the tool execution layer. Called by both the single agent (`agent.py`) and sub-agents (`sub_agent.py`) after the model emits a `tool_use` block.

## `execute_tool(name, inputs) -> str`

Dispatches to the correct handler based on `name`, runs the operation, and returns a plain string result. All exceptions are caught and returned as `"ERROR: ..."` strings so the model can reason about failures rather than crashing.

## Output truncation

| Tool | Limit | Reason |
|---|---|---|
| `bash` | 8 000 chars | Prevents large build logs from filling the context window |
| `read_file` | 20 000 chars | Large files are summarised by the model rather than read wholesale |
| `list_files` | 100 paths | Keeps directory listings scannable |

Truncation is silent — the model receives the truncated string with no truncation marker. If a task requires processing a very large file, prompt the model to use `bash` with `head`, `grep`, or `awk` to extract only the relevant portion.
