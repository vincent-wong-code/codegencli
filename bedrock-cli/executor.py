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
