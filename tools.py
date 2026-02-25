import os
import subprocess
from models import InputSchema, Tool, ToolProperty


# ── Schemas ───────────────────────────────────────────────────────────────────

spawn_subagent = Tool(
    name="spawn_subagent",
    description="Assign a subagent to complete a task.",
    input_schema=InputSchema(
        properties={
            "task": ToolProperty(type="string", description="Task you want completed."),
            "agent_type": ToolProperty(type="string", description="Type of agent to spawn. Must be one of: thinking, code, test, synthesize."),
        },
        required=["task", "agent_type"],
    ),
)

read_file = Tool(
    name="read_file",
    description="Read the contents of a file.",
    input_schema=InputSchema(
        properties={
            "path": ToolProperty(type="string", description="Path to the file to read."),
        },
        required=["path"],
    ),
)

write_file = Tool(
    name="write_file",
    description="Write content to a file, creating it if it doesn't exist.",
    input_schema=InputSchema(
        properties={
            "path": ToolProperty(type="string", description="Path to the file to write."),
            "content": ToolProperty(type="string", description="Content to write to the file."),
        },
        required=["path", "content"],
    ),
)

list_directory = Tool(
    name="list_directory",
    description="List the files and directories at a given path.",
    input_schema=InputSchema(
        properties={
            "path": ToolProperty(type="string", description="Directory path to list. Defaults to current directory."),
        },
        required=[],
    ),
)

run_shell = Tool(
    name="run_shell",
    description="Run a shell command and return its output.",
    input_schema=InputSchema(
        properties={
            "command": ToolProperty(type="string", description="Shell command to run."),
        },
        required=["command"],
    ),
)


# ── Implementations ───────────────────────────────────────────────────────────

def _read_file(path: str) -> str:
    try:
        with open(path) as f:
            return f.read()
    except Exception as e:
        return f"Error: {e}"


def _write_file(path: str, content: str) -> str:
    try:
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(path, "w") as f:
            f.write(content)
        return f"Wrote {len(content)} bytes to {path}"
    except Exception as e:
        return f"Error: {e}"


def _list_directory(path: str = ".") -> str:
    try:
        return "\n".join(sorted(os.listdir(path)))
    except Exception as e:
        return f"Error: {e}"


def _run_shell(command: str) -> str:
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = result.stdout
        if result.stderr:
            output += f"\nstderr:\n{result.stderr}"
        if result.returncode != 0:
            output += f"\nreturn code: {result.returncode}"
        return output or "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: command timed out after 30 seconds"
    except Exception as e:
        return f"Error: {e}"


TOOL_REGISTRY: dict[str, callable] = {
    "read_file":      lambda inp: _read_file(inp["path"]),
    "write_file":     lambda inp: _write_file(inp["path"], inp["content"]),
    "list_directory": lambda inp: _list_directory(inp.get("path", ".")),
    "run_shell":      lambda inp: _run_shell(inp["command"]),
}
