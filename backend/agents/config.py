"""
Agent Configuration
Configuration settings for the multi-agent system
"""

import os
from pathlib import Path

# Workspace directory where agents can create files
AGENT_WORKSPACE_DIR = r"D:\learning\code\website"

# Screenshots directory for browser automation
SCREENSHOTS_DIR = os.path.join(AGENT_WORKSPACE_DIR, "_screenshots")

# Vision model for UI screenshot analysis
VISION_MODEL = "gemma4:26b"

# Documents directory for presentations and spreadsheets
DOCUMENTS_DIR = os.path.join(AGENT_WORKSPACE_DIR, "_documents")

# Generated images directory
IMAGE_OUTPUT_DIR = os.path.join(AGENT_WORKSPACE_DIR, "_generated_images")

# Default image generation model settings (SDXL 1024x1024)
DEFAULT_IMAGE_MODEL = os.environ.get("IMAGE_MODEL", "stabilityai/stable-diffusion-xl-base-1.0")
DEFAULT_IMAGE_WIDTH = int(os.environ.get("IMAGE_WIDTH", "1024"))
DEFAULT_IMAGE_HEIGHT = int(os.environ.get("IMAGE_HEIGHT", "1024"))

# Ensure the workspace, screenshots, documents, and image directories exist
os.makedirs(AGENT_WORKSPACE_DIR, exist_ok=True)
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
os.makedirs(DOCUMENTS_DIR, exist_ok=True)
os.makedirs(IMAGE_OUTPUT_DIR, exist_ok=True)

# Safety settings
ALLOWED_EXTENSIONS = [
    '.py', '.js', '.ts', '.jsx', '.tsx', '.mjs', '.cjs', '.html', '.css', '.scss', '.pcss',
    '.json', '.yaml', '.yml', '.md', '.txt', '.env', '.gitignore', '.lock',
    '.sql', '.sh', '.bat', '.ps1', '.xml', '.toml', '.ini',
    '.vue', '.svelte', '.php', '.java', '.c', '.cpp', '.h',
    '.go', '.rs', '.rb', '.swift', '.kt', '.dart', '.csv',
    '.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg',
    '.pptx', '.xlsx', '.xls', '.pdf', '.docx'
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
        
        # Combine configured allowed paths with workspace directory
        configured = [p for p in (allowed_paths or []) if p and p.strip()]
        all_allowed = configured if configured else [AGENT_WORKSPACE_DIR]
        
        for allowed in all_allowed:
            if not allowed:
                continue
            allowed_abs = os.path.abspath(allowed)
            allowed_norm = norm_case(allowed_abs)
            if abs_path_norm == allowed_norm:
                return True
            prefix = allowed_norm if allowed_norm.endswith(os.sep) else allowed_norm + os.sep
            if abs_path_norm.startswith(prefix):
                return True
        return False
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
DEFAULT_MAIN_MODEL = "gemma4:26b"
DEFAULT_CODE_MODEL = "granite-code:20b"

# Agent Mode configuration
AGENT_MODE_MODEL = "granite-code:20b"
OLLAMA_KEEP_ALIVE = "1h"
CLAUDE_CODE_MAX_TURNS = 10
CLAUDE_CODE_TIMEOUT = 120  # seconds
CLAUDE_CODE_ALLOWED_TOOLS = ["Read", "Write", "Edit", "MultiEdit", "Glob", "Grep", "LS", "Bash"]
CLAUDE_CODE_DISALLOWED_TOOLS = []  # User-configurable blocklist

def get_current_main_model() -> str:
    try:
        from .config_store import load_config
        config = load_config()
        return config.get("default_main_model", DEFAULT_MAIN_MODEL)
    except Exception:
        return DEFAULT_MAIN_MODEL

def get_current_code_model() -> str:
    try:
        from .config_store import load_config
        config = load_config()
        return config.get("default_code_model", DEFAULT_CODE_MODEL)
    except Exception:
        return DEFAULT_CODE_MODEL

# Made with Bob

