#!/usr/bin/env python3
"""
Environment Variable Debug Script

This script helps debug environment variable issues with the Jira-Todoist sync tool.
"""

import os
import sys

def check_environment_variables():
    """Check and display environment variable status"""
    print("🔍 Environment Variable Debug Information")
    print("=" * 50)
    
    # Check for Jira token
    jira_token = os.getenv("JIRA_API_TOKEN")
    print(f"JIRA_API_TOKEN: {'✅ Set' if jira_token else '❌ Not found'}")
    if jira_token:
        print(f"  Length: {len(jira_token)} characters")
        print(f"  Preview: {jira_token[:10]}..." if len(jira_token) > 10 else f"  Value: {jira_token}")
    
    # Check for Todoist token
    todoist_token = os.getenv("TODOIST_API_TOKEN")
    print(f"TODOIST_API_TOKEN: {'✅ Set' if todoist_token else '❌ Not found'}")
    if todoist_token:
        print(f"  Length: {len(todoist_token)} characters")
        print(f"  Preview: {todoist_token[:10]}..." if len(todoist_token) > 10 else f"  Value: {todoist_token}")
    
    print("\n🔍 All API-related environment variables:")
    api_vars = []
    for key, value in os.environ.items():
        if any(term in key.upper() for term in ['API', 'TOKEN', 'JIRA', 'TODOIST']):
            api_vars.append((key, len(value) if value else 0))
    
    if api_vars:
        for key, length in api_vars:
            print(f"  - {key}: {length} characters")
    else:
        print("  No API-related environment variables found")
    
    print(f"\n💡 Current working directory: {os.getcwd()}")
    print(f"💡 Python executable: {sys.executable}")
    
    return jira_token and todoist_token

def set_environment_variables():
    """Guide user through setting environment variables"""
    print("\n🔧 Setting Environment Variables")
    print("=" * 50)
    
    if sys.platform == "win32":
        print("📋 For Windows PowerShell, run these commands:")
        print()
        print("# Set JIRA API Token")
        print('$env:JIRA_API_TOKEN="your_jira_token_here"')
        print()
        print("# Set Todoist API Token") 
        print('$env:TODOIST_API_TOKEN="your_todoist_token_here"')
        print()
        print("# To make them permanent (optional):")
        print('[Environment]::SetEnvironmentVariable("JIRA_API_TOKEN", "your_jira_token_here", "User")')
        print('[Environment]::SetEnvironmentVariable("TODOIST_API_TOKEN", "your_todoist_token_here", "User")')
        print()
        print("⚠️  Note: After setting permanent variables, restart PowerShell/VS Code")
    else:
        print("📋 For Linux/Mac, add to your ~/.bashrc or ~/.zshrc:")
        print()
        print('export JIRA_API_TOKEN="your_jira_token_here"')
        print('export TODOIST_API_TOKEN="your_todoist_token_here"')
        print()
        print("Then run: source ~/.bashrc (or restart terminal)")

if __name__ == "__main__":
    print("🚀 Jira-Todoist Sync - Environment Variable Checker\n")
    
    has_vars = check_environment_variables()
    
    if not has_vars:
        set_environment_variables()
        print("\n❌ Please set the environment variables and run this script again to verify.")
        sys.exit(1)
    else:
        print("\n✅ All environment variables are properly set!")
        print("You can now run the main application: python main_new.py")
        sys.exit(0)
