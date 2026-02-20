from dataclasses import dataclass, field
from typing import Literal


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
