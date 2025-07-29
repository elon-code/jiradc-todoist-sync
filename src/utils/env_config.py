"""
Enhanced configuration management with .env file support.

This module adds support for .env files as an alternative to environment variables.
"""

import os
from typing import Dict, Any, Optional

def load_env_file(filepath: str = ".env") -> Dict[str, str]:
    """Load environment variables from a .env file"""
    env_vars = {}
    
    if not os.path.exists(filepath):
        return env_vars
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                
                # Parse KEY=VALUE format
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Remove quotes if present
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    
                    env_vars[key] = value
                else:
                    print(f"⚠️  Invalid line {line_num} in {filepath}: {line}")
    
    except Exception as e:
        print(f"❌ Error reading {filepath}: {e}")
    
    return env_vars

def get_credential_with_env_file(service_name: str, env_var_name: str, config_token: str = "") -> Optional[str]:
    """
    Get API credential from multiple sources in order of preference:
    1. Environment variables
    2. .env file
    3. Config file
    """
    
    # 1. Check environment variables first
    token = os.getenv(env_var_name)
    if token:
        print(f"✅ Found {service_name} token in environment variable {env_var_name}")
        return token
    
    # 2. Check .env file
    env_file_vars = load_env_file()
    if env_var_name in env_file_vars:
        token = env_file_vars[env_var_name]
        if token:
            print(f"✅ Found {service_name} token in .env file")
            return token
    
    # 3. Check config file
    if config_token:
        print(f"✅ Found {service_name} token in config file")
        return config_token
    
    print(f"❌ No {service_name} token found in environment, .env file, or config")
    return None

def create_env_file_template():
    """Create a template .env file"""
    template_content = """# Jira-Todoist Sync Environment Variables
# Copy this file to .env and fill in your actual tokens

# Jira API Token
# Get from: https://id.atlassian.com/manage-profile/security/api-tokens
JIRA_API_TOKEN=your_jira_api_token_here

# Todoist API Token  
# Get from: https://todoist.com/prefs/integrations
TODOIST_API_TOKEN=your_todoist_api_token_here

# Optional: Override config settings
# DEBUG=true
# SYNC_INTERVAL_MINUTES=5
"""
    
    try:
        with open(".env.template", "w", encoding='utf-8') as f:
            f.write(template_content)
        print("✅ Created .env.template file")
        print("💡 Copy .env.template to .env and add your actual tokens")
        return True
    except Exception as e:
        print(f"❌ Error creating .env.template: {e}")
        return False
