"""
Agent Configuration Store
Manages dynamic settings for allowed file paths and enabled tools
"""

import os
import json

CONFIG_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "agents_config.json")

DEFAULT_CONFIG = {
    "agent_tools": {
        "code": ["execute_code", "generate_code", "file_operation", "create_project", "analyze_code", "execute_terminal", "schedule_task"],
        "research": ["web_search", "summarize_text"],
        "analysis": ["analyze_code", "file_operation"]
    },
    "allowed_paths": [],
    "allowed_commands": []
}

_current_config = None


def load_config() -> dict:
    """Load configuration from JSON file or return default"""
    global _current_config
    if _current_config is not None:
        return _current_config

    if os.path.exists(CONFIG_FILE_PATH):
        try:
            with open(CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
                config = json.load(f)
                
                # Merge with default config to ensure completeness
                merged = {
                    "agent_tools": {
                        **DEFAULT_CONFIG["agent_tools"],
                        **config.get("agent_tools", {})
                    },
                    "allowed_paths": config.get("allowed_paths", []),
                    "allowed_commands": config.get("allowed_commands", [])
                }
                _current_config = merged
                return _current_config
        except Exception as e:
            print(f"Error loading agents_config.json: {e}")

    _current_config = {
        "agent_tools": {k: list(v) for k, v in DEFAULT_CONFIG["agent_tools"].items()},
        "allowed_paths": list(DEFAULT_CONFIG["allowed_paths"]),
        "allowed_commands": list(DEFAULT_CONFIG["allowed_commands"])
    }
    return _current_config


def save_config(config: dict) -> None:
    """Save configuration to JSON file"""
    global _current_config
    
    # Normalize paths to absolute paths
    allowed_paths = []
    if "allowed_paths" in config:
        for path in config["allowed_paths"]:
            if path and path.strip():
                # Store absolute normalized paths
                allowed_paths.append(os.path.abspath(path.strip()))
                
    # Normalize allowed commands
    allowed_commands = []
    if "allowed_commands" in config:
        for cmd in config["allowed_commands"]:
            if cmd and cmd.strip():
                allowed_commands.append(cmd.strip())

    updated_config = {
        "agent_tools": config.get("agent_tools", DEFAULT_CONFIG["agent_tools"]),
        "allowed_paths": allowed_paths,
        "allowed_commands": allowed_commands
    }
    
    _current_config = updated_config
    try:
        with open(CONFIG_FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(updated_config, f, indent=2)
    except Exception as e:
        print(f"Error saving agents_config.json: {e}")


def get_enabled_tools_for_agent(agent_type: str) -> list:
    """Get list of enabled tools for a specific agent type"""
    config = load_config()
    return config.get("agent_tools", {}).get(agent_type, [])


def get_allowed_paths() -> list:
    """Get list of user-allowed directories or files"""
    config = load_config()
    return config.get("allowed_paths", [])


def get_allowed_commands() -> list:
    """Get list of user-allowed terminal commands"""
    config = load_config()
    return config.get("allowed_commands", [])


def add_allowed_command(command: str) -> None:
    """Add a command to the allowed commands list and persist"""
    config = load_config()
    allowed = config.get("allowed_commands", [])
    if command not in allowed:
        allowed.append(command)
        config["allowed_commands"] = allowed
        save_config(config)
