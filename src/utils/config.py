"""
Configuration management module for Jira-Todoist sync.

Simple approach: Check environment variables, prompt if not found.
"""

import json
import os
import getpass
from typing import Dict, Any


def get_api_credential(service_name: str, env_var_name: str) -> str:
    """Get API credential from environment variable, .env file, or prompt user"""
    # 1. Check environment variable first
    token = os.getenv(env_var_name)
    if token:
        print(f"✅ Found {service_name} token in environment variable {env_var_name}")
        return token
    
    # 2. Check local .env file
    token = load_from_env_file(env_var_name)
    if token:
        print(f"✅ Found {service_name} token in .env file")
        return token
    
    # 3. If not found, prompt user for input
    print(f"⚠️  {service_name} token not found in environment variables or .env file")
    token = getpass.getpass(f"Enter your {service_name} API token: ").strip()
    
    if not token:
        print(f"❌ {service_name} API token is required!")
        exit(1)
    
    # 4. Save the token to .env file for future use
    save_to_env_file(env_var_name, token)
    print(f"✅ Saved {service_name} token to .env file for future use")
    
    return token


def load_from_env_file(env_var_name: str) -> str:
    """Load a specific environment variable from .env file"""
    env_file = ".env"
    if not os.path.exists(env_file):
        return ""
    
    try:
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith(f"{env_var_name}="):
                    # Extract value after the =
                    value = line.split("=", 1)[1]
                    # Remove quotes if present
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    return value
    except Exception as e:
        print(f"⚠️  Error reading .env file: {e}")
    
    return ""


def save_to_env_file(env_var_name: str, token: str) -> None:
    """Save or update an environment variable in .env file"""
    env_file = ".env"
    lines = []
    token_found = False
    
    # Read existing lines if file exists
    if os.path.exists(env_file):
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except Exception as e:
            print(f"⚠️  Error reading .env file: {e}")
            lines = []
    
    # Update existing token or mark that we need to add it
    for i, line in enumerate(lines):
        if line.strip().startswith(f"{env_var_name}="):
            lines[i] = f"{env_var_name}={token}\n"
            token_found = True
            break
    
    # Add new token if not found
    if not token_found:
        if lines and not lines[-1].endswith('\n'):
            lines.append('\n')
        lines.append(f"{env_var_name}={token}\n")
    
    # Write back to file
    try:
        with open(env_file, "w", encoding="utf-8") as f:
            f.writelines(lines)
        
        # Ensure .env is in .gitignore
        ensure_gitignore_entry()
        
    except Exception as e:
        print(f"⚠️  Error saving to .env file: {e}")


def ensure_gitignore_entry() -> None:
    """Ensure .env is added to .gitignore"""
    gitignore_file = ".gitignore"
    env_entry = ".env"
    
    # Check if .gitignore exists and if .env is already in it
    gitignore_content = ""
    if os.path.exists(gitignore_file):
        try:
            with open(gitignore_file, "r", encoding="utf-8") as f:
                gitignore_content = f.read()
        except Exception:
            pass
    
    # Add .env to .gitignore if not already there
    if env_entry not in gitignore_content:
        try:
            with open(gitignore_file, "a", encoding="utf-8") as f:
                if gitignore_content and not gitignore_content.endswith('\n'):
                    f.write('\n')
                f.write("# Local environment variables\n")
                f.write(".env\n")
            print("✅ Added .env to .gitignore")
        except Exception as e:
            print(f"⚠️  Could not update .gitignore: {e}")


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
