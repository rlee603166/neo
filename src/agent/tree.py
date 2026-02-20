from dataclasses import dataclass
from models import Conversation
from enum import Enum

class NodeType(Enum):
    DECOMPOSITION = "decomposition"
    CODE = "code"
    TEST = "test"
    SYNTHESIZE = "synthesize"

class NodeState(Enum):
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class Node:
    node_id: str
    parent_id: str | None
    children_ids: list[str]
    children_counter: int
    conversation: Conversation
    type: NodeType
    state: NodeState


class DecompositionTree:
    root: Node
    nodes: dict[str, Node]

    def __init__(self, root: Node):
        self.root = root
        self.nodes = {root.node_id: root}
    
    def get_ready_nodes(self) -> list[Node]:
        return [node for node in self.nodes.values() if node.state == NodeState.READY]

    def to_dict(self) -> dict:
        return {
            "root_id": self.root.node_id,
            "nodes": {k: v.to_dict() for k, v in self.nodes.items()},
        }

    def add_node(self, node: Node):
        self.nodes[node.node_id] = node

    def is_done(self) -> bool:
        if len(self.nodes) == 0:
            return True
        return False

    def message_parent_node(self, node: Node):
        parent_id = node.parent_id

        self.nodes[parent_id].children_counter -= 1
        if self.nodes[parent_id].children_counter == 0:
            self.nodes[parent_id].state = NodeState.READY

    def add_children(self, parent: Node, children: list[Node]):
        parent.children_counter = len(children)
        for child in children:
            child.parent_id = parent.node_id
            self.add_node(child)