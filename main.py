import asyncio
import json
import logging
import os
import getpass
import urllib.parse
import requests
import aiohttp
import signal
import sys
from datetime import datetime, date, timedelta
from aiohttp import TCPConnector
from requests.adapters import HTTPAdapter
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

async def prompt_for_config():
    """Prompt user for configuration values and save to config.json"""
    print("🔧 Setting up Jira-Todoist Sync Configuration")
    print("=" * 50)
    
    config = {}
    
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
    while True:
        interval_input = input("Sync interval in minutes (default: 5): ").strip()
        if not interval_input:
            config["sync_interval_minutes"] = 5
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
    try:
        with open(CONFIG_FILE, "w") as config_file:
            json.dump(config, config_file, indent=2)
        print(f"\n✅ Configuration saved to {CONFIG_FILE}")
        return config
    except Exception as e:
        print(f"❌ Error saving configuration: {e}")
        exit(1)

async def load_config():
    """Load or create configuration"""
    if not os.path.exists(CONFIG_FILE):
        print(f"❌ {CONFIG_FILE} not found.")
        return await prompt_for_config()
    else:
        # Load configuration from config.json
        try:
            with open(CONFIG_FILE, "r") as config_file:
                config = json.load(config_file)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            print(f"❌ Error reading {CONFIG_FILE}: {e}")
            return await prompt_for_config()

        # Validate required configuration values
        required_fields = ["server_url", "api_token", "todoist_api_token"]
        missing_fields = []

        for field in required_fields:
            if not config.get(field) or config[field].strip() == "":
                missing_fields.append(field)

        if missing_fields:
            print(f"❌ Missing required configuration fields in {CONFIG_FILE}:")
            for field in missing_fields:
                print(f"   - {field}")
            print("\n🔧 Let's set up your configuration:")
            return await prompt_for_config()
        
        return config

# Configuration constants
CONFIG_FILE = "config.json"
DEFAULT_SYNC_INTERVAL = 5  # minutes
DEFAULT_PRIORITY = 4
SLEEP_CHUNK_SIZE = 10  # seconds
PROJECT_NAME = "Jira Tickets"
CONNECTION_POOL_SIZE = 20

# Priority mappings
JIRA_TO_TODOIST_PRIORITY = {
    "Blocker": 1,
    "Critical": 1, 
    "Major": 2,
    "Minor": 3,
    "Trivial": 4,
}

# Jira statuses to skip
SKIP_STATUSES = {"Blocked"}
EXCLUDE_STATUSES = ["Blocked", "Canceled", "Cancelled", "Backlog", "Done"]

def get_current_jira_user():
    """Fetch the current Jira user based on the API token."""
    url = f"{JIRA_SERVER_URL}/rest/api/2/myself"
    headers = {
        "Authorization": f"Bearer {JIRA_API_TOKEN}",
        "Content-Type": "application/json",
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    user = response.json()["name"]
    logging.info(f"Autofound Jira username: {user}")  # Log the autofound username
    logging.debug(f"Fetched current Jira user: {response.json()}")
    return user

async def get_green_resolution_statuses():
    """Fetch all Jira statuses and identify green resolution statuses asynchronously."""
    url = f"{JIRA_SERVER_URL}/rest/api/2/status"
    headers = {
        "Authorization": f"Bearer {JIRA_API_TOKEN}",
        "Content-Type": "application/json"
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status != 200:
                logging.error(f"Error fetching Jira statuses: {response.status} - {await response.text()}")
                response.raise_for_status()
            statuses = await response.json()
            green_statuses = [status["name"] for status in statuses if status.get("statusCategory", {}).get("key") == "done"]
            logging.debug(f"Green resolution statuses: {green_statuses}")
            return green_statuses

async def get_open_jira_tickets():
    """Fetch open Jira tickets assigned to the user, including Jira Service Management tasks."""
    url = f"{JIRA_SERVER_URL}/rest/api/2/search"
    headers = {
        "Authorization": f"Bearer {JIRA_API_TOKEN}",
        "Content-Type": "application/json",
    }
    # Use resolution filter to only fetch unresolved tickets and exclude blocked and cancelled
    jql_query = f'assignee = "{JIRA_USERNAME}" AND resolution = Unresolved AND status NOT IN ("Blocked","Canceled","Cancelled","Backlog","Done")'
    logging.debug(f"Using JQL Query: {jql_query}")
    query = {
        "jql": jql_query,
        "fields": "summary,duedate,priority,status,issuetype,description",  # Include description field
    }
    # Use shared aiohttp session
    async with shared_session.get(url, headers=headers, params=query) as response:
        if response.status != 200:
            logging.error(
                f"Error fetching Jira tickets: {response.status} - {await response.text()}"
            )
            response.raise_for_status()
        response_json = await response.json()
        # Only log the response in debug mode if it's a small number of tickets
        if DEBUG_MODE and len(response_json.get("issues", [])) <= 5:
            logging.debug(f"Jira API Response: {json.dumps(response_json, indent=2)}")
        elif DEBUG_MODE:
            logging.debug(f"Jira API Response: Found {len(response_json.get('issues', []))} tickets (response too large to log)")
        issues = response_json.get("issues", [])
    if not issues:
        logging.info("No tickets found.")
    else:
        logging.info(f"Found {len(issues)} tickets assigned to {JIRA_USERNAME}.")
    
    # Debug log just the ticket keys and summaries for overview
    if DEBUG_MODE and issues:
        ticket_summary = [(issue["key"], issue["fields"]["summary"][:50] + "..." if len(issue["fields"]["summary"]) > 50 else issue["fields"]["summary"]) for issue in issues[:5]]
        logging.debug(f"First 5 tickets: {ticket_summary}")
        if len(issues) > 5:
            logging.debug(f"... and {len(issues) - 5} more tickets")
    
    return [
        {
            "key": issue["key"],
            "summary": issue["fields"]["summary"],
            "due_date": issue["fields"].get("duedate"),
            "priority": issue["fields"].get("priority", {}).get("name"),
            "status": issue["fields"].get("status", {}).get("name"),
            "issuetype": issue["fields"].get("issuetype", {}).get("name"),
            "description": issue["fields"].get("description"),  # Fetch description
        }
        for issue in issues
    ]


async def get_jira_comments(ticket_key):
    """Fetch comments for a Jira ticket."""
    url = f"{JIRA_SERVER_URL}/rest/api/2/issue/{ticket_key}/comment"
    headers = {
        "Authorization": f"Bearer {JIRA_API_TOKEN}",
        "Content-Type": "application/json",
    }
    # Use shared aiohttp session
    async with shared_session.get(url, headers=headers) as response:
        if response.status != 200:
            logging.error(
                f"Error fetching comments for {ticket_key}: {response.status} - {await response.text()}"
            )
            return []
        response_json = await response.json()
        comments = response_json.get("comments", [])
        return [comment["body"] for comment in comments]


async def get_todoist_comments(api, task_id):
    """Fetch comments for a Todoist task."""
    try:
        comments_result = await api.get_comments(task_id=task_id)
        # Handle both async generator and regular list cases
        if hasattr(comments_result, '__aiter__'):
            # It's an async generator, convert to list
            comments_nested = [comment async for comment in comments_result]
            # The API returns a list inside the async generator
            comments = comments_nested[0] if comments_nested and isinstance(comments_nested[0], list) else comments_nested
        else:
            # It's already a list
            comments = comments_result
            
        # Return a mapping of comment content to its id for lookup
        return {comment.content: comment.id for comment in comments}
    except Exception as error:
        logging.error(f"Failed to fetch comments for task {task_id}: {error}")
        return {}


async def sync_todoist_comments(api, task_id, jira_comments):
    """Sync Jira comments with Todoist comments."""
    todoist_comments = await get_todoist_comments(api, task_id)
    
    changes_made = 0
    
    # Normalize comments for comparison by stripping whitespace and converting to lowercase
    def normalize_comment(comment):
        if not comment:
            return ""
        return comment.strip().lower()
    
    # Create normalized versions for comparison
    normalized_jira_comments = {normalize_comment(comment): comment for comment in jira_comments if comment and comment.strip()}
    normalized_todoist_comments = {normalize_comment(content): (content, comment_id) for content, comment_id in todoist_comments.items() if content and content.strip()}

    # Add comments from Jira that don't exist in Todoist
    for normalized_jira, original_jira in normalized_jira_comments.items():
        if normalized_jira not in normalized_todoist_comments:
            try:
                await api.add_comment(content=original_jira, task_id=task_id)
                logging.debug(f"Added new comment to task {task_id}")
                changes_made += 1
            except Exception as error:
                logging.error(
                    f"Failed to add comment to task {task_id}. Error: {error}"
                )

    # Delete comments in Todoist that are no longer in Jira
    for normalized_todoist, (original_todoist, comment_id) in normalized_todoist_comments.items():
        if normalized_todoist not in normalized_jira_comments:
            try:
                await api.delete_comment(comment_id=comment_id)
                logging.debug(f"Deleted comment from task {task_id}")
                changes_made += 1
            except Exception as error:
                logging.error(
                    f"Failed to delete comment from task {task_id}. Error: {error}"
                )
    
    # Only log if there were actual changes
    if changes_made > 0:
        logging.info(f"Synced {changes_made} comment changes for task {task_id}")
    elif DEBUG_MODE:
        logging.debug(f"No comment changes needed for task {task_id}")


async def sync_to_todoist(jira_tickets):
    """Sync Jira tickets and comments to Todoist asynchronously."""
    # Use a dedicated synchronous requests.Session for Todoist calls
    todoist_session = requests.Session()
    # Increase connection pool size for Todoist API and block when full
    adapter = HTTPAdapter(pool_connections=20, pool_maxsize=20, pool_block=True)
    todoist_session.mount("https://api.todoist.com/", adapter)
    todoist_session.mount("http://api.todoist.com/", adapter)
    
    try:
        api = TodoistAPIAsync(TODOIST_API_TOKEN, session=todoist_session)
        project_name = "Jira Tickets"
        
        # Get or create project
        projects_result = await api.get_projects()
        # Handle both async generator and regular list cases
        if hasattr(projects_result, '__aiter__'):
            # It's an async generator, convert to list
            projects_nested = [p async for p in projects_result]
            # The API returns a list inside the async generator
            projects = projects_nested[0] if projects_nested and isinstance(projects_nested[0], list) else projects_nested
        else:
            # It's already a list
            projects = projects_result
        
        jira_project = next((p for p in projects if p.name == project_name), None)
        if not jira_project:
            jira_project = await api.add_project(name=project_name)
            logging.info(f"Created project: {project_name}")
        else:
            logging.info(f"Using existing project: {project_name}")

            # Get existing tasks
            tasks_result = await api.get_tasks(project_id=jira_project.id)
            # Handle both async generator and regular list cases
            if hasattr(tasks_result, '__aiter__'):
                # It's an async generator, convert to list
                tasks_nested = [task async for task in tasks_result]
                # The API returns a list inside the async generator
                existing_tasks = tasks_nested[0] if tasks_nested and isinstance(tasks_nested[0], list) else tasks_nested
            else:
                # It's already a list
                existing_tasks = tasks_result
                
            # Normalize task keys by stripping whitespace and ensuring consistent formatting
            existing_task_map = {}
            for task in existing_tasks:
                if ":" in task.content:
                    jira_key = task.content.split(":")[0].strip()
                    existing_task_map[jira_key] = task

            # Prepare batch updates, additions, and deletions
            tasks_to_update = []
            tasks_to_delete = []

            jira_ticket_keys = {ticket["key"] for ticket in jira_tickets}

            # Identify tasks to delete (tasks that no longer exist in Jira)
            for task_key, task in existing_task_map.items():
                if task_key not in jira_ticket_keys:
                    tasks_to_delete.append(task.id)
                    logging.debug(f"Marked task for deletion: {task_key} (Task ID: {task.id})")

            for ticket in jira_tickets:
                if ticket["status"] in {"Blocked"}:  # Skip blocked tickets
                    continue

                task_content = f"{ticket['key']}: {ticket['summary']}".strip()
                task_due_date = ticket["due_date"]
                # Convert due_date to proper format if it exists
                if task_due_date:
                    # Ensure due_date is a date object for Todoist API
                    if isinstance(task_due_date, str):
                        # Try to parse and convert to date object
                        try:
                            # Try parsing as YYYY-MM-DD first
                            parsed_date = datetime.strptime(task_due_date, '%Y-%m-%d')
                            task_due_date = parsed_date.date()  # Convert to date object
                        except ValueError:
                            try:
                                # Try parsing as ISO format (YYYY-MM-DDTHH:MM:SS)
                                parsed_date = datetime.fromisoformat(task_due_date.replace('Z', '+00:00'))
                                task_due_date = parsed_date.date()  # Convert to date object
                            except ValueError:
                                # If all parsing fails, set to None
                                logging.debug(f"Could not parse due date '{task_due_date}' for ticket {ticket['key']}, setting to None")
                                task_due_date = None
                    else:
                        # If not a string, set to None
                        logging.debug(f"Due date for ticket {ticket['key']} is not a string: {type(task_due_date)} = {task_due_date}, setting to None")
                        task_due_date = None
                
                # Debug logging to see what we're actually passing
                if DEBUG_MODE:
                    logging.debug(f"Ticket {ticket['key']}: task_due_date = {task_due_date} (type: {type(task_due_date)})")
                
                task_priority = 4  # Default priority
                jira_link = f"{JIRA_SERVER_URL}/browse/{ticket['key']}"
                comments = await get_jira_comments(ticket["key"])  # Fetch comments
                task_description = f"{jira_link}\n\n{ticket.get('description', '') or ''}"  # Add link and description

                if ticket["priority"]:
                    priority_mapping = {
                        "Blocker": 1,
                        "Critical": 1,
                        "Major": 2,
                        "Minor": 3,
                        "Trivial": 4,
                    }
                    jira_priority = priority_mapping.get(ticket["priority"], 4)
                    # Invert the priority for Todoist
                    task_priority = 5 - jira_priority
                    logging.debug(
                        f"Ticket {ticket['key']} has Jira priority '{ticket['priority']}' mapped to Todoist priority {task_priority}"
                    )

                if ticket["key"] in existing_task_map:
                    # Check if existing task needs updating
                    existing_task = existing_task_map[ticket["key"]]
                    needs_update = False
                    update_payload = {"task_id": existing_task.id}
                    
                    # Check if content changed
                    if existing_task.content != task_content:
                        update_payload["content"] = task_content
                        needs_update = True
                    
                    # Check if priority changed
                    if existing_task.priority != task_priority:
                        update_payload["priority"] = task_priority
                        needs_update = True
                    
                    # Check if description changed
                    if getattr(existing_task, 'description', '') != task_description:
                        update_payload["description"] = task_description
                        needs_update = True
                    
                    # Check if due date changed
                    existing_due = getattr(existing_task, 'due', None)
                    existing_due_date = existing_due.date if existing_due and hasattr(existing_due, 'date') else None
                    if existing_due_date != task_due_date:
                        if task_due_date:
                            update_payload["due_date"] = task_due_date
                        needs_update = True
                    
                    # Only update if changes detected
                    if needs_update:
                        if DEBUG_MODE:
                            logging.debug(f"Updating task {ticket['key']} with payload: {update_payload}")
                        tasks_to_update.append(update_payload)
                    else:
                        if DEBUG_MODE:
                            logging.debug(f"No changes detected for task {ticket['key']}, skipping update")
                    
                    # Sync comments with the existing task
                    await sync_todoist_comments(api, existing_task.id, comments)
                else:
                    # Add new task
                    new_task = {
                        "content": task_content,
                        "project_id": jira_project.id,
                        "priority": task_priority,
                        "description": task_description,
                    }
                    # Only add due_date if it's valid
                    if task_due_date:
                        new_task["due_date"] = task_due_date
                    if DEBUG_MODE:
                        logging.debug(f"Creating new task with payload: {new_task}")
                    try:
                        created_task = await api.add_task(**new_task)
                        logging.info(f"Added new task: {created_task.id}")
                        # Sync comments with the new task
                        await sync_todoist_comments(api, created_task.id, comments)
                    except Exception as e:
                        logging.error(f"Failed to add new task: {e}")

            # Perform batch updates asynchronously
            update_tasks = [api.update_task(**task) for task in tasks_to_update]
            delete_tasks = [api.delete_task(task_id=task_id) for task_id in tasks_to_delete]

            try:
                if update_tasks:
                    await asyncio.gather(*update_tasks)
                    logging.info(f"Updated {len(update_tasks)} tasks.")
                else:
                    logging.info("No tasks needed updating.")
            except Exception as e:
                logging.error(f"Failed to update some tasks: {e}")

            try:
                if delete_tasks:
                    await asyncio.gather(*delete_tasks)
                    logging.info(f"Deleted {len(delete_tasks)} tasks.")
                else:
                    logging.debug("No tasks needed deletion.")
            except Exception as e:
                logging.error(f"Failed to delete some tasks: {e}")
    finally:
        # Clean up the synchronous session
        todoist_session.close()


async def run_service(sync_interval_minutes=5):
    """Run the sync process as a service, checking at the specified interval."""
    # Create session within running loop to bind to correct event loop
    connector = TCPConnector(limit=20)
    async with aiohttp.ClientSession(connector=connector) as session:
        global shared_session
        shared_session = session
        
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
                jira_tickets = await get_open_jira_tickets()
                logging.debug(f"Jira Tickets: {jira_tickets}")
                await sync_to_todoist(jira_tickets)
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
            sleep_chunk_seconds = min(10, total_sleep_seconds)  # Sleep in 10-second chunks or less
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


async def main():
    """Main function to handle async config loading and run service"""
    global JIRA_SERVER_URL, JIRA_API_TOKEN, TODOIST_API_TOKEN, DEBUG_MODE, JIRA_USERNAME
    
    config = await load_config()
    
    JIRA_SERVER_URL = config["server_url"].rstrip('/')  # Remove trailing slash
    JIRA_API_TOKEN = config["api_token"]
    TODOIST_API_TOKEN = config["todoist_api_token"]

    # Configure logging
    DEBUG_MODE = config.get("debug", False)  # Enable debug mode based on config
    logging.basicConfig(
        level=logging.DEBUG if DEBUG_MODE else logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    
    # Reduce verbosity of third-party libraries in debug mode
    if DEBUG_MODE:
        logging.getLogger("aiohttp").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("requests").setLevel(logging.WARNING)

    # Update JIRA_USERNAME to fetch dynamically if not provided in config
    JIRA_USERNAME = config.get("jira_username") or get_current_jira_user()
    
    # Get sync interval from config
    sync_interval_minutes = config.get("sync_interval_minutes", 5)
    
    # Display startup banner
    print("\n" + "="*60)
    print("🚀 JIRA-TODOIST SYNC SERVICE STARTING")
    print("="*60)
    print(f"📍 Jira Server: {JIRA_SERVER_URL}")
    print(f"👤 Jira User: {JIRA_USERNAME}")
    print(f"🔧 Debug Mode: {'ON' if DEBUG_MODE else 'OFF'}")
    print(f"⏰ Sync Interval: {sync_interval_minutes} minute{'s' if sync_interval_minutes != 1 else ''}")
    print("💡 Press Ctrl+C to stop gracefully")
    print("="*60 + "\n")
    
    # Start the service with graceful shutdown handling
    try:
        await run_service(sync_interval_minutes)
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
