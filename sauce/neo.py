import os
import re
import uuid
import asyncio

import llm
import tools as tool_defs
from models import Conversation, Message, ToolCall, UserMessage
from node import Node, NodeType, NodeState, NODE_CONFIG, TOOLS_FOR_NODE
from tree import DecompositionTree


class Neo:
    def __init__(self, tree: DecompositionTree, max_concurrent_tasks: int = 10):
        self.tree = tree
        self.sem = asyncio.Semaphore(max_concurrent_tasks)
        self.pending: set[asyncio.Task] = set()

    def prompt(self, prompt: str, working_directory: str = ".") -> Node:
        prompt_with_context = f"[Working Directory: {working_directory}]\n\n{prompt}"

        root = Node(
            node_id=self.generate_id(),
            tool_id="",
            node_type=NodeType.THINKING,
            conversation=Conversation(
                system=NODE_CONFIG[NodeType.THINKING].system_prompt,
                messages=[UserMessage(prompt_with_context)],
            ),
            parent_id="ROOT",
            children_ids=[],
            working_directory=working_directory,
        )
        self.tree.add_node(root)
        self.tree.root.children_ids.append(root.node_id)
        self.tree.root.active_children.add(root.node_id)
        self.tree.root.for_vis.append(root.node_id)

        return root

    async def run(self) -> Node:
        self.schedule_ready()

        while not self.tree.is_done():
            if not self.pending:
                await asyncio.sleep(0.1)
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

            content = []
            if result.text:
                content.append({"type": "text", "text": result.text})
            for tc in result.tool_calls:
                content.append({"type": "tool_use", "id": tc.id, "name": tc.name, "input": tc.input})
            node.conversation.add_message(Message(role="assistant", content=content))

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
                node = self.spawn_subagent(caller, tc)
                if node:
                    subagents.append(node)
            else:
                regular_tools.append(tc)
                result = tool_defs.TOOL_REGISTRY[tc.name](tc.input, self.tree, caller.node_id, caller.working_directory)
                caller.conversation.add_tool_result(tc.id, result)

        if regular_tools:
            caller.tool_calls.extend(regular_tools)

        return subagents

    def spawn_subagent(self, parent: Node, tool_call: ToolCall) -> Node | None:
        requested = tool_call.input["agent_type"]
        allowed = tool_defs.ALLOWED_SPAWN.get(parent.node_type.value, [])
        if requested not in allowed:
            error = f"Error: {parent.node_type.value} agents may only spawn {allowed}, not '{requested}'."
            parent.conversation.add_tool_result(tool_call.id, error)
            return None

        requested_dir = tool_call.input.get("working_directory")

        if requested_dir is None:
            working_dir = parent.working_directory
        elif os.path.isabs(requested_dir):
            working_dir = requested_dir
        else:
            working_dir = os.path.join(parent.working_directory, requested_dir)

        try:
            os.makedirs(working_dir, exist_ok=True)
        except Exception as e:
            error = f"Error: Could not create directory '{working_dir}': {e}"
            parent.conversation.add_tool_result(tool_call.id, error)
            return None

        node_type = NodeType(requested)
        task_with_context = f"[Working Directory: {working_dir}]\n\n{tool_call.input['task']}"

        return Node(
            node_id=self.generate_id(),
            tool_id=tool_call.id,
            node_type=node_type,
            conversation=Conversation(
                system=NODE_CONFIG[node_type].system_prompt,
                messages=[UserMessage(task_with_context)],
            ),
            parent_id=parent.node_id,
            working_directory=working_dir,
        )

    def generate_id(self) -> str:
        return str(uuid.uuid4())

    def parse_xml_tag(self, text: str, tag: str) -> str | None:
        match = re.search(rf"<{tag}>(.*?)</{tag}>", text, re.DOTALL)
        return match.group(1).strip() if match else None
