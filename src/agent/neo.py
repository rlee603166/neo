import asyncio

from agent.tree import DecompositionTree, Node, NodeType


class NeoAgent:
    def __init__(self, tree: DecompositionTree, max_concurrent_tasks: int = 10):
        self.tree = tree
        self.sem = asyncio.Semaphore(max_concurrent_tasks)
        self.pending: set[asyncio.Task] = set()

    async def run(self):
        self.schedule_ready()

        while not self.tree.is_done():
            done, self.pending = await asyncio.wait(self.pending, return_when=asyncio.FIRST_COMPLETED)

            for task in done:
                node = task.result()
                self.on_node_complete(node)

            self.schedule_ready()

    def schedule_ready(self):
        for node in self.tree.get_ready_nodes():
            if node.node_id not in self.pending:
                t = asyncio.create_task(self.execute_node(node))
                self.pending.add(t)

    async def execute_node(self, node: Node) -> Message:
        async with self.sem:
            match node.type:
                case NodeType.DECOMPOSITION:
                    await self.decomposition(node)
                case NodeType.CODE:
                    message =AssistantMessage(await self.code(node))
                case NodeType.TEST:
                    message = AssistantMessage(await self.test(node))
                case NodeType.SYNTHESIZE:
                    message = AssistantMessage(await self.synthesize(node))

    def node_on_complete(self, node: Node):
        self.tree.message_parent_node(node)

    async def decomposition(self, node: Node):
        result = await self.llm.call(node.conversation)
        children = [SubAgent(r) for r in result.tool_calls]
        self.tree.add_children(node, children)
