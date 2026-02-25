import json
from enum import Enum
from dataclasses import dataclass, field

import prompts
import tools as tool_defs
from models import Conversation, Message, ToolCall, UserMessage


class NodeType(Enum):
    THINKING = "thinking"
    CODE = "code"
    TEST = "test"
    SYNTHESIZE = "synthesize"


class NodeState(Enum):
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class NodeConfig:
    model: str
    system_prompt: str
    message: str


NODE_CONFIG: dict[NodeType, NodeConfig] = {
    NodeType.THINKING:  NodeConfig("claude-sonnet-4-6", prompts.THINKING_PROMPT, "MESSAGE"),
    NodeType.CODE:      NodeConfig("claude-haiku-4-5",  prompts.CODE_PROMPT,     "MESSAGE"),
    NodeType.TEST:      NodeConfig("claude-haiku-4-5",  prompts.TEST_PROMPT,     "MESSAGE"),
}

TOOLS_FOR_NODE: dict[NodeType, list] = {
    NodeType.THINKING:  [tool_defs.spawn_subagent, tool_defs.read_file, tool_defs.write_file, tool_defs.list_directory, tool_defs.run_shell],
    NodeType.CODE:      [tool_defs.read_file, tool_defs.write_file, tool_defs.list_directory, tool_defs.run_shell, tool_defs.spawn_subagent],
    NodeType.TEST:      [tool_defs.read_file, tool_defs.run_shell],
}


@dataclass
class Node:
    node_id: str
    node_type: NodeType
    conversation: Conversation
    tool_id: str | None = None
    parent_id: str | None = None

    state: NodeState = NodeState.READY

    children_ids: list[str] = field(default_factory=list)
    active_children: set = field(default_factory=set)

    for_vis: list[str] = field(default_factory=list)
    tool_calls: list[ToolCall] = field(default_factory=list)

    # Track file versions for optimistic concurrency control
    file_versions: dict[str, str] = field(default_factory=dict)

    # Working directory for this node
    working_directory: str = "."

    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type.value,
            "tool_id": self.tool_id,
            "parent_id": self.parent_id,
            "state": self.state.value,
            "children_ids": self.children_ids,
            "active_children": list(self.active_children),
            "for_vis": self.for_vis,
            "tool_calls": [{"id": tc.id, "name": tc.name, "input": tc.input} for tc in self.tool_calls],
            "file_versions": self.file_versions,
            "working_directory": self.working_directory,
            "conversation": {
                "system": self.conversation.system,
                "messages": self.conversation.to_list(),
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Node":
        conversation = Conversation(
            system=data["conversation"]["system"],
            messages=[Message(**m) for m in data["conversation"]["messages"]],
        )
        return cls(
            node_id=data["node_id"],
            node_type=NodeType(data["node_type"]),
            conversation=conversation,
            tool_id=data.get("tool_id"),
            parent_id=data.get("parent_id"),
            state=NodeState(data["state"]),
            children_ids=data.get("children_ids", []),
            active_children=set(data.get("active_children", [])),
            for_vis=data.get("for_vis", []),
            tool_calls=[ToolCall(**tc) for tc in data.get("tool_calls", [])],
            file_versions=data.get("file_versions", {}),
            working_directory=data.get("working_directory", "."),
        )
