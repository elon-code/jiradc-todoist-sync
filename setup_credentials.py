#!/usr/bin/env python3
"""
Quick Credential Setup

This script provides multiple ways to set up your API credentials.
"""

import os
import sys
import getpass

def main():
    print("🔧 Jira-Todoist Sync - Quick Credential Setup")
    print("=" * 50)
    print("Choose how you'd like to set up your API credentials:")
    print()
    print("1. Environment Variables (current session)")
    print("2. Permanent Environment Variables (Windows)")
    print("3. Create .env file (recommended)")
    print("4. Check current credential status")
    print()
    
    choice = input("Enter your choice (1-4): ").strip()
    
    if choice == "1":
        setup_session_env_vars()
    elif choice == "2":
        setup_permanent_env_vars()
    elif choice == "3":
        setup_env_file()
    elif choice == "4":
        check_credentials()
    else:
        print("❌ Invalid choice. Please run the script again.")

def setup_session_env_vars():
    """Set up environment variables for current session"""
    print("\n🔧 Setting up environment variables for current session...")
    print("⚠️  Note: These will be lost when you close PowerShell/terminal")
    print()
    
    jira_token = getpass.getpass("Enter your Jira API token: ").strip()
    todoist_token = getpass.getpass("Enter your Todoist API token: ").strip()
    
    if jira_token and todoist_token:
        print("\n📋 Run these commands in your PowerShell:")
        print(f'$env:JIRA_API_TOKEN="{jira_token}"')
        print(f'$env:TODOIST_API_TOKEN="{todoist_token}"')
        print()
        print("💡 Copy and paste the commands above into your PowerShell window")
    else:
        print("❌ Both tokens are required.")

def setup_permanent_env_vars():
    """Set up permanent environment variables (Windows)"""
    print("\n🔧 Setting up permanent environment variables...")
    print("⚠️  Note: You'll need to restart PowerShell/VS Code after this")
    print()
    
    jira_token = getpass.getpass("Enter your Jira API token: ").strip()
    todoist_token = getpass.getpass("Enter your Todoist API token: ").strip()
    
    if jira_token and todoist_token:
        print("\n📋 Run these commands in your PowerShell (as Administrator if needed):")
        print(f'[Environment]::SetEnvironmentVariable("JIRA_API_TOKEN", "{jira_token}", "User")')
        print(f'[Environment]::SetEnvironmentVariable("TODOIST_API_TOKEN", "{todoist_token}", "User")')
        print()
        print("💡 Copy and paste the commands above into your PowerShell window")
        print("🔄 Then restart PowerShell/VS Code")
    else:
        print("❌ Both tokens are required.")

def setup_env_file():
    """Create a .env file with credentials"""
    print("\n🔧 Creating .env file...")
    print("💡 This file will be ignored by git for security")
    print()
    
    jira_token = getpass.getpass("Enter your Jira API token: ").strip()
    todoist_token = getpass.getpass("Enter your Todoist API token: ").strip()
    
    if not jira_token or not todoist_token:
        print("❌ Both tokens are required.")
        return
    
    env_content = f"""# Jira-Todoist Sync Environment Variables
# This file contains your API tokens - keep it secure!

JIRA_API_TOKEN={jira_token}
TODOIST_API_TOKEN={todoist_token}

# Optional: Override config settings
# DEBUG=true
# SYNC_INTERVAL_MINUTES=5
"""
    
    try:
        with open(".env", "w", encoding='utf-8') as f:
            f.write(env_content)
        
        print("✅ Created .env file successfully!")
        print("🔒 Make sure .env is in your .gitignore file")
        
        # Create .gitignore entry if it doesn't exist
        gitignore_path = ".gitignore"
        gitignore_content = ""
        
        if os.path.exists(gitignore_path):
            with open(gitignore_path, "r", encoding='utf-8') as f:
                gitignore_content = f.read()
        
        if ".env" not in gitignore_content:
            with open(gitignore_path, "a", encoding='utf-8') as f:
                if gitignore_content and not gitignore_content.endswith('\n'):
                    f.write('\n')
                f.write("# Environment variables\n.env\n")
            print("✅ Added .env to .gitignore")
        
        print("\n🚀 You can now run: python main_new.py")
        
    except Exception as e:
        print(f"❌ Error creating .env file: {e}")

def check_credentials():
    """Check current credential status"""
    print("\n🔍 Checking credential status...")
    
    # Check environment variables
    jira_env = os.getenv("JIRA_API_TOKEN")
    todoist_env = os.getenv("TODOIST_API_TOKEN")
    
    print(f"Environment Variables:")
    print(f"  JIRA_API_TOKEN: {'✅ Set' if jira_env else '❌ Not set'}")
    print(f"  TODOIST_API_TOKEN: {'✅ Set' if todoist_env else '❌ Not set'}")
    
    # Check .env file
    env_file_exists = os.path.exists(".env")
    print(f"\n.env file: {'✅ Exists' if env_file_exists else '❌ Not found'}")
    
    if env_file_exists:
        try:
            with open(".env", "r", encoding='utf-8') as f:
                content = f.read()
                has_jira = "JIRA_API_TOKEN=" in content
                has_todoist = "TODOIST_API_TOKEN=" in content
                print(f"  JIRA_API_TOKEN: {'✅ Found' if has_jira else '❌ Missing'}")
                print(f"  TODOIST_API_TOKEN: {'✅ Found' if has_todoist else '❌ Missing'}")
        except Exception as e:
            print(f"  ❌ Error reading .env file: {e}")
    
    # Check config.json
    config_exists = os.path.exists("config.json")
    print(f"\nconfig.json: {'✅ Exists' if config_exists else '❌ Not found'}")
    
    if config_exists:
        try:
            import json
            with open("config.json", "r", encoding='utf-8') as f:
                config = json.load(f)
                has_jira_config = bool(config.get("api_token"))
                has_todoist_config = bool(config.get("todoist_api_token"))
                print(f"  JIRA token in config: {'✅ Found' if has_jira_config else '❌ Missing'}")
                print(f"  TODOIST token in config: {'✅ Found' if has_todoist_config else '❌ Missing'}")
        except Exception as e:
            print(f"  ❌ Error reading config.json: {e}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n❌ Setup cancelled by user.")
        sys.exit(1)
