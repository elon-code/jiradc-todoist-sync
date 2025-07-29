#!/usr/bin/env python3
"""
Jira-Todoist Sync Application

A service that synchronizes Jira tickets with Todoist tasks, keeping your
todo list up-to-date with your assigned issues.
"""

import asyncio
import logging
import sys

from src.utils.config import load_config, get_api_credential
from src.api.jira import get_current_jira_user
from src.sync.service import run_service


async def main():
    """Main function to handle async config loading and run service"""
    config = await load_config()
    
    # Get runtime API tokens (from config or environment)
    jira_token = await get_api_credential(config, "jira", "api_token")
    todoist_token = await get_api_credential(config, "todoist", "todoist_api_token")
    
    # Store runtime tokens in config for easy access
    config["_runtime_jira_token"] = jira_token
    config["_runtime_todoist_token"] = todoist_token
    
    server_url = config["server_url"].rstrip('/')  # Remove trailing slash

    # Configure logging
    debug_mode = config.get("debug", False)  # Enable debug mode based on config
    logging.basicConfig(
        level=logging.DEBUG if debug_mode else logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    
    # Reduce verbosity of third-party libraries in debug mode
    if debug_mode:
        logging.getLogger("aiohttp").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("requests").setLevel(logging.WARNING)

    # Update jira_username to fetch dynamically if not provided in config
    jira_username = config.get("jira_username") or get_current_jira_user(config)
    config["_runtime_jira_username"] = jira_username
    
    # Get sync interval from config
    sync_interval_minutes = config.get("sync_interval_minutes", 5)
    
    # Display startup banner
    print("\n" + "="*60)
    print("🚀 JIRA-TODOIST SYNC SERVICE STARTING")
    print("="*60)
    print(f"📍 Jira Server: {server_url}")
    print(f"👤 Jira User: {jira_username}")
    print(f"🔧 Debug Mode: {'ON' if debug_mode else 'OFF'}")
    print(f"⏰ Sync Interval: {sync_interval_minutes} minute{'s' if sync_interval_minutes != 1 else ''}")
    print(f"📂 Project Name: {config['settings']['project_name']}")
    print("💡 Press Ctrl+C to stop gracefully")
    print("="*60 + "\n")
    
    # Start the service with graceful shutdown handling
    try:
        await run_service(config)
    except KeyboardInterrupt:
        logging.info("Received keyboard interrupt. Shutting down gracefully...")
    except Exception as e:
        logging.error(f"Unexpected error in main: {e}")
        raise
    finally:
        logging.info("Application shutdown complete.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # This handles the case where KeyboardInterrupt bubbles up
        print("\n🛑 Application interrupted by user. Goodbye!")
        sys.exit(0)
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        sys.exit(1)
