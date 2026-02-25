"""
Main entry point for Neo with live visualization.
Run with: uv run python main.py
"""
import asyncio

from sauce import DecompositionTree, Neo, run_with_live_visualization

async def main():

    env_dir = "./sandbox"

    tree = DecompositionTree()
    neo = Neo(tree, max_concurrent_tasks=10, env_dir=env_dir)

    # Define the task
    task = """Build a Python algorithms library as a package at ./algorithms/.
    Implement and test the following categories, each in its own module:

    1. Sorting: bubble sort, merge sort, quick sort, heap sort, radix sort
    2. Searching: binary search, BFS, DFS, A*
    3. Graph algorithms: Dijkstra's shortest path, topological sort, detect cycles, find connected components
    4. Data structures: linked list, stack, queue, min-heap, hash map (open addressing)

    Each implementation must have a corresponding test file that verifies correctness.
    Finally, produce a README.md documenting the public API for each module.
    """

    # Run with live visualization
    await run_with_live_visualization(
        neo=neo,
        task=task,
        title="Neo Decomposition Tree - Live",
        refresh_rate=4
    )

    tree.dump_state(f"{env_dir}/state/tree.json")


if __name__ == "__main__":
    asyncio.run(main())
