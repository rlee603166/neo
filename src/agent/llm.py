import anthropic
from models import Message, Tool

client = anthropic.Anthropic()


def call_llm(messages: list[Message], system: str = "", model: str = "claude-sonnet-4-6", tools: list[Tool] | None = None) -> anthropic.types.Message:
    kwargs = {
        "model": model,
        "max_tokens": 8096,
        "messages": [m.to_dict() for m in messages],
    }
    if system:
        kwargs["system"] = system
    if tools:
        kwargs["tools"] = [t.to_dict() for t in tools]

    return client.messages.create(**kwargs)
