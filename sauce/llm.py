import anthropic

from sauce.models import AgentResponse, Message, Tool

client = anthropic.Anthropic()
async_client = anthropic.AsyncAnthropic()


def call_llm(
    messages: list[Message],
    system: str = "",
    model: str = "claude-sonnet-4-6",
    tools: list[Tool] | None = None,
) -> AgentResponse:
    kwargs = {
        "model": model,
        "max_tokens": 8096,
        "messages": [m.to_dict() for m in messages],
    }
    if system:
        kwargs["system"] = system
    if tools:
        kwargs["tools"] = [t.to_dict() for t in tools]

    return AgentResponse.from_message(client.messages.create(**kwargs))


async def call_llm_async(
    messages: list[Message],
    system: str = "",
    model: str = "claude-sonnet-4-6",
    tools: list[Tool] | None = None,
) -> AgentResponse:
    kwargs = {
        "model": model,
        "max_tokens": 8096,
        "messages": [m.to_dict() for m in messages],
    }
    if system:
        kwargs["system"] = system
    if tools:
        kwargs["tools"] = [t.to_dict() for t in tools]

    return AgentResponse.from_message(await async_client.messages.create(**kwargs))
