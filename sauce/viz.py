"""
Frontend visualization module for Neo's decomposition tree.
Provides live terminal UI to watch the tree mechanics in real-time.
"""

import os
import asyncio
from rich.live import Live
from rich.tree import Tree as RichTree
from rich.console import Console
from rich.text import Text


class Tree(RichTree):
    """Rich Tree with curved corners on last-child connectors (╰── instead of └──)."""
    TREE_GUIDES = [
        ("    ", "│   ", "├── ", "╰── "),
        ("    ", "┃   ", "┣━━ ", "┗━━ "),
        ("    ", "║   ", "╠══ ", "╚══ "),
    ]

from sauce.neo import Neo
from sauce.tree import DecompositionTree
from sauce.node import Node, NodeState


# ── Terminal UI Rendering ────────────────────────────────────────────────────

def render_tree(decomp_tree: DecompositionTree) -> Tree:
    """Render the decomposition tree as a rich Tree."""
    root_node = decomp_tree.root
    tree = Tree(format_node(root_node))
    _add_children(tree, root_node, decomp_tree)
    return tree


def _add_children(parent_tree: Tree, parent_node: Node, decomp_tree: DecompositionTree) -> None:
    """Recursively add children to the tree visualization."""
    # Use for_vis instead of children_ids - shows current loop's children only
    for child_id in parent_node.for_vis:
        child_node = decomp_tree.nodes[child_id]
        child_tree = parent_tree.add(format_node(child_node))
        _add_children(child_tree, child_node, decomp_tree)

    # Also show active tool calls as temporary branches
    for tool_call in parent_node.active_tool_calls:
        tool_text = Text()
        tool_text.append("[TOOL]: ", style="yellow")
        tool_text.append(f"{tool_call.name}", style="cyan")
        tool_text.append(f"({_format_tool_input(tool_call.input)})", style="dim")
        parent_tree.add(tool_text)


def _format_tool_input(input_dict: dict) -> str:
    """Format tool input for display."""
    if not input_dict:
        return ""
    # Show first key-value pair, truncate if too long
    items = list(input_dict.items())
    if not items:
        return ""
    key, val = items[0]
    val_str = str(val)
    if len(val_str) > 30:
        val_str = val_str[:27] + "..."
    return f"{key}={val_str}"


def format_node(node: Node) -> Text:
    """Format a node for display with color coding."""
    # Color by state
    color_map = {
        NodeState.READY: "yellow",
        NodeState.RUNNING: "blue",
        NodeState.COMPLETED: "green",
        NodeState.FAILED: "red",
    }
    color = color_map.get(node.state, "white")

    # Format: [STATE] TYPE (node_id) | msgs: N | cwd: path
    text = Text()
    text.append(f"({node.state.value.lower()}) ", style=f"bold bright_{color}")
    text.append(f"{node.node_type.value.upper()} AGENT", style="bright_magenta")
    text.append(f"({node.node_id[:8]}...) ", style="dim")
    text.append(f"| msgs: {len(node.conversation.messages)}", style="dim")

    # Show working directory if not root
    if hasattr(node, 'working_directory') and node.working_directory and node.working_directory != ".":
        text.append(f" | cwd: {node.working_directory}", style="dim italic")

    # Show active children count if any
    if node.active_children:
        text.append(f" | active: {len(node.active_children)}", style="magenta")

    return text


def render_tree_with_title(tree: DecompositionTree, title: str) -> Tree:
    """Render tree with a title."""
    title_tree = Tree(f"[bold white]{title}[/bold white]")
    actual_tree = render_tree(tree)
    title_tree.add(actual_tree)
    return title_tree


# ── Live Visualization Runner ─────────────────────────────────────────────────

async def run_with_live_visualization(
    neo: Neo,
    task: str,
    title: str = "Neo Decomposition Tree",
    refresh_rate: int = 4
) -> None:
    """
    Run Neo with live visualization.

    Args:
        neo: Neo instance with initialized tree (env_directory set at initialization)
        task: Task to prompt Neo with
        title: Title for the visualization
        refresh_rate: Refresh rate in Hz (default 4)
    """
    console = Console()

    # Create the initial task
    neo.prompt(task)

    with Live(console=console, refresh_per_second=refresh_rate) as live:
        # Start the visualization update loop
        viz_task = asyncio.create_task(_update_visualization(live, neo.tree, title))

        # Run Neo
        await neo.run()

        # Final update
        await asyncio.sleep(0.5)
        live.update(render_tree_with_title(neo.tree, title))

        # Cancel viz task
        viz_task.cancel()
        try:
            await viz_task
        except asyncio.CancelledError:
            pass


async def _update_visualization(live: Live, tree: DecompositionTree, title: str) -> None:
    """Continuously update the visualization."""
    while True:
        live.update(render_tree_with_title(tree, title))
        await asyncio.sleep(0.25)


# ── Static Snapshot Rendering ────────────────────────────────────────────────

def print_tree_snapshot(tree: DecompositionTree, title: str = "Neo Tree Snapshot") -> None:
    """Print a static snapshot of the tree (no live updates)."""
    console = Console()
    console.print("\n")
    console.print(render_tree_with_title(tree, title))
    console.print("\n")
