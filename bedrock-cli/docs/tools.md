# tools.py

Defines the tool schemas passed to Bedrock's `converse` / `converse_stream` API. Each entry follows the `toolSpec` format required by the Converse API.

## Available tools

### `bash`
Runs an arbitrary shell command. Returns combined stdout + stderr, truncated to 8 000 characters.

| Input | Type | Required | Default |
|---|---|---|---|
| `command` | string | yes | — |
| `timeout` | integer (seconds) | no | 30 |

### `read_file`
Reads a file from disk. Returns up to 20 000 characters to stay within context limits.

| Input | Type | Required |
|---|---|---|
| `path` | string | yes |

Supports `~` expansion.

### `write_file`
Creates or overwrites a file. Intermediate directories are created automatically.

| Input | Type | Required |
|---|---|---|
| `path` | string | yes |
| `content` | string | yes |

### `list_files`
Recursively lists files under a directory, with optional glob filtering. Returns up to 100 paths.

| Input | Type | Required | Default |
|---|---|---|---|
| `path` | string | no | `.` |
| `pattern` | string | no | `*` |

## Adding a new tool

1. Add a `toolSpec` entry to the `TOOLS` list in `tools.py`.
2. Add a matching `if name == "..."` branch in `executor.py`.

The model will automatically discover and use the tool on its next invocation.
