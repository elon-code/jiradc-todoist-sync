"""
Configuration management module for Jira-Todoist sync.

Simple approach: Check environment variables, prompt if not found.
"""

import json
import os
import getpass
import requests
from urllib.parse import urlparse, urlunparse
from typing import Dict, Any


def test_jira_connection(server_url: str, api_token: str) -> tuple[bool, str]:
    """Test if the Jira API token works with the given server URL. Returns (success, username)"""
    try:
        url = f"{server_url}/rest/api/2/myself"
        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
        }
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            user_data = response.json()
            username = user_data.get("name", "Unknown")
            print(f"✅ Successfully connected to Jira as user: {username}")
            return True, username
        else:
            print(f"❌ Jira API test failed: HTTP {response.status_code}")
            return False, ""
    except requests.exceptions.RequestException as e:
        print(f"❌ Connection to Jira failed: {e}")
        return False, ""


def format_server_url(url: str) -> str:
    """Format server URL to ensure it starts with https:// and has no trailing slash"""
    if not url:
        return ""
    
    # Strip whitespace
    url = url.strip()
    
    # Add https:// if no protocol specified
    if not url.startswith(('http://', 'https://')):
        url = f"https://{url}"
    
    # Parse and reconstruct URL to ensure proper formatting
    parsed = urlparse(url)
    
    # Remove trailing slash from path
    path = parsed.path.rstrip('/')
    if not path:
        path = ''
    
    # Reconstruct URL without trailing slash
    formatted_url = urlunparse((
        parsed.scheme,
        parsed.netloc,
        path,
        parsed.params,
        parsed.query,
        parsed.fragment
    ))
    
    return formatted_url


def get_server_url(env_var_name: str = "JIRA_SERVER_URL") -> str:
    """Get Jira server URL from environment variable, .env file, or prompt user"""
    # 1. Check environment variable first
    url = os.getenv(env_var_name)
    if url:
        formatted_url = format_server_url(url)
        print(f"✅ Found Jira server URL in environment variable {env_var_name}")
        return formatted_url
    
    # 2. Check local .env file
    url = load_from_env_file(env_var_name)
    if url:
        formatted_url = format_server_url(url)
        print("✅ Found Jira server URL in .env file")
        return formatted_url
    
    # 3. If not found, prompt user for input
    print("⚠️  Jira server URL not found in environment variables or .env file")
    print("💡 Please enter your Jira server URL (e.g., 'jira.company.com' or 'https://company.atlassian.net')")
    url = input("Enter your Jira server URL: ").strip()
    
    if not url:
        print("❌ Jira server URL is required!")
        exit(1)
    
    # Format the URL
    formatted_url = format_server_url(url)
    
    # 4. Save the URL to .env file for future use
    save_to_env_file(env_var_name, formatted_url)
    print(f"✅ Saved Jira server URL to .env file as: {formatted_url}")
    
    return formatted_url


def get_api_credential(service_name: str, env_var_name: str, server_url: str = None) -> tuple[str, str]:
    """Get API credential from environment variable, .env file, or prompt user. 
    Returns (token, username) for Jira, (token, '') for others"""
    username = ""
    
    # 1. Check environment variable first
    token = os.getenv(env_var_name)
    if token:
        print(f"✅ Found {service_name} token in environment variable {env_var_name}")
        # Test the token if it's Jira and we have a server URL
        if service_name.lower() == "jira" and server_url:
            success, username = test_jira_connection(server_url, token)
            if not success:
                print("⚠️  Environment variable token failed validation. Please enter a new one.")
                token = None
            else:
                return token, username
        else:
            return token, username
    
    # 2. Check local .env file
    if not token:
        token = load_from_env_file(env_var_name)
        if token:
            print(f"✅ Found {service_name} token in .env file")
            # Test the token if it's Jira and we have a server URL
            if service_name.lower() == "jira" and server_url:
                success, username = test_jira_connection(server_url, token)
                if not success:
                    print("⚠️  Saved token failed validation. Please enter a new one.")
                    token = None
                else:
                    return token, username
            else:
                return token, username
    
    # 3. If not found or failed validation, prompt user for input
    if not token:
        print(f"⚠️  {service_name} token not found in environment variables or .env file")
    
    while True:
        token = getpass.getpass(f"Enter your {service_name} API token: ").strip()
        
        if not token:
            print(f"❌ {service_name} API token is required!")
            continue
        
        # Test the token if it's Jira and we have a server URL
        if service_name.lower() == "jira" and server_url:
            success, username = test_jira_connection(server_url, token)
            if success:
                break
            else:
                print("❌ Token validation failed. Please try again.")
                continue
        else:
            break
    
    # 4. Save the token to .env file for future use
    save_to_env_file(env_var_name, token)
    print(f"✅ Saved {service_name} token to .env file for future use")
    
    return token, username


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
        },
        "api_credentials": {
            "jira": {
                "use_env_var": True,
                "env_var_name": "JIRA_API_TOKEN",
                "server_url_env_var": "JIRA_SERVER_URL"
            },
            "todoist": {
                "use_env_var": True,
                "env_var_name": "TODOIST_API_TOKEN"
            }
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
    # No required fields for now since server_url is now handled via environment variables
    # Future validation can be added here if needed
    return True
