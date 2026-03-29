import os

AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
SYSTEM_PROMPT_FILE = "system_prompt.txt"
MAX_TOKENS = 4096
TEMPERATURE = 0

DEFAULT_MODEL = "anthropic.claude-3-5-sonnet-20241022-v2:0"

AGENT_MODELS = {
    "orchestrator": "anthropic.claude-3-5-sonnet-20241022-v2:0",
    "architect":    "anthropic.claude-3-5-sonnet-20241022-v2:0",
    "coder":        "anthropic.claude-3-5-sonnet-20241022-v2:0",
    "tester":       "anthropic.claude-3-haiku-20240307-v1:0",
    "reviewer":     "anthropic.claude-3-5-sonnet-20241022-v2:0",
}


def model_for(agent_name: str) -> str:
    return AGENT_MODELS.get(agent_name, DEFAULT_MODEL)
