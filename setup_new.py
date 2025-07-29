#!/usr/bin/env python3
"""
Jira-Todoist Sync Setup Script

This script helps you get started with the Jira-Todoist sync tool.
It will guide you through setting up your API tokens and configuration.
"""

import asyncio
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.utils.setup import prompt_for_config


async def main():
    """Main setup function"""
    print("🚀 Jira-Todoist Sync Setup")
    print("This script will help you configure your sync tool.\n")
    
    try:
        config = await prompt_for_config()
        print("\n🎉 Setup completed successfully!")
        print("You can now run 'python main_new.py' to start the sync service.")
        
    except KeyboardInterrupt:
        print("\n❌ Setup cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
