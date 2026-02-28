# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
uv sync

# Run the tree visualization tests (mocked LLM, no API calls)
uv run python -m sauce.tests.viz

# Run with live visualization (prompts for a task)
uv run python main.py
```

There is no test suite or linter configured yet. `sauce/tests/concurrency.py` tests optimistic concurrency control but imports from old top-level paths and is currently broken.

## Architecture

Neo is a recursive multi-agent framework built on the Anthropic API. The core idea is a **decomposition tree**: a root "thinking" agent receives a problem, decides whether to answer it directly or split it into independent sub-problems, and spawns typed child agents to handle each sub-problem. Results bubble back up to a synthesizing parent.

### Package structure

All core logic lives in the `sauce/` package:

- **`sauce/models.py`** — Dataclasses: `Message`, `Conversation`, `Tool`, `ToolCall`, `AgentResponse`. `AgentResponse.from_message()` parses raw Anthropic API responses.
- **`sauce/llm.py`** — Thin wrapper: `call_llm()` / `call_llm_async()` → `AgentResponse`.
- **`sauce/node.py`** — `Node` dataclass, `NodeType`/`NodeState` enums, `NodeConfig`, `NODE_CONFIG` (model + prompt per type), `TOOLS_FOR_NODE`.
- **`sauce/tree.py`** — `DecompositionTree`: manages the node graph, parent/child wiring, `dump_state()` / `load_state()` for JSON serialization.
- **`sauce/neo.py`** — `Neo`: async execution engine. Semaphore-limited (`max_concurrent_tasks=10`). Accepts `env_directory` to sandbox all file/shell operations.
- **`sauce/tools.py`** — Tool schemas (`Tool` objects) and implementations (`TOOL_REGISTRY`). Includes `ALLOWED_SPAWN` spawn permission table.
- **`sauce/prompts.py`** — Loads system prompts from `.md` files in `sauce/prompts/`.
- **`sauce/viz.py`** — Live terminal visualization using `rich`. Exports `run_with_live_visualization()`.
- **`sauce/tests/viz.py`** — Mocked LLM harness; run this to develop without API calls.

`main.py` is the entry point. `anthro.py` is a scratch file for raw SDK experiments.

### Node types and models

| NodeType   | Model             | Role                                   |
|------------|-------------------|----------------------------------------|
| THINKING   | claude-sonnet-4-6 | Decompose or directly answer a problem |
| CODE       | claude-haiku-4-5  | Implement a specific coding task       |
| TEST       | claude-haiku-4-5  | Verify/test code                       |
| SYNTHESIZE | (no config yet)   | Declared but not wired up              |

Spawn restrictions (`ALLOWED_SPAWN` in `tools.py`): `thinking` may spawn `thinking`, `code`, `synthesize`; `code` may only spawn `test`.

### Execution flow

1. `Neo(tree, env_directory=...)` is constructed. All file/shell tool paths are resolved relative to `env_directory`.
2. `neo.prompt(task)` creates a root `THINKING` node and kicks off scheduling.
3. `Neo.run()` loops: finds `READY` nodes, schedules them as async tasks under the semaphore.
4. `execute_node()` calls `call_llm_async`. On `tool_use` stop, non-spawn tools execute immediately (results injected as tool results); `spawn_subagent` calls create child nodes. On `end_turn`, the node's XML-tagged result is sent to the parent as a tool result.
5. When all of a parent's `active_children` complete, the parent returns to `READY` and continues its own conversation.
6. When every node is `COMPLETED`, `tree.dump_state(path)` can serialize the full tree to JSON.

### Working directories

Each `Node` has a `working_directory` (relative path, always `.` for root). `Neo.spawn_subagent()` resolves the child's `working_directory` relative to the parent's, creates the directory under `env_directory`, and prepends `env_directory` when executing file/shell tools. Agents always see relative paths.

### Optimistic concurrency control

`write_file` uses SHA-256 hashing to detect conflicts: when a node reads a file, its hash is stored in `node.file_versions[path]`. A subsequent write checks if the file has been modified by another agent since the read; if so, it returns a `CONFLICT:` error and the agent must re-read before retrying.

### Visualization metadata

Nodes track:
- **`children_ids`** — Permanent history of all spawned children
- **`active_children`** — Runtime set, decrements as children complete
- **`for_vis`** — Currently displayed children; cleared when new children spawn or tools execute

## Notes

- `ANTHROPIC_API_KEY` must be set in the environment.
- `sandbox/` is the default `env_directory` used by `main.py`; tree state is dumped to `sandbox/state/tree.json`.
- System prompts are `.md` files in `sauce/prompts/`. `thinking_v2.md` is the active thinking prompt.
