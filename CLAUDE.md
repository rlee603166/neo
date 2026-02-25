# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
uv sync

# Run the tree visualization tests (mocked LLM, no API calls)
uv run python test_viz.py

# Run example scripts
uv run python main.py
uv run python anthro.py
```

There is no test suite or linter configured yet.

## Architecture

Neo is a recursive multi-agent framework built on the Anthropic API. The core idea is a **decomposition tree**: a root "thinking" agent receives a problem, decides whether to answer it directly or split it into independent sub-problems, and spawns typed child agents to handle each sub-problem. Results bubble back up to a synthesizing parent.

### Key files

- **`models.py`** — All dataclasses: `Message`, `Conversation`, `Tool`, `ToolCall`, `AgentResponse`, `SubAgentCall`. `AgentResponse.from_message()` parses raw Anthropic API responses.
- **`llm.py`** — Thin wrapper: `call_llm(messages, system, model, tools) -> AgentResponse` and async variant `call_llm_async()`. Uses module-level `anthropic.Anthropic()` and `anthropic.AsyncAnthropic()` clients.
- **`agent.py`** — Orchestration: `DecompositionTree` manages the node graph; `Neo` drives async execution with a semaphore (`max_concurrent_tasks=10`). Each `Node` holds its own `Conversation` history plus visualization metadata (`for_vis`, `active_tools`).
- **`prompts.py`** — System prompts for each `NodeType`: `THINKING_PROMPT`, `CODE_PROMPT`, `TEST_PROMPT`, `SYNTHESIZE_PROMPT`.
- **`tools.py`** — Tool schemas and implementations. Defines `spawn_subagent` (for creating child nodes), plus file/shell tools (`read_file`, `write_file`, `list_directory`, `run_shell`). `TOOL_REGISTRY` maps tool names to Python callables.
- **`viz.py`** — Frontend module for live terminal visualization using `rich`. Provides `run_with_live_visualization()` and `print_tree_snapshot()`. Displays nodes with state colors, tool calls, and tree expansion/collapse mechanics.
- **`test_viz.py`** — Testing harness with mocked LLM responses. Run this to see the tree mechanics without making API calls.

### Node types and models

| NodeType    | Model               | Role                                      |
|-------------|---------------------|-------------------------------------------|
| THINKING    | claude-sonnet-4-6   | Decompose or directly answer a problem    |
| CODE        | claude-haiku-4-5    | Implement a specific coding task          |
| TEST        | claude-haiku-4-5    | Verify/test code                          |
| SYNTHESIZE  | claude-sonnet-4-6   | Combine outputs from parallel sub-agents  |

### Execution flow

1. A root `Node` (usually `THINKING`) is created and placed in the `DecompositionTree`.
2. `Neo.run()` loops: finds `READY` nodes, schedules them as async tasks.
3. `execute_node()` calls `call_llm` with the node's conversation. On `tool_use` stop, `spawn_subagent` calls create child nodes. On `end_turn`, the node's XML-tagged result (`<THOUGHTS>`, `<CODE>`, etc.) is sent to the parent as a `ToolResultMessage`.
4. When all of a parent's active children complete, the parent's state returns to `READY` and it continues its own conversation.

### Visualization metadata

Nodes track three collections for managing children:
- **`children_ids`** — Permanent history of all children ever spawned (never cleared, for future use)
- **`active_children`** — Runtime tracking set that decrements as children complete
- **`for_vis`** — Current children to display in visualization; cleared when new children spawn or tools execute

This design allows the tree to "fold back in" cleanly: completed children stay visible until the parent starts its next loop.

### Scratch files

`anthro.py` and `main.py` are standalone example scripts (not part of the agent system) used for experimenting with raw Anthropic SDK patterns like parallel tool calls.

## Notes

- `ANTHROPIC_API_KEY` must be set in the environment for `llm.py` and `anthro.py` to work.
- Use `test_viz.py` to develop/debug without making API calls.
