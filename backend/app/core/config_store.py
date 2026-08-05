"""
Agent Configuration Store
Manages dynamic settings for allowed file paths and enabled tools
"""

import os
import json

_possible_config_paths = [
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "config", "agents_config.json"),
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "agents", "agents_config.json"),
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "agents_config.json")
]
CONFIG_FILE_PATH = next((p for p in _possible_config_paths if os.path.exists(p)), _possible_config_paths[0])

DEFAULT_CONFIG = {
    "agent_tools": {
        "code": ["generate_image", "execute_code", "generate_code", "file_operation", "create_project", "analyze_code", "execute_terminal", "schedule_task", "verify_app_browser_console", "browser_open_url", "browser_get_console_errors", "browser_take_screenshot", "browser_vision_audit"],
        "research": ["web_search", "summarize_text"],
        "analysis": ["analyze_code", "file_operation", "verify_app_browser_console", "browser_open_url", "browser_get_console_errors", "browser_take_screenshot", "browser_vision_audit"],
        "business": ["generate_image", "web_search", "fetch_web_page", "generate_presentation", "generate_excel_sheet", "read_excel_sheet", "csv_sheet_operation", "file_operation"]
    },
    "allowed_paths": [],
    "allowed_commands": [],
    "default_main_model": "gemma4:26b",
    "default_code_model": "gemma4:26b",
    "strict_coding_rules": {
        "no_hardcoded_html": "STRICT PROJECT RULE: Never hardcode any HTML files or index.html templates in Python backend files. Code Agent must generate 100% of application files dynamically using LLM tools."
    }
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
                    "allowed_commands": config.get("allowed_commands", []),
                    "default_main_model": config.get("default_main_model", DEFAULT_CONFIG["default_main_model"]),
                    "default_code_model": config.get("default_code_model", DEFAULT_CONFIG["default_code_model"])
                }
                _current_config = merged
                return _current_config
        except Exception as e:
            print(f"Error loading agents_config.json: {e}")

    _current_config = {
        "agent_tools": {k: list(v) for k, v in DEFAULT_CONFIG["agent_tools"].items()},
        "allowed_paths": list(DEFAULT_CONFIG["allowed_paths"]),
        "allowed_commands": list(DEFAULT_CONFIG["allowed_commands"]),
        "default_main_model": DEFAULT_CONFIG["default_main_model"],
        "default_code_model": DEFAULT_CONFIG["default_code_model"]
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
                normalized_path = os.path.abspath(path.strip())
                # Never treat an entire filesystem/drive as a safe zone.
                if os.path.dirname(normalized_path) == normalized_path:
                    continue
                allowed_paths.append(normalized_path)
                
    # Normalize allowed commands
    allowed_commands = []
    if "allowed_commands" in config:
        for cmd in config["allowed_commands"]:
            if cmd and cmd.strip():
                allowed_commands.append(cmd.strip())

    updated_config = {
        "agent_tools": config.get("agent_tools", DEFAULT_CONFIG["agent_tools"]),
        "allowed_paths": allowed_paths,
        "allowed_commands": allowed_commands,
        "default_main_model": config.get("default_main_model", DEFAULT_CONFIG["default_main_model"]),
        "default_code_model": config.get("default_code_model", DEFAULT_CONFIG["default_code_model"])
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
