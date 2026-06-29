"""
Agent Configuration
Configuration settings for the multi-agent system
"""

import os
from pathlib import Path

# Workspace directory where agents can create files
AGENT_WORKSPACE_DIR = r"D:\learning\code\website"

# Ensure the workspace directory exists
os.makedirs(AGENT_WORKSPACE_DIR, exist_ok=True)

# Safety settings
ALLOWED_EXTENSIONS = [
    '.py', '.js', '.ts', '.jsx', '.tsx', '.html', '.css', '.scss',
    '.json', '.yaml', '.yml', '.md', '.txt', '.env', '.gitignore',
    '.sql', '.sh', '.bat', '.ps1', '.xml', '.toml', '.ini',
    '.vue', '.svelte', '.php', '.java', '.c', '.cpp', '.h',
    '.go', '.rs', '.rb', '.swift', '.kt', '.dart'
]

# Maximum file size for reading (10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024

# Maximum number of files to create in one operation
MAX_FILES_PER_OPERATION = 50


def is_safe_path(path: str) -> bool:
    """
    Check if a path is safe to access (within allowed directories or workspace)
    
    Args:
        path: Path to check
        
    Returns:
        True if path is safe, False otherwise
    """
    try:
        from .config_store import get_allowed_paths
        
        # Convert to absolute path
        abs_path = os.path.abspath(path)
        allowed_paths = get_allowed_paths()
        
        # Helper for case normalization on Windows
        is_windows = os.name == 'nt'
        def norm_case(p: str) -> str:
            return p.lower() if is_windows else p
            
        abs_path_norm = norm_case(abs_path)
        
        if allowed_paths:
            # If the user has configured specific allowed paths, check if target is inside any of them
            for allowed in allowed_paths:
                allowed_abs = os.path.abspath(allowed)
                allowed_norm = norm_case(allowed_abs)
                if abs_path_norm == allowed_norm:
                    return True
                # Add directory separator to prevent partial string matches
                prefix = allowed_norm if allowed_norm.endswith(os.sep) else allowed_norm + os.sep
                if abs_path_norm.startswith(prefix):
                    return True
            return False
        
        # Fallback to default AGENT_WORKSPACE_DIR
        workspace_path = os.path.abspath(AGENT_WORKSPACE_DIR)
        workspace_norm = norm_case(workspace_path)
        if abs_path_norm == workspace_norm:
            return True
        prefix = workspace_norm if workspace_norm.endswith(os.sep) else workspace_norm + os.sep
        return abs_path_norm.startswith(prefix)
    except Exception:
        return False


def get_workspace_path(relative_path: str = "") -> str:
    """
    Get absolute path within workspace
    
    Args:
        relative_path: Relative path within workspace
        
    Returns:
        Absolute path
    """
    return os.path.join(AGENT_WORKSPACE_DIR, relative_path)


def is_allowed_extension(filename: str) -> bool:
    """
    Check if file extension is allowed
    
    Args:
        filename: Filename to check
        
    Returns:
        True if extension is allowed, False otherwise
    """
    ext = os.path.splitext(filename)[1].lower()
    return ext in ALLOWED_EXTENSIONS or ext == ''

# Model configurations
DEFAULT_MAIN_MODEL = "qwen3.5:9b"
DEFAULT_CODE_MODEL = "qwen3.5:9b"

# Made with Bob

