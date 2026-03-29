# config.py

Central configuration. All tuneable values live here — no magic numbers scattered across the codebase.

## Variables

| Variable | Default | Description |
|---|---|---|
| `DEFAULT_MODEL` | `claude-3-5-sonnet-20241022-v2:0` | Fallback model for any agent not listed in `AGENT_MODELS`. |
| `AGENT_MODELS` | see below | Per-agent model map. |
| `AWS_REGION` | `us-east-1` (or `$AWS_REGION`) | Region for the Bedrock client. |
| `SYSTEM_PROMPT_FILE` | `system_prompt.txt` | Path (relative to project root) of the single-agent system prompt. |
| `MAX_TOKENS` | `4096` | Maximum tokens per LLM response. |
| `TEMPERATURE` | `0` | Sampling temperature. 0 = deterministic, better for tool-use. |

## Per-agent model assignment

Each agent resolves its model at runtime via `model_for(agent_name)`. Edit `AGENT_MODELS` to route any agent to any Bedrock-supported model:

```python
AGENT_MODELS = {
    "orchestrator": "anthropic.claude-3-5-sonnet-20241022-v2:0",  # needs strong reasoning
    "architect":    "anthropic.claude-3-5-sonnet-20241022-v2:0",  # needs strong reasoning
    "coder":        "anthropic.claude-3-5-sonnet-20241022-v2:0",  # needs strong reasoning
    "tester":       "anthropic.claude-3-haiku-20240307-v1:0",     # fast + cheap for boilerplate
    "reviewer":     "anthropic.claude-3-5-sonnet-20241022-v2:0",  # needs strong reasoning
}
```

## `model_for(agent_name) -> str`

Looks up `AGENT_MODELS[agent_name]`. Falls back to `DEFAULT_MODEL` for any unknown agent name, so custom agents added at runtime never raise a `KeyError`.

## Available Bedrock model strings

```python
# Anthropic — best tool-use support
"anthropic.claude-3-5-sonnet-20241022-v2:0"
"anthropic.claude-3-haiku-20240307-v1:0"      # 3× faster, ~20× cheaper than Sonnet

# Amazon Nova
"amazon.nova-pro-v1:0"                         # strong reasoning
"amazon.nova-lite-v1:0"                        # fast, low cost

# Meta Llama
"meta.llama3-1-70b-instruct-v1:0"
"meta.llama3-1-8b-instruct-v1:0"               # very fast, low cost
```

Tool-use reliability varies. Anthropic models have the most consistent tool-use behaviour. Test non-Anthropic models before assigning them to tool-heavy agents like `coder`.
