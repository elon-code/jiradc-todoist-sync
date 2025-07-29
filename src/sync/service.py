"""
Service runner module.

This module handles the main service loop, scheduling, and graceful shutdown.
"""

import asyncio
import logging
import signal
import sys
from datetime import datetime, timedelta
from typing import Dict, Any

import aiohttp
from aiohttp import TCPConnector

from ..api.jira import get_open_jira_tickets
from ..sync.engine import sync_to_todoist


async def run_service(config: Dict[str, Any]) -> None:
    """Run the sync process as a service, checking at the specified interval."""
    sync_interval_minutes = config.get("sync_interval_minutes", 5)
    sleep_chunk_size = config["settings"]["sleep_chunk_size"]
    connection_pool_size = config["settings"]["connection_pool_size"]
    
    # Create session within running loop to bind to correct event loop
    connector = TCPConnector(limit=connection_pool_size)
    async with aiohttp.ClientSession(connector=connector) as session:
        # Set up graceful shutdown flag
        shutdown_requested = False
        
        def signal_handler():
            nonlocal shutdown_requested
            shutdown_requested = True
            logging.info("Shutdown requested. Finishing current sync and exiting gracefully...")
        
        # Register signal handlers for graceful shutdown
        if sys.platform != "win32":
            # Unix-like systems
            loop = asyncio.get_running_loop()
            for sig in (signal.SIGTERM, signal.SIGINT):
                loop.add_signal_handler(sig, signal_handler)
        else:
            # Windows - use different approach
            signal.signal(signal.SIGINT, lambda s, f: signal_handler())
            signal.signal(signal.SIGTERM, lambda s, f: signal_handler())
        
        while not shutdown_requested:
            sync_start_time = datetime.now()
            logging.info("Starting Jira to Todoist sync...")
            try:
                jira_tickets = await get_open_jira_tickets(config, session)
                logging.debug(f"Jira Tickets: {jira_tickets}")
                await sync_to_todoist(config, jira_tickets, session)
                sync_duration = (datetime.now() - sync_start_time).total_seconds()
                logging.info(f"Sync completed successfully in {sync_duration:.1f} seconds")
            except Exception as e:
                sync_duration = (datetime.now() - sync_start_time).total_seconds()
                logging.error(f"Error during sync (after {sync_duration:.1f}s): {e}")
            
            if shutdown_requested:
                break
                
            next_sync_time = datetime.now().replace(microsecond=0) + timedelta(minutes=sync_interval_minutes)
            logging.info(f"Next sync scheduled for {next_sync_time.strftime('%H:%M:%S')}")
            
            # Sleep in chunks to allow for more responsive shutdown
            total_sleep_seconds = sync_interval_minutes * 60
            sleep_chunk_seconds = min(sleep_chunk_size, total_sleep_seconds)  # Sleep in configured chunks or less
            chunks = int(total_sleep_seconds / sleep_chunk_seconds)
            
            for _ in range(chunks):
                if shutdown_requested:
                    break
                await asyncio.sleep(sleep_chunk_seconds)
            
            # Handle any remaining time if not evenly divisible
            remaining_seconds = total_sleep_seconds % sleep_chunk_seconds
            if remaining_seconds > 0 and not shutdown_requested:
                await asyncio.sleep(remaining_seconds)
        
        logging.info("Sync service shutting down gracefully...")
        return
