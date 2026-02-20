from dataclasses import dataclass, field
import anthropic


@dataclass
class ToolCall:
    id: str
    name: str
    input: dict


@dataclass
class AgentResponse:
    text: str
    tool_calls: list[ToolCall]
    stop_reason: str
    input_tokens: int
    output_tokens: int

    @property
    def has_tool_calls(self) -> bool:
        return len(self.tool_calls) > 0

    @classmethod
    def from_message(cls, message: anthropic.types.Message) -> "AgentResponse":
        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []

        for block in message.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(ToolCall(id=block.id, name=block.name, input=block.input))

        return cls(
            text="\n".join(text_parts),
            tool_calls=tool_calls,
            stop_reason=message.stop_reason or "",
            input_tokens=message.usage.input_tokens,
            output_tokens=message.usage.output_tokens,
        )
