#!/usr/bin/env python3
"""
Jira-Todoist Sync Setup Script

This script helps you get started with the Jira-Todoist sync tool.
It will guide you through setting up your API tokens and configuration.
"""

import os
import sys
import json
import getpass
import asyncio
import subprocess
import aiohttp
from todoist_api_python.api_async import TodoistAPIAsync

async def test_jira_credentials(server_url, api_token):
    """Test Jira credentials by making a simple API call"""
    try:
        url = f"{server_url}/rest/api/2/myself"
        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    user_data = await response.json()
                    return True, user_data.get("displayName", "Unknown User")
                elif response.status == 401:
                    return False, "Invalid API token or insufficient permissions"
                elif response.status == 404:
                    return False, "Server URL not found - check your Jira server address"
                else:
                    error_text = await response.text()
                    return False, f"HTTP {response.status}: {error_text}"
    except Exception as e:
        return False, f"Connection error: {str(e)}"

async def test_todoist_credentials(api_token):
    """Test Todoist credentials by making a simple API call"""
    try:
        api = TodoistAPIAsync(api_token)
        projects_result = await api.get_projects()
        # Handle both async generator and regular list cases
        if hasattr(projects_result, '__aiter__'):
            # It's an async generator, convert to list
            projects_nested = [p async for p in projects_result]
            # The API returns a list inside the async generator
            project_list = projects_nested[0] if projects_nested and isinstance(projects_nested[0], list) else projects_nested
        else:
            # It's already a list
            project_list = projects_result
            
        return True, f"Found {len(project_list)} projects"
    except Exception as e:
        error_msg = str(e)
        if "401" in error_msg or "Unauthorized" in error_msg:
            return False, "Invalid Todoist API token"
        else:
            return False, f"Error connecting to Todoist: {error_msg}"

def load_config():
    """Load configuration to get server URL"""
    try:
        with open("config.json", "r") as config_file:
            return json.load(config_file)
    except (json.JSONDecodeError, FileNotFoundError):
        return {"server_url": "https://your-jira-instance.atlassian.net"}

def check_environment():
    """Check if required environment variables are set"""
    jira_token = os.getenv("JIRA_API_TOKEN")
    todoist_token = os.getenv("TODOIST_API_TOKEN")
    
    if jira_token and todoist_token:
        print("✅ Environment variables found!")
        print(f"   JIRA_API_TOKEN: {'*' * len(jira_token[:4])}...")
        print(f"   TODOIST_API_TOKEN: {'*' * len(todoist_token[:4])}...")
        return True
    
    return False

async def setup_environment():
    """Guide user through setting up environment variables"""
    print("\n🔧 Setting up API tokens...")
    print("For security, we recommend using environment variables for your API tokens.")
    print("This keeps them out of configuration files and git history.\n")
    
    # Load config to get server URL
    config = load_config()
    server_url = config.get("server_url", "https://your-jira-instance.atlassian.net")
    
    # Get and test Jira API token
    while True:
        jira_token = getpass.getpass("Enter your Jira API token (input hidden): ").strip()
        if not jira_token:
            print("❌ Jira API token is required!")
            continue
            
        print("🔍 Testing Jira credentials...")
        success, message = await test_jira_credentials(server_url, jira_token)
        if success:
            print(f"✅ Jira credentials verified! Connected as: {message}")
            break
        else:
            print(f"❌ Jira credential test failed: {message}")
            retry = input("Would you like to try again? (y/N): ").strip().lower()
            if retry not in ['y', 'yes']:
                return False
    
    # Get and test Todoist API token  
    while True:
        todoist_token = getpass.getpass("Enter your Todoist API token (input hidden): ").strip()
        if not todoist_token:
            print("❌ Todoist API token is required!")
            continue
            
        print("🔍 Testing Todoist credentials...")
        success, message = await test_todoist_credentials(todoist_token)
        if success:
            print(f"✅ Todoist credentials verified! {message}")
            break
        else:
            print(f"❌ Todoist credential test failed: {message}")
            retry = input("Would you like to try again? (y/N): ").strip().lower()
            if retry not in ['y', 'yes']:
                return False
    
    # Automatically set environment variables for current session
    print("\n🔄 Setting environment variables for current session...")
    os.environ["JIRA_API_TOKEN"] = jira_token
    os.environ["TODOIST_API_TOKEN"] = todoist_token
    print("✅ Environment variables set successfully!")
    
    # Ask about making them persistent
    make_persistent = input("\n� Would you like to make these environment variables persistent? (y/N): ").strip().lower()
    
    if make_persistent in ['y', 'yes']:
        if sys.platform == "win32":
            try:
                # Try to set persistent environment variables on Windows
                subprocess.run(['setx', 'JIRA_API_TOKEN', jira_token], check=True, capture_output=True)
                subprocess.run(['setx', 'TODOIST_API_TOKEN', todoist_token], check=True, capture_output=True)
                print("✅ Environment variables saved persistently!")
                print("💡 Note: You may need to restart your terminal for the changes to take effect in new sessions.")
            except subprocess.CalledProcessError as e:
                print(f"⚠️  Could not set persistent environment variables: {e}")
                print("💡 You can set them manually using System Properties > Environment Variables")
        else:
            # For Linux/Mac, show instructions for making them persistent
            print("\n💡 To make these persistent, add the following to your shell profile:")
            shell = os.environ.get('SHELL', '/bin/bash')
            if 'zsh' in shell:
                profile_file = "~/.zshrc"
            elif 'fish' in shell:
                profile_file = "~/.config/fish/config.fish"
            else:
                profile_file = "~/.bashrc"
            
            print(f"   Add to {profile_file}:")
            print(f'   export JIRA_API_TOKEN="{jira_token}"')
            print(f'   export TODOIST_API_TOKEN="{todoist_token}"')
            print(f"\n   Then run: source {profile_file}")
    else:
        print("\n💡 Environment variables are set for this session only.")
        print("   They will need to be set again when you restart your terminal.")
    
    return True

async def main():
    print("🚀 Jira-Todoist Sync Setup")
    print("=" * 40)
    
    if check_environment():
        print("\n✅ You're all set! Run 'python3 main.py' to start syncing.")
        return
    
    print("❌ API tokens not found in environment variables.")
    
    choice = input("\nWould you like help setting them up? (y/N): ").strip().lower()
    if choice in ['y', 'yes']:
        if await setup_environment():
            print("\n🎉 Setup complete! Environment variables are now set.")
            
            # Ask if user wants to start the sync application immediately
            start_now = input("\n🚀 Would you like to start the sync application now? (Y/n): ").strip().lower()
            if start_now not in ['n', 'no']:
                try:
                    print("\n🔄 Starting Jira-Todoist sync application...")
                    # Import and run main application
                    import main
                    await main.main()
                except KeyboardInterrupt:
                    print("\n🛑 Application stopped by user.")
                except ImportError:
                    print("⚠️  Could not import main.py. Please run 'python3 main.py' manually.")
                except Exception as e:
                    print(f"⚠️  Error starting application: {e}")
                    print("💡 Please run 'python3 main.py' manually.")
        else:
            print("\n❌ Setup failed. Please try again.")
    else:
        print("\n💡 Set JIRA_API_TOKEN and TODOIST_API_TOKEN environment variables, then run 'python3 main.py'")

if __name__ == "__main__":
    asyncio.run(main())
