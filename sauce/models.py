
import anthropic
from enum import Enum
from typing import Literal
from dataclasses import dataclass, field


@dataclass
class Message:
    role: Literal["user", "assistant"]
    content: str | list

    def to_dict(self) -> dict:
        return {"role": self.role, "content": self.content}


def UserMessage(content: str) -> Message:
    return Message(role="user", content=content)


def AssistantMessage(content: str) -> Message:
    return Message(role="assistant", content=content)


def ToolResultMessage(tool_use_id: str, content: str) -> Message:
    return Message(
        role="user",
        content=[{"type": "tool_result", "tool_use_id": tool_use_id, "content": content}],
    )


@dataclass
class Conversation:
    """Accumulates the full message history for a single agent session."""

    system: str = ""
    messages: list[Message] = field(default_factory=list)

    def add_user(self, content: str) -> None:
        self.messages.append(UserMessage(content))

    def add_assistant(self, content: str) -> None:
        self.messages.append(AssistantMessage(content))

    def add_message(self, message: Message) -> None:
        self.messages.append(message)

    def add_tool_use(self, tool_use_id: str, name: str, input: dict) -> None:
        """Appends the assistant turn that contains a tool_use block."""
        self.messages.append(
            Message(
                role="assistant",
                content=[{"type": "tool_use", "id": tool_use_id, "name": name, "input": input}],
            )
        )

    def add_tool_result(self, tool_use_id: str, content: str) -> None:
        self.messages.append(ToolResultMessage(tool_use_id, content))

    def to_list(self) -> list[dict]:
        return [m.to_dict() for m in self.messages]

    def from_list(self, data: list[dict]) -> "Conversation":
        self.messages = [Message(**m) for m in data]
        return self

    def __len__(self) -> int:
        return len(self.messages)


@dataclass
class ToolProperty:
    type: str
    description: str

    def to_dict(self) -> dict:
        return {"type": self.type, "description": self.description}


@dataclass
class InputSchema:
    properties: dict[str, ToolProperty]
    required: list[str] = field(default_factory=list)
    type: str = "object"

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "properties": {k: v.to_dict() for k, v in self.properties.items()},
            "required": self.required,
        }


@dataclass
class Tool:
    name: str
    description: str
    input_schema: InputSchema

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema.to_dict(),
        }

class ToolType(Enum):
    SPAWN_SUBAGENT = "spawn_subagent"


@dataclass
class ToolCall:
    id: str
    name: str
    input: dict


@dataclass
class SubAgentParams:
    task: str
    agent_type: str

@dataclass
class SubAgentCall(ToolCall):
    input: SubAgentParams


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
