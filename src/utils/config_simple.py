"""
Configuration management module for Jira-Todoist sync.

Simple approach: Check environment variables, prompt if not found.
"""

import json
import os
import getpass
from typing import Dict, Any


def get_api_credential(service_name: str, env_var_name: str) -> str:
    """Get API credential from environment variable or prompt user"""
    # 1. Check environment variable first
    token = os.getenv(env_var_name)
    if token:
        print(f"✅ Found {service_name} token in environment variable {env_var_name}")
        return token
    
    # 2. If not found, prompt user for input
    print(f"⚠️  Environment variable {env_var_name} not found")
    token = getpass.getpass(f"Enter your {service_name} API token: ").strip()
    
    if not token:
        print(f"❌ {service_name} API token is required!")
        exit(1)
    
    return token


def load_config() -> Dict[str, Any]:
    """Load configuration from config.json"""
    CONFIG_FILE = "config.json"
    
    if not os.path.exists(CONFIG_FILE):
        print(f"❌ {CONFIG_FILE} not found.")
        print("Creating default configuration...")
        config = create_default_config()
        save_config(config)
        return config
    
    try:
        with open(CONFIG_FILE, "r") as config_file:
            config = json.load(config_file)
        print(f"✅ Loaded configuration from {CONFIG_FILE}")
        return config
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"❌ Error reading {CONFIG_FILE}: {e}")
        print("Creating default configuration...")
        config = create_default_config()
        save_config(config)
        return config


def create_default_config() -> Dict[str, Any]:
    """Create default configuration"""
    return {
        "server_url": "https://your-jira-instance.atlassian.net",
        "debug": False,
        "sync_interval_minutes": 5,
        "jira_username": "",
        "settings": {
            "default_priority": 4,
            "sleep_chunk_size": 10,
            "project_name": "Jira Tickets",
            "connection_pool_size": 20,
            "priority_mapping": {
                "Blocker": 1,
                "Critical": 1,
                "Major": 2,
                "Minor": 3,
                "Trivial": 4
            },
            "skip_statuses": ["Blocked"],
            "exclude_statuses": ["Blocked", "Canceled", "Cancelled", "Backlog", "Done"]
        }
    }


def save_config(config: Dict[str, Any], filename: str = "config.json") -> None:
    """Save configuration to file"""
    try:
        with open(filename, "w") as config_file:
            json.dump(config, config_file, indent=2)
        print(f"✅ Configuration saved to {filename}")
    except Exception as e:
        print(f"❌ Error saving configuration: {e}")
        exit(1)


def validate_config(config: Dict[str, Any]) -> bool:
    """Validate required configuration fields"""
    required_fields = ["server_url"]
    missing_fields = []

    for field in required_fields:
        if not config.get(field) or config[field].strip() == "":
            missing_fields.append(field)

    if missing_fields:
        print(f"❌ Missing required configuration fields:")
        for field in missing_fields:
            print(f"   - {field}")
        print(f"💡 Please update your config.json file")
        return False
    
    return True
