"""
Setup and configuration prompt module.

This module handles interactive setup and configuration for new installations.
"""

import os
import getpass
import urllib.parse
from typing import Dict, Any

from ..auth.credentials import test_jira_credentials, test_todoist_credentials
from .config import get_default_settings, get_default_api_credentials, save_config


async def prompt_for_config() -> Dict[str, Any]:
    """Prompt user for configuration values and save to config.json"""
    print("🔧 Setting up Jira-Todoist Sync Configuration")
    print("=" * 50)
    
    config = {
        "settings": get_default_settings(),
        "api_credentials": get_default_api_credentials()
    }
    
    # Prompt for server URL
    while True:
        server_url = input("Enter your Jira server URL: ").strip()
        if server_url:
            # Auto-add https:// if no protocol specified
            if not server_url.startswith(('http://', 'https://')):
                server_url = f"https://{server_url}"
            
            # Parse and validate URL
            try:
                parsed = urllib.parse.urlparse(server_url)
                if not parsed.netloc or not parsed.scheme:
                    raise ValueError("Invalid URL")
                
                # Reconstruct clean URL
                clean_url = f"{parsed.scheme}://{parsed.netloc}"
                config["server_url"] = clean_url.rstrip('/')
                print(f"✅ Server URL set to: {config['server_url']}")
                break
                
            except ValueError:
                print("❌ Invalid URL. Please try again.")
                continue
                
        print("❌ Server URL is required. Please try again.")
    
    # Prompt for Jira API token with validation
    while True:
        print("\n🔑 Jira API Token Setup:")
        print("1. Enter token directly")
        print("2. Use environment variable (JIRA_API_TOKEN)")
        choice = input("Choose option (1 or 2): ").strip()
        
        if choice == "2":
            config["api_credentials"]["jira"]["use_env_var"] = True
            env_token = os.getenv("JIRA_API_TOKEN")
            if env_token:
                print("🔍 Testing Jira credentials from environment...")
                success, message = await test_jira_credentials(config["server_url"], env_token)
                if success:
                    print(f"✅ Jira credentials verified! Connected as: {message}")
                    config["api_token"] = ""  # Don't store in config when using env var
                    break
                else:
                    print(f"❌ Jira credential test failed: {message}")
                    retry = input("Would you like to enter token directly instead? (y/N): ").strip().lower()
                    if retry not in ['y', 'yes']:
                        print("⚠️  Continuing with environment variable setup...")
                        config["api_token"] = ""
                        break
            else:
                print("❌ Environment variable JIRA_API_TOKEN not found.")
                continue
        else:
            config["api_credentials"]["jira"]["use_env_var"] = False
            api_token = getpass.getpass("Enter your Jira API token (input will be hidden): ").strip()
            if api_token:
                print("🔍 Testing Jira credentials...")
                success, message = await test_jira_credentials(config["server_url"], api_token)
                if success:
                    print(f"✅ Jira credentials verified! Connected as: {message}")
                    config["api_token"] = api_token
                    break
                else:
                    print(f"❌ Jira credential test failed: {message}")
                    retry = input("Would you like to try again? (y/N): ").strip().lower()
                    if retry not in ['y', 'yes']:
                        print("⚠️  Continuing with unverified credentials...")
                        config["api_token"] = api_token
                        break
            else:
                print("❌ Jira API token is required. Please try again.")
    
    # Prompt for Todoist API token with validation
    while True:
        print("\n🔑 Todoist API Token Setup:")
        print("1. Enter token directly")
        print("2. Use environment variable (TODOIST_API_TOKEN)")
        choice = input("Choose option (1 or 2): ").strip()
        
        if choice == "2":
            config["api_credentials"]["todoist"]["use_env_var"] = True
            env_token = os.getenv("TODOIST_API_TOKEN")
            if env_token:
                print("🔍 Testing Todoist credentials from environment...")
                success, message = await test_todoist_credentials(env_token)
                if success:
                    print(f"✅ Todoist credentials verified! {message}")
                    config["todoist_api_token"] = ""  # Don't store in config when using env var
                    break
                else:
                    print(f"❌ Todoist credential test failed: {message}")
                    retry = input("Would you like to enter token directly instead? (y/N): ").strip().lower()
                    if retry not in ['y', 'yes']:
                        print("⚠️  Continuing with environment variable setup...")
                        config["todoist_api_token"] = ""
                        break
            else:
                print("❌ Environment variable TODOIST_API_TOKEN not found.")
                continue
        else:
            config["api_credentials"]["todoist"]["use_env_var"] = False
            todoist_token = getpass.getpass("Enter your Todoist API token (input will be hidden): ").strip()
            if todoist_token:
                print("🔍 Testing Todoist credentials...")
                success, message = await test_todoist_credentials(todoist_token)
                if success:
                    print(f"✅ Todoist credentials verified! {message}")
                    config["todoist_api_token"] = todoist_token
                    break
                else:
                    print(f"❌ Todoist credential test failed: {message}")
                    retry = input("Would you like to try again? (y/N): ").strip().lower()
                    if retry not in ['y', 'yes']:
                        print("⚠️  Continuing with unverified credentials...")
                        config["todoist_api_token"] = todoist_token
                        break
            else:
                print("❌ Todoist API token is required. Please try again.")
    
    # Prompt for debug mode (optional)
    debug_input = input("Enable debug logging? (y/N): ").strip().lower()
    config["debug"] = debug_input in ['y', 'yes', 'true']
    
    # Prompt for sync interval (optional)
    default_interval = 5  # Default sync interval
    while True:
        interval_input = input(f"Sync interval in minutes (default: {default_interval}): ").strip()
        if not interval_input:
            config["sync_interval_minutes"] = default_interval
            break
        try:
            interval = int(interval_input)
            if interval < 1:
                print("❌ Sync interval must be at least 1 minute.")
                continue
            config["sync_interval_minutes"] = interval
            break
        except ValueError:
            print("❌ Please enter a valid number.")
    
    # Save configuration
    save_config(config)
    return config
