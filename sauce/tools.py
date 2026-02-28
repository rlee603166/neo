import os
import subprocess
import hashlib
from sauce.models import InputSchema, Tool, ToolProperty


# ── Schemas ───────────────────────────────────────────────────────────────────


spawn_subagent = Tool(
    name="spawn_subagent",
    description="Assign a subagent to complete a task. You can optionally specify a working directory for the subagent.",
    input_schema=InputSchema(
        properties={
            "task": ToolProperty(type="string", description="Task you want completed."),
            "agent_type": ToolProperty(type="string", description="Type of agent to spawn. Must be one of: thinking, code, test, synthesize."),
            "working_directory": ToolProperty(type="string", description="Optional: Working directory for the subagent. If not specified, inherits parent's directory. The directory will be created if it doesn't exist."),
        },
        required=["task", "agent_type"],
    ),
)

# Which agent types each caller is permitted to spawn.
ALLOWED_SPAWN: dict[str, list[str]] = {
    "thinking": ["thinking", "code", "synthesize"],
    "code":     ["test"],
}

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

def _read_file(path: str, tree=None, node_id: str = None, working_directory: str = ".") -> str:
    try:
        # Resolve path relative to working directory if it's not absolute
        if not os.path.isabs(path):
            path = os.path.join(working_directory, path)

        with open(path) as f:
            content = f.read()

        # Track file version for optimistic concurrency control
        if tree and node_id:
            content_hash = hashlib.sha256(content.encode()).hexdigest()
            tree.nodes[node_id].file_versions[path] = content_hash

        return content
    except Exception as e:
        return f"Error: {e}"


def _write_file(path: str, content: str, tree=None, node_id: str = None, working_directory: str = ".") -> str:
    try:
        # Keep original path for display
        display_path = path

        # Resolve path relative to working directory if it's not absolute
        if not os.path.isabs(path):
            path = os.path.join(working_directory, path)

        # Check for file conflicts (optimistic concurrency control)
        if tree and node_id and path in tree.nodes[node_id].file_versions:
            # File was previously read by this agent - check if it changed
            if os.path.exists(path):
                with open(path) as f:
                    current_content = f.read()
                current_hash = hashlib.sha256(current_content.encode()).hexdigest()
                expected_hash = tree.nodes[node_id].file_versions[path]

                if current_hash != expected_hash:
                    return (
                        f"CONFLICT: File '{display_path}' was modified by another agent since you read it. "
                        f"Please re-read the file to see the latest changes and try again."
                    )

        # No conflict - proceed with write
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(path, "w") as f:
            f.write(content)

        # Update the file version after successful write
        if tree and node_id:
            new_hash = hashlib.sha256(content.encode()).hexdigest()
            tree.nodes[node_id].file_versions[path] = new_hash

        return f"Wrote {len(content)} bytes to {display_path}"
    except Exception as e:
        return f"Error: {e}"


def _list_directory(path: str = ".", tree=None, node_id: str = None, working_directory: str = ".") -> str:
    try:
        # Resolve path relative to working directory if it's not absolute
        if not os.path.isabs(path):
            path = os.path.join(working_directory, path)

        return "\n".join(sorted(os.listdir(path)))
    except Exception as e:
        return f"Error: {e}"


def _run_shell(command: str, tree=None, node_id: str = None, working_directory: str = ".") -> str:
    try:
        env = os.environ.copy()
        env["CI"] = "true"
        env["DEBIAN_FRONTEND"] = "noninteractive"
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            stdin=subprocess.DEVNULL,
            text=True,
            timeout=30,
            cwd=working_directory,
            env=env,
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
    "read_file":      lambda inp, tree=None, node_id=None, working_directory=".": _read_file(inp["path"], tree, node_id, working_directory),
    "write_file":     lambda inp, tree=None, node_id=None, working_directory=".": _write_file(inp["path"], inp["content"], tree, node_id, working_directory),
    "list_directory": lambda inp, tree=None, node_id=None, working_directory=".": _list_directory(inp.get("path", "."), tree, node_id, working_directory),
    "run_shell":      lambda inp, tree=None, node_id=None, working_directory=".": _run_shell(inp["command"], tree, node_id, working_directory),
}
