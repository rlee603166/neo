"""
Main entry point for Neo with live visualization.
Run with: uv run python main.py
"""
import asyncio
import signal
import sys

from sauce import DecompositionTree, Neo, run_with_live_visualization

STATE_PATH = "dashboard/backend/state/tree.json"

async def main():

    env_dir = "./sandbox"

    tree = DecompositionTree()
    neo = Neo(tree, max_concurrent_tasks=10, env_directory=env_dir)

    def handle_sigint(sig, frame):
        print("\nInterrupted — saving tree state...")
        if tree.root is not None:
            tree.dump_state(STATE_PATH)
            print(f"Tree state saved to {STATE_PATH}")
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_sigint)

    task = input("What do you want to build? ").strip()
    if not task:
        print("No task provided. Exiting.")
        return

    try:
        await run_with_live_visualization(
            neo=neo,
            task=task,
            title="Neo Decomposition Tree - Live",
            refresh_rate=4
        )
    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\nInterrupted — saving tree state...")
        if tree.root is not None:
            tree.dump_state(STATE_PATH)
            print(f"Tree state saved to {STATE_PATH}")
        return

    print(tree.root.conversation.messages[-1].content[0]['text'])
    tree.dump_state(STATE_PATH)


if __name__ == "__main__":
    asyncio.run(main())
