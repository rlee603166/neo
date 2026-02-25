import json
import os

from sauce.node import Node, NodeType, NodeState


class DecompositionTree:
    def __init__(self):
        self.root: Node | None = None
        self.nodes: dict[str, Node] = {}

    def set_root(self, node: Node) -> None:
        self.root = node
        self.add_node(node)


    def add_node(self, node: Node) -> None:
        self.nodes[node.node_id] = node

    def add_children(self, parent: Node, children: list[Node]) -> None:
        child_ids = [child.node_id for child in children]
        parent.active_children = set(child_ids)
        parent.children_ids.extend(child_ids)
        parent.for_vis.clear()
        parent.for_vis.extend(child_ids)
        parent.state = NodeState.RUNNING
        for child in children:
            self.add_node(child)

    def get_ready_nodes(self) -> list[Node]:
        return [n for n in self.nodes.values() if n.state == NodeState.READY]

    def message_parent(self, node: Node, message: str) -> None:
        if node.parent_id is None:
            return
        parent = self.nodes[node.parent_id]
        parent.conversation.add_tool_result(node.tool_id, message)

    def sync_with_parent(self, node: Node) -> None:
        if node.parent_id is None:
            return
        parent = self.nodes[node.parent_id]
        parent.active_children.discard(node.node_id)
        if len(parent.active_children) == 0:
            parent.for_vis.clear()
            parent.state = NodeState.READY

    def is_done(self) -> bool:
        if self.root is None:
            return False
        return all(n.state == NodeState.COMPLETED for n in self.nodes.values())

    def dump_state(self, path: str | None = None) -> dict:
        """Serialize the full tree to a dict. Optionally writes to a JSON file at `path`."""
        self.root.state = NodeState.COMPLETED
        root_id = self.root.node_id
        state = {
            "root": self.root.to_dict(),
            "nodes": {node_id: node.to_dict() for node_id, node in self.nodes.items() if node_id != root_id},
        }
        if path:
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            with open(path, "w") as f:
                json.dump(state, f, indent=2)
        return state

    @classmethod
    def load_state(cls, source: dict | str) -> "DecompositionTree":
        """Reconstruct a tree from a dict or a path to a JSON file produced by dump_state()."""
        if isinstance(source, str):
            with open(source) as f:
                source = json.load(f)
        tree = cls.__new__(cls)
        tree.root = Node.from_dict(source["root"])
        tree.nodes = {node_id: Node.from_dict(node_data) for node_id, node_data in source["nodes"].items()}
        tree.nodes[tree.root.node_id] = tree.root
        return tree
