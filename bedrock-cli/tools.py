TOOLS = [
    {
        "toolSpec": {
            "name": "bash",
            "description": "Run a shell command and return stdout/stderr",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "command": {"type": "string"},
                        "timeout": {"type": "integer", "default": 30}
                    },
                    "required": ["command"]
                }
            }
        }
    },
    {
        "toolSpec": {
            "name": "read_file",
            "description": "Read a file's contents",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"}
                    },
                    "required": ["path"]
                }
            }
        }
    },
    {
        "toolSpec": {
            "name": "write_file",
            "description": "Write or overwrite a file",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "content": {"type": "string"}
                    },
                    "required": ["path", "content"]
                }
            }
        }
    },
    {
        "toolSpec": {
            "name": "list_files",
            "description": "List files in a directory",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "default": "."},
                        "pattern": {"type": "string"}
                    }
                }
            }
        }
    }
]
