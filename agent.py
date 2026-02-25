import re
import uuid
import asyncio
from enum import Enum
from dataclasses import dataclass, field

import llm
import prompts
import tools as tool_defs
from models import Conversation, Message, ToolCall, UserMessage


class NodeType(Enum):
    THINKING = "thinking"
    CODE = "code"
    TEST = "test"
    SYNTHESIZE = "synthesize"


@dataclass
class NodeConfig:
    model: str
    system_prompt: str
    message: str


NODE_CONFIG: dict[NodeType, NodeConfig] = {
    NodeType.THINKING:   NodeConfig("claude-sonnet-4-6", prompts.THINKING_PROMPT, "THOUGHTS"),
    NodeType.CODE:       NodeConfig("claude-haiku-4-5",  prompts.CODE_PROMPT, "CODE"),
    NodeType.TEST:       NodeConfig("claude-haiku-4-5",  prompts.TEST_PROMPT, "TESTS"),
    NodeType.SYNTHESIZE: NodeConfig("claude-sonnet-4-6", prompts.SYNTHESIZE_PROMPT, "SYNTHESIS"),
}

TOOLS_FOR_NODE: dict[NodeType, list] = {
    NodeType.THINKING:   [tool_defs.spawn_subagent],
    NodeType.CODE:       [tool_defs.read_file, tool_defs.write_file, tool_defs.list_directory, tool_defs.run_shell],
    NodeType.TEST:       [tool_defs.read_file, tool_defs.run_shell],
    NodeType.SYNTHESIZE: [],
}


class NodeState(Enum):
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Node:
    node_id: str
    node_type: NodeType
    conversation: Conversation
    tool_id: str | None = None
    parent_id: str | None = None
    children_ids: list[str] = field(default_factory=list)
    active_children: set = field(default_factory=set)
    for_vis: list[str] = field(default_factory=list)  # Current children to visualize
    active_tools: list[ToolCall] = field(default_factory=list)  # Current tool calls being executed
    state: NodeState = NodeState.READY


class DecompositionTree:
    def __init__(self):
        self.root: Node = Node(
            node_id="ROOT",
            node_type=NodeType.THINKING,
            conversation=Conversation(),
            state=NodeState.COMPLETED,  # ROOT is just a placeholder
        )
        self.nodes: dict[str, Node] = {}

    def add_node(self, node: Node) -> None:
        self.nodes[node.node_id] = node

    def add_children(self, parent: Node, children: list[Node]) -> None:
        child_ids = [child.node_id for child in children]
        parent.active_children = set(child_ids)
        parent.children_ids.extend(child_ids)
        parent.for_vis.clear()  # Clear old visualization children
        parent.for_vis.extend(child_ids)  # Add new children for visualization
        parent.state = NodeState.RUNNING
        for child in children:
            self.add_node(child)

    def get_ready_nodes(self) -> list[Node]:
        return [n for n in self.nodes.values() if n.state == NodeState.READY]

    def message_parent(self, node: Node, message: str) -> None:
        if node.parent_id is None or node.parent_id == "ROOT":
            return
        parent = self.nodes[node.parent_id]
        parent.conversation.add_tool_result(node.tool_id, message)

    def sync_with_parent(self, node: Node) -> None:
        if node.parent_id is None or node.parent_id == "ROOT":
            return
        parent = self.nodes[node.parent_id]
        parent.active_children.discard(node.node_id)
        if len(parent.active_children) == 0:
            parent.state = NodeState.READY

    def is_done(self) -> bool:
        return all(n.state == NodeState.COMPLETED for n in self.nodes.values())


class Neo:
    def __init__(self, tree: DecompositionTree, max_concurrent_tasks: int = 10):
        self.tree = tree
        self.sem = asyncio.Semaphore(max_concurrent_tasks)
        self.pending: set[asyncio.Task] = set()

    def prompt(self, prompt: str) -> Node:
        root = Node(
            node_id=self.generate_id(),
            tool_id="",
            node_type=NodeType.THINKING,
            conversation=Conversation(
                system=NODE_CONFIG[NodeType.THINKING].system_prompt,
                messages=[UserMessage(prompt)],
            ),
            parent_id="ROOT",
            children_ids=[],
        )
        self.tree.add_node(root)
        self.tree.root.children_ids.append(root.node_id)
        self.tree.root.active_children.add(root.node_id)
        self.tree.root.for_vis.append(root.node_id)  # Add to visualization too

        return root

    async def run(self) -> Node:
        self.schedule_ready()

        while not self.tree.is_done():
            if not self.pending:
                await asyncio.sleep(0.1)  # Avoid tight loop if no tasks pending
                continue

            done, self.pending = await asyncio.wait(self.pending, return_when=asyncio.FIRST_COMPLETED)

            for task in done:
                node = task.result()
                self.on_node_complete(node)

            self.schedule_ready()

        return self.tree.root if self.tree.root else None

    def schedule_ready(self) -> None:
        for node in self.tree.get_ready_nodes():
            node.state = NodeState.RUNNING
            t = asyncio.create_task(self.execute_node(node))
            self.pending.add(t)

    def on_node_complete(self, node: Node) -> None:
        if node.state == NodeState.COMPLETED:
            self.tree.sync_with_parent(node)

    async def execute_node(self, node: Node) -> Node:
        async with self.sem:
            node_tools = TOOLS_FOR_NODE[node.node_type] or None
            result = await llm.call_llm_async(
                system=NODE_CONFIG[node.node_type].system_prompt,
                model=NODE_CONFIG[node.node_type].model,
                tools=node_tools,
                messages=node.conversation.messages,
            )

            # Bookkeeping for the conversation history.
            content = []
            if result.text:
                content.append({"type": "text", "text": result.text})
            for tc in result.tool_calls:
                content.append({"type": "tool_use", "id": tc.id, "name": tc.name, "input": tc.input})
            node.conversation.add_message(Message(role="assistant", content=content))

            # Decide whether to complete the node or spawn subagents.
            if result.stop_reason == "end_turn":
                message = self.parse_xml_tag(result.text, NODE_CONFIG[node.node_type].message)
                self.tree.message_parent(node, message)
                node.state = NodeState.COMPLETED

            elif result.stop_reason == "tool_use":
                subagents = self.execute_tools(node, result.tool_calls)
                if subagents:
                    self.tree.add_children(node, subagents)
                else:
                    node.state = NodeState.READY

        return node

    def execute_tools(self, caller: Node, tool_calls: list[ToolCall]) -> list[Node]:
        subagents = []
        regular_tools = []

        for tc in tool_calls:
            if tc.name == "spawn_subagent":
                subagents.append(self.spawn_subagent(caller, tc))
            else:
                regular_tools.append(tc)
                result = tool_defs.TOOL_REGISTRY[tc.name](tc.input)
                caller.conversation.add_tool_result(tc.id, result)

        # Update active_tools for visualization - clear old ones first
        if regular_tools:
            caller.active_tools.extend(regular_tools)

        return subagents

    def spawn_subagent(self, parent: Node, tool_call: ToolCall) -> Node:
        node_type = NodeType(tool_call.input["agent_type"])
        return Node(
            node_id=self.generate_id(),
            tool_id=tool_call.id,
            node_type=node_type,
            conversation=Conversation(
                system=NODE_CONFIG[node_type].system_prompt,
                messages=[UserMessage(tool_call.input["task"])],
            ),
            parent_id=parent.node_id,
        )

    def generate_id(self) -> str:
        return str(uuid.uuid4())

    def parse_xml_tag(self, text: str, tag: str) -> str | None:
        match = re.search(rf"<{tag}>(.*?)</{tag}>", text, re.DOTALL)
        return match.group(1).strip() if match else None
