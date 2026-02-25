"""
Unit tests for optimistic concurrency control in file operations.

Tests that agents can detect when files are modified by other agents
and receive conflict errors, forcing them to re-read before retrying.
"""

import os
import tempfile
from agent import Node, NodeType, DecompositionTree
from models import Conversation
import tools


def test_concurrent_file_writes():
    """Test that concurrent writes to the same file are detected."""
    print("\n" + "="*70)
    print("TEST: Concurrent File Writes with Conflict Detection")
    print("="*70 + "\n")

    # Setup: Create tree and two agents
    tree = DecompositionTree()
    node1 = Node(
        node_id="agent_1",
        node_type=NodeType.CODE,
        conversation=Conversation(),
    )
    node2 = Node(
        node_id="agent_2",
        node_type=NodeType.CODE,
        conversation=Conversation(),
    )
    tree.add_node(node1)
    tree.add_node(node2)

    # Create a temporary test file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.py') as f:
        initial_content = "def hello():\n    print('version 1')\n"
        f.write(initial_content)
        test_file = f.name

    print(f"📄 Created test file: {test_file}")
    print(f"   Initial content: {repr(initial_content)}")

    try:
        # Step 1: Both agents read the same file
        print("\n--- Step 1: Both agents read the file ---")
        content_agent1 = tools._read_file(test_file, tree, "agent_1")
        content_agent2 = tools._read_file(test_file, tree, "agent_2")

        print(f"✓ Agent 1 read: {repr(content_agent1)}")
        print(f"  Version hash stored: {tree.nodes['agent_1'].file_versions[test_file][:8]}...")
        print(f"✓ Agent 2 read: {repr(content_agent2)}")
        print(f"  Version hash stored: {tree.nodes['agent_2'].file_versions[test_file][:8]}...")

        assert content_agent1 == initial_content, "Agent 1 didn't read correct content"
        assert content_agent2 == initial_content, "Agent 2 didn't read correct content"
        assert tree.nodes['agent_1'].file_versions[test_file] == tree.nodes['agent_2'].file_versions[test_file], \
            "Both agents should have same hash"

        # Step 2: Agent 1 writes successfully
        print("\n--- Step 2: Agent 1 writes to the file ---")
        new_content_1 = "def hello():\n    print('version 2 - from agent 1')\n"
        result1 = tools._write_file(test_file, new_content_1, tree, "agent_1")

        print(f"✓ Agent 1 write result: {result1}")
        assert "Wrote" in result1, "Agent 1 write should succeed"
        assert "CONFLICT" not in result1, "Agent 1 should not have conflict"

        # Verify file actually changed
        with open(test_file) as f:
            actual_content = f.read()
        assert actual_content == new_content_1, "File content should be updated"
        print(f"  File now contains: {repr(actual_content)}")

        # Step 3: Agent 2 tries to write (should get CONFLICT!)
        print("\n--- Step 3: Agent 2 tries to write (expects CONFLICT) ---")
        new_content_2 = "def hello():\n    print('version 2 - from agent 2')\n"
        result2 = tools._write_file(test_file, new_content_2, tree, "agent_2")

        print(f"✓ Agent 2 write result: {result2}")

        if "CONFLICT" in result2:
            print("  ✅ CONFLICT DETECTED! Agent 2 was correctly blocked.")
        else:
            print("  ❌ CONFLICT NOT DETECTED! This is a bug.")
            raise AssertionError("Expected conflict but agent 2 write succeeded")

        # Verify file wasn't overwritten
        with open(test_file) as f:
            actual_content = f.read()
        assert actual_content == new_content_1, "File should still have Agent 1's content"

        # Step 4: Agent 2 re-reads and successfully writes
        print("\n--- Step 4: Agent 2 re-reads and retries ---")
        content_agent2_new = tools._read_file(test_file, tree, "agent_2")
        print(f"✓ Agent 2 re-read: {repr(content_agent2_new)}")
        print(f"  New version hash: {tree.nodes['agent_2'].file_versions[test_file][:8]}...")

        assert content_agent2_new == new_content_1, "Agent 2 should see Agent 1's changes"

        # Now write should succeed
        new_content_2_retry = "def hello():\n    print('version 3 - from agent 2 after retry')\n"
        result2_retry = tools._write_file(test_file, new_content_2_retry, tree, "agent_2")

        print(f"✓ Agent 2 retry result: {result2_retry}")
        assert "Wrote" in result2_retry, "Agent 2 retry should succeed"
        assert "CONFLICT" not in result2_retry, "Agent 2 retry should not have conflict"

        # Verify final content
        with open(test_file) as f:
            final_content = f.read()
        assert final_content == new_content_2_retry, "File should have Agent 2's new content"
        print(f"  Final file content: {repr(final_content)}")

        print("\n" + "="*70)
        print("✅ ALL TESTS PASSED! Optimistic concurrency control is working.")
        print("="*70 + "\n")

    finally:
        # Cleanup
        os.unlink(test_file)
        print(f"🗑️  Cleaned up test file: {test_file}")


def test_no_conflict_without_prior_read():
    """Test that writes without prior reads don't trigger false conflicts."""
    print("\n" + "="*70)
    print("TEST: Write Without Prior Read (No False Conflicts)")
    print("="*70 + "\n")

    tree = DecompositionTree()
    node = Node(
        node_id="agent_write_only",
        node_type=NodeType.CODE,
        conversation=Conversation(),
    )
    tree.add_node(node)

    # Create test file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.py') as f:
        f.write("# existing content\n")
        test_file = f.name

    try:
        # Agent writes without reading first - should succeed
        new_content = "# new content without reading\n"
        result = tools._write_file(test_file, new_content, tree, "agent_write_only")

        print(f"✓ Write result: {result}")
        assert "Wrote" in result, "Write without prior read should succeed"
        assert "CONFLICT" not in result, "Should not have false conflict"

        print("✅ No false conflicts when writing without prior read")

    finally:
        os.unlink(test_file)


def test_new_file_creation():
    """Test that creating new files works correctly."""
    print("\n" + "="*70)
    print("TEST: New File Creation")
    print("="*70 + "\n")

    tree = DecompositionTree()
    node = Node(
        node_id="agent_creator",
        node_type=NodeType.CODE,
        conversation=Conversation(),
    )
    tree.add_node(node)

    # Create in temp directory
    test_file = tempfile.mktemp(suffix='.py')

    try:
        # Create new file
        content = "def new_function():\n    pass\n"
        result = tools._write_file(test_file, content, tree, "agent_creator")

        print(f"✓ Create result: {result}")
        assert "Wrote" in result, "New file creation should succeed"
        assert os.path.exists(test_file), "File should exist"

        with open(test_file) as f:
            actual = f.read()
        assert actual == content, "File should have correct content"

        print("✅ New file creation works correctly")

    finally:
        if os.path.exists(test_file):
            os.unlink(test_file)


if __name__ == "__main__":
    print("\n🧪 Running Optimistic Concurrency Control Tests\n")

    test_concurrent_file_writes()
    test_no_conflict_without_prior_read()
    test_new_file_creation()

    print("\n✅ All concurrency tests passed!\n")
