import os
import sys
import tempfile
import pytest

# Add parent dir to path to import agents
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.git_manager import GitManager

def test_git_manager_init_and_repo():
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = GitManager(workspace_dir=temp_dir)
        
        # Should not be a repo initially
        assert not manager.is_repo()
        
        # Init repo
        assert manager.init_if_needed()
        
        # Should be a repo now
        assert manager.is_repo()
        
        # Repeated init should return True
        assert manager.init_if_needed()

def test_create_checkpoint_and_diff():
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = GitManager(workspace_dir=temp_dir)
        manager.init_if_needed()
        
        # Write a file
        test_file = os.path.join(temp_dir, "test.txt")
        with open(test_file, "w") as f:
            f.write("initial content")
            
        # Create checkpoint
        hash1 = manager.create_checkpoint("add test file")
        assert hash1 is not None
        
        # Modify file
        with open(test_file, "w") as f:
            f.write("modified content")
            
        # Check diff
        diff = manager.get_diff()
        assert "modified content" in diff
        assert "initial content" in diff
        
        # Create second checkpoint
        hash2 = manager.create_checkpoint("modify test file")
        assert hash2 is not None
        assert hash1 != hash2
        
        # Test checkpoints list
        checkpoints = manager.list_recent_checkpoints()
        assert len(checkpoints) >= 2
        assert any(cp['hash'] == hash1 for cp in checkpoints)

def test_rollback():
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = GitManager(workspace_dir=temp_dir)
        manager.init_if_needed()
        
        test_file = os.path.join(temp_dir, "test.txt")
        
        # State 1
        with open(test_file, "w") as f:
            f.write("state 1")
        hash1 = manager.create_checkpoint("state 1")
        
        # State 2
        with open(test_file, "w") as f:
            f.write("state 2")
        manager.create_checkpoint("state 2")
        
        with open(test_file, "r") as f:
            assert f.read() == "state 2"
            
        # Rollback to state 1
        assert manager.rollback_to(hash1)
        
        with open(test_file, "r") as f:
            assert f.read() == "state 1"

def test_get_status():
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = GitManager(workspace_dir=temp_dir)
        manager.init_if_needed()
        
        test_file = os.path.join(temp_dir, "test.txt")
        with open(test_file, "w") as f:
            f.write("test")
            
        status = manager.get_status()
        assert "1 files added" in status or "?? test.txt" in status
