"""
Testing module for Neo with mocked LLM calls and visualization.
Run this to see the tree mechanics without making real API calls.
"""

import asyncio
from unittest.mock import patch
from rich.console import Console

from sauce.neo import DecompositionTree, Neo
from sauce.models import AgentResponse, ToolCall
from sauce.viz import run_with_live_visualization


# ── Mock LLM Infrastructure ───────────────────────────────────────────────────

async def mock_call_llm_async(
    messages: list,
    system: str = "",
    model: str = "",
    tools: list | None = None,
) -> AgentResponse:
    """Mock LLM that returns scripted responses based on conversation state."""

    # Simulate API latency
    await asyncio.sleep(2.5)

    # Determine what kind of response to return based on the system prompt
    if "recursive reasoning agent" in system:  # THINKING node
        return _mock_thinking_response(messages)
    elif "code implementation agent" in system:  # CODE node
        return _mock_code_response(messages)
    elif "code verification agent" in system:  # TEST node
        return _mock_test_response(messages)
    elif "synthesis agent" in system:  # SYNTHESIZE node
        return _mock_synthesize_response()

    # Default: just end
    return AgentResponse(
        text="<DEFAULT>Done</DEFAULT>",
        tool_calls=[],
        stop_reason="end_turn",
        input_tokens=100,
        output_tokens=50,
    )


def _mock_thinking_response(messages: list) -> AgentResponse:
    """THINKING node spawns sub-agents on first call, then completes."""
    already_spawned = any(
        isinstance(m.content, list) and any(b.get("type") == "tool_result" for b in m.content)
        for m in messages if m.role == "user"
    )
    if already_spawned:
        return AgentResponse(
            text="<MESSAGE>All sub-tasks complete.</MESSAGE>",
            tool_calls=[],
            stop_reason="end_turn",
            input_tokens=100,
            output_tokens=50,
        )
    return AgentResponse(
        text="I'll break this down into sub-problems.",
        tool_calls=[
            ToolCall(
                id="call_1",
                name="spawn_subagent",
                input={"task": "Implement feature X", "agent_type": "code"}
            ),
            ToolCall(
                id="call_2",
                name="spawn_subagent",
                input={"task": "Write tests for feature X", "agent_type": "test"}
            ),
            ToolCall(
                id="call_3",
                name="spawn_subagent",
                input={"task": "Implement feature Y", "agent_type": "code"}
            ),
        ],
        stop_reason="tool_use",
        input_tokens=100,
        output_tokens=50,
    )


def _mock_code_response(messages: list) -> AgentResponse:
    """CODE node makes a few tool calls then completes."""
    # Count how many tool results we've received
    tool_result_count = sum(1 for m in messages if m.role == "user" and
                           isinstance(m.content, list) and
                           any(b.get("type") == "tool_result" for b in m.content))

    if tool_result_count == 0:
        # First call: read a file
        return AgentResponse(
            text="Let me read the existing code.",
            tool_calls=[
                ToolCall(id="read_1", name="read_file", input={"path": "example.py"})
            ],
            stop_reason="tool_use",
            input_tokens=100,
            output_tokens=50,
        )
    elif tool_result_count == 1:
        # Second call: write a file
        return AgentResponse(
            text="Now I'll write the implementation.",
            tool_calls=[
                ToolCall(id="write_1", name="write_file", input={"path": "feature.py", "content": "# implementation"})
            ],
            stop_reason="tool_use",
            input_tokens=100,
            output_tokens=50,
        )
    elif tool_result_count == 2:
        # Third call: run tests
        return AgentResponse(
            text="Let me verify it works.",
            tool_calls=[
                ToolCall(id="shell_1", name="run_shell", input={"command": "python feature.py"})
            ],
            stop_reason="tool_use",
            input_tokens=100,
            output_tokens=50,
        )
    else:
        # Done
        return AgentResponse(
            text="<CODE>\ndef feature_x():\n    return 'implemented'\n</CODE>",
            tool_calls=[],
            stop_reason="end_turn",
            input_tokens=100,
            output_tokens=50,
        )


def _mock_test_response(messages: list) -> AgentResponse:
    """TEST node reads code, runs tests, completes."""
    tool_result_count = sum(1 for m in messages if m.role == "user" and
                           isinstance(m.content, list) and
                           any(b.get("type") == "tool_result" for b in m.content))

    if tool_result_count == 0:
        return AgentResponse(
            text="Reading the code to test.",
            tool_calls=[
                ToolCall(id="read_1", name="read_file", input={"path": "feature.py"})
            ],
            stop_reason="tool_use",
            input_tokens=100,
            output_tokens=50,
        )
    elif tool_result_count == 1:
        return AgentResponse(
            text="Running tests.",
            tool_calls=[
                ToolCall(id="shell_1", name="run_shell", input={"command": "pytest feature.py"})
            ],
            stop_reason="tool_use",
            input_tokens=100,
            output_tokens=50,
        )
    else:
        return AgentResponse(
            text="<TESTS>\nAll tests passed ✓\n</TESTS>",
            tool_calls=[],
            stop_reason="end_turn",
            input_tokens=100,
            output_tokens=50,
        )


def _mock_synthesize_response() -> AgentResponse:
    """SYNTHESIZE node just combines results."""
    return AgentResponse(
        text="<SYNTHESIS>\nCombined all sub-agent results successfully.\n</SYNTHESIS>",
        tool_calls=[],
        stop_reason="end_turn",
        input_tokens=100,
        output_tokens=50,
    )


# ── Test Scenarios ────────────────────────────────────────────────────────────

SIMPLE_TASK = "Build a new feature with tests"
TOOL_HEAVY_TASK = "Refactor the codebase"


# ── Entry Point ───────────────────────────────────────────────────────────────

async def main():
    """Run all test scenarios."""
    console = Console()

    # Patch the LLM call
    with patch('sauce.llm.call_llm_async', new=mock_call_llm_async):

        console.print("\n[bold cyan]═══ Test 1: Simple Scenario ═══[/bold cyan]\n")
        console.print("THINKING node spawns 3 children (CODE + TEST + CODE)")
        console.print("Each child makes sequential tool calls\n")
        tree1 = DecompositionTree()
        neo1 = Neo(tree1)
        await run_with_live_visualization(neo1, SIMPLE_TASK, "Simple: THINKING → 3 children")
        await asyncio.sleep(2)

        console.print("\n[bold green]✓ All scenarios complete![/bold green]\n")


if __name__ == "__main__":
    asyncio.run(main())
