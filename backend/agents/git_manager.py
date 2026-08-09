import logging
import subprocess
import threading
from typing import Optional, Tuple, List, Dict
from .config import AGENT_WORKSPACE_DIR

logger = logging.getLogger(__name__)

class GitManager:
    """Manages Git operations for the agent workspace."""
    
    def __init__(self, workspace_dir: Optional[str] = None) -> None:
        """Initializes the GitManager with a workspace directory."""
        self.workspace_dir = workspace_dir or AGENT_WORKSPACE_DIR
        self._lock = threading.Lock()
        
    def _run_git(self, *args, cwd: Optional[str] = None) -> Tuple[bool, str]:
        """Runs a git command via subprocess.run."""
        command = ["git"] + list(args)
        target_cwd = cwd or self.workspace_dir
        
        try:
            with self._lock:
                result = subprocess.run(
                    command,
                    cwd=target_cwd,
                    capture_output=True,
                    text=True,
                    timeout=30,
                    check=False
                )
            
            output = result.stdout + result.stderr
            return result.returncode == 0, output.strip()
        except FileNotFoundError:
            return False, "Error: git executable not found"
        except subprocess.TimeoutExpired:
            return False, "Error: git command timed out"
        except Exception as e:
            logger.exception(f"Unexpected error running git {args}")
            return False, f"Unexpected error: {str(e)}"
            
    def is_repo(self) -> bool:
        """Checks if the workspace is a git repository."""
        success, _ = self._run_git("rev-parse", "--is-inside-work-tree")
        return success
        
    def init_if_needed(self) -> bool:
        """Initializes a git repository if one does not exist."""
        if self.is_repo():
            return True
            
        success, output = self._run_git("init")
        if not success:
            logger.error(f"Failed to init git repo: {output}")
            return False
            
        # Configure user if not set
        self._run_git("config", "user.name", "SeniorAgent")
        self._run_git("config", "user.email", "agent@local")
        
        # Initial commit
        self._run_git("add", "-A")
        self._run_git("commit", "-m", "Initial commit")
        
        return True
        
    def get_current_hash(self) -> Optional[str]:
        """Gets the short hash of the current HEAD."""
        success, output = self._run_git("rev-parse", "--short", "HEAD")
        return output if success and output else None

    def create_checkpoint(self, message: str = "pre-agent-edit") -> Optional[str]:
        """Creates a git commit checkpoint of current state."""
        self._run_git("add", "-A")
        
        # Check if changes exist (git diff --quiet returns 0 if NO changes, 1 if changes exist)
        success, _ = self._run_git("diff", "--cached", "--quiet")
        if success:
            # No changes
            return self.get_current_hash()
            
        commit_msg = f"[agent-checkpoint] {message}"
        success, output = self._run_git("commit", "-m", commit_msg)
        
        if not success:
            logger.warning(f"Failed to create checkpoint: {output}")
            return None
            
        return self.get_current_hash()
        
    def rollback_to(self, commit_hash: str) -> bool:
        """Rolls back the workspace to a specific commit hash, restoring files."""
        # Checkout files from the specific commit
        success1, _ = self._run_git("checkout", commit_hash, "--", ".")
        
        # Preserve gitignore (it might fail if there isn't one, so we just run it)
        self._run_git("checkout", "HEAD", "--", ".gitignore")
        
        return success1
        
    def get_diff(self, from_hash: Optional[str] = None) -> str:
        """Gets diff, either unstaged or compared to a hash."""
        args = ["diff"]
        if from_hash:
            args.extend([from_hash, "HEAD"])
            
        success, output = self._run_git(*args)
        
        if not success:
            return ""
            
        if len(output) > 5000:
            return output[:5000] + "\n... (truncated)"
        return output
        
    def get_status(self) -> str:
        """Gets git status porcelain with a summary line."""
        success, output = self._run_git("status", "--porcelain")
        if not success:
            return "Failed to get git status"
            
        if not output:
            return "0 files modified, 0 files added, 0 files deleted\n"
            
        lines = output.splitlines()
        modified = sum(1 for line in lines if line.startswith(" M") or line.startswith("M "))
        added = sum(1 for line in lines if line.startswith("A ") or line.startswith("??"))
        deleted = sum(1 for line in lines if line.startswith(" D") or line.startswith("D "))
        
        summary = f"{modified} files modified, {added} files added, {deleted} files deleted"
        return f"{summary}\n\n{output}"
        
    def list_recent_checkpoints(self, count: int = 10) -> List[Dict[str, str]]:
        """Lists recent checkpoint commits."""
        success, output = self._run_git("log", "--oneline", f"-n{count}", "--grep=\\[agent-checkpoint\\]")
        if not success or not output:
            return []
            
        result = []
        for line in output.splitlines():
            parts = line.split(" ", 1)
            if len(parts) == 2:
                result.append({"hash": parts[0], "message": parts[1]})
        return result


_git_manager: Optional[GitManager] = None

def get_git_manager(workspace_dir: Optional[str] = None) -> GitManager:
    """Returns a singleton instance of GitManager."""
    global _git_manager
    if _git_manager is None:
        _git_manager = GitManager(workspace_dir)
    return _git_manager
