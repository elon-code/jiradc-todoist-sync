#!/usr/bin/env python3
"""
Jira-Todoist Sync Application - Simplified Version

A service that synchronizes Jira tickets with Todoist tasks.
Simple approach: Check env vars, prompt if missing.
"""

import asyncio
import logging
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.utils.config_simple import load_config, get_api_credential, validate_config
from src.api.jira import get_current_jira_user
from src.sync.service import run_service


async def main():
    """Main function to handle async config loading and run service"""
    print("🚀 Jira-Todoist Sync Service")
    print("=" * 40)
    
    # Load configuration
    config = load_config()
    
    # Validate configuration
    if not validate_config(config):
        print("❌ Configuration validation failed")
        sys.exit(1)
    
    # Get API credentials (check env vars or prompt)
    print("\n🔑 Checking API credentials...")
    jira_token = get_api_credential("Jira", "JIRA_API_TOKEN")
    todoist_token = get_api_credential("Todoist", "TODOIST_API_TOKEN")
    
    # Store runtime tokens in config for easy access
    config["_runtime_jira_token"] = jira_token
    config["_runtime_todoist_token"] = todoist_token
    
    server_url = config["server_url"].rstrip('/')  # Remove trailing slash

    # Configure logging
    debug_mode = config.get("debug", False)
    logging.basicConfig(
        level=logging.DEBUG if debug_mode else logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    
    # Reduce verbosity of third-party libraries in debug mode
    if debug_mode:
        logging.getLogger("aiohttp").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("requests").setLevel(logging.WARNING)

    # Get Jira username
    print("\n🔍 Getting Jira user info...")
    try:
        jira_username = config.get("jira_username") or get_current_jira_user(config)
        config["_runtime_jira_username"] = jira_username
    except Exception as e:
        print(f"❌ Failed to get Jira user info: {e}")
        print("💡 Please check your Jira server URL and API token")
        sys.exit(1)
    
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
