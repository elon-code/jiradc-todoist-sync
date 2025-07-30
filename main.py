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

from src.utils.config import load_config, get_api_credential, get_server_url, validate_config
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
    
    # Get server URL first (needed for API credential testing)
    print("\n🌐 Getting Jira server URL...")
    server_url_env_var = config.get("api_credentials", {}).get("jira", {}).get("server_url_env_var", "JIRA_SERVER_URL")
    server_url = get_server_url(server_url_env_var)
    
    # Get API credentials and test them (check env vars or prompt)
    print("\n🔑 Checking API credentials...")
    jira_token, jira_username = get_api_credential("Jira", "JIRA_API_TOKEN", server_url)
    todoist_token, _ = get_api_credential("Todoist", "TODOIST_API_TOKEN")
    
    # Store runtime values in config for easy access
    config["_runtime_jira_token"] = jira_token
    config["_runtime_todoist_token"] = todoist_token
    config["_runtime_jira_username"] = jira_username
    config["server_url"] = server_url  # Add server_url to config for compatibility

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
