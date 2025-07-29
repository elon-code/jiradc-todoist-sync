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
import subprocess
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

async def get_api_credential(config, service_name, token_key):
    """Get API credential from config or environment variable"""
    api_creds = config.get("api_credentials", {}).get(service_name, {})
    
    if api_creds.get("use_env_var", False):
        env_var_name = api_creds.get("env_var_name")
        if env_var_name:
            token = os.getenv(env_var_name)
            if token:
                return token
            else:
                print(f"⚠️  Environment variable {env_var_name} not found, falling back to config file")
    
    return config.get(token_key, "")

async def prompt_for_config():
    """Prompt user for configuration values and save to config.json"""
    print("🔧 Setting up Jira-Todoist Sync Configuration")
    print("=" * 50)
    
    config = {
        "settings": {
            "default_priority": 4,
            "sleep_chunk_size": 10,
            "project_name": "Jira Tickets",
            "connection_pool_size": 20,
            "priority_mapping": {
                "Blocker": 1,
                "Critical": 1,
                "Major": 2,
                "Minor": 3,
                "Trivial": 4
            },
            "skip_statuses": ["Blocked"],
            "exclude_statuses": ["Blocked", "Canceled", "Cancelled", "Backlog", "Done"]
        },
        "api_credentials": {
            "jira": {
                "use_env_var": False,
                "env_var_name": "JIRA_API_TOKEN"
            },
            "todoist": {
                "use_env_var": False,
                "env_var_name": "TODOIST_API_TOKEN"
            }
        }
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
    CONFIG_FILE = "config.json"
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
    CONFIG_FILE = "config.json"
    
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

        # Ensure settings section exists with defaults
        if "settings" not in config:
            config["settings"] = {
                "default_priority": 4,
                "sleep_chunk_size": 10,
                "project_name": "Jira Tickets",
                "connection_pool_size": 20,
                "priority_mapping": {
                    "Blocker": 1,
                    "Critical": 1,
                    "Major": 2,
                    "Minor": 3,
                    "Trivial": 4
                },
                "skip_statuses": ["Blocked"],
                "exclude_statuses": ["Blocked", "Canceled", "Cancelled", "Backlog", "Done"]
            }

        # Ensure api_credentials section exists with defaults
        if "api_credentials" not in config:
            config["api_credentials"] = {
                "jira": {
                    "use_env_var": False,
                    "env_var_name": "JIRA_API_TOKEN"
                },
                "todoist": {
                    "use_env_var": False,
                    "env_var_name": "TODOIST_API_TOKEN"
                }
            }

        # Validate required configuration values
        required_fields = ["server_url"]
        missing_fields = []

        for field in required_fields:
            if not config.get(field) or config[field].strip() == "":
                missing_fields.append(field)

        # Check API tokens (from config or environment)
        jira_token = await get_api_credential(config, "jira", "api_token")
        todoist_token = await get_api_credential(config, "todoist", "todoist_api_token")
        
        # If API tokens are missing, automatically run setup
        if not jira_token or not todoist_token:
            print("❌ API tokens not found in environment variables or config file.")
            print("🚀 Running automatic setup...")
            
            # Check if setup.py exists
            if os.path.exists("setup.py"):
                try:
                    # Run setup.py
                    result = subprocess.run([sys.executable, "setup.py"], 
                                          capture_output=False, 
                                          text=True, 
                                          cwd=os.getcwd())
                    
                    if result.returncode == 0:
                        print("\n🔄 Setup completed. Please restart the application after setting environment variables.")
                        print("💡 Run 'python3 main.py' again once you've set the environment variables.")
                        sys.exit(0)
                    else:
                        print("⚠️  Setup script completed with issues. Falling back to manual configuration...")
                except Exception as e:
                    print(f"⚠️  Could not run setup script: {e}. Falling back to manual configuration...")
            else:
                print("⚠️  setup.py not found. Falling back to manual configuration...")
            
            # Fallback to manual configuration - add missing token fields
            if not jira_token:
                missing_fields.append("api_token (or JIRA_API_TOKEN environment variable)")
            if not todoist_token:
                missing_fields.append("todoist_api_token (or TODOIST_API_TOKEN environment variable)")

        if missing_fields:
            print(f"❌ Missing required configuration fields in {CONFIG_FILE}:")
            for field in missing_fields:
                print(f"   - {field}")
            print("\n🔧 Let's set up your configuration:")
            return await prompt_for_config()
        
        return config

def get_current_jira_user(config):
    """Fetch the current Jira user based on the API token."""
    url = f"{config['server_url']}/rest/api/2/myself"
    headers = {
        "Authorization": f"Bearer {config['_runtime_jira_token']}",
        "Content-Type": "application/json",
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    user = response.json()["name"]
    logging.info(f"Autofound Jira username: {user}")  # Log the autofound username
    logging.debug(f"Fetched current Jira user: {response.json()}")
    return user

async def get_green_resolution_statuses(config):
    """Fetch all Jira statuses and identify green resolution statuses asynchronously."""
    url = f"{config['server_url']}/rest/api/2/status"
    headers = {
        "Authorization": f"Bearer {config['_runtime_jira_token']}",
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

async def get_open_jira_tickets(config):
    """Fetch open Jira tickets assigned to the user, including Jira Service Management tasks."""
    url = f"{config['server_url']}/rest/api/2/search"
    headers = {
        "Authorization": f"Bearer {config['_runtime_jira_token']}",
        "Content-Type": "application/json",
    }
    
    exclude_statuses = config["settings"]["exclude_statuses"]
    exclude_list = '","'.join(exclude_statuses)
    
    # Use resolution filter to only fetch unresolved tickets and exclude blocked and cancelled
    jql_query = f'assignee = "{config["_runtime_jira_username"]}" AND resolution = Unresolved AND status NOT IN ("{exclude_list}")'
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
        debug_mode = config.get("debug", False)
        if debug_mode and len(response_json.get("issues", [])) <= 5:
            logging.debug(f"Jira API Response: {json.dumps(response_json, indent=2)}")
        elif debug_mode:
            logging.debug(f"Jira API Response: Found {len(response_json.get('issues', []))} tickets (response too large to log)")
        issues = response_json.get("issues", [])
    if not issues:
        logging.info("No tickets found.")
    else:
        logging.info(f"Found {len(issues)} tickets assigned to {config['_runtime_jira_username']}.")
    
    # Debug log just the ticket keys and summaries for overview
    if debug_mode and issues:
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


async def get_jira_comments(config, ticket_key):
    """Fetch comments for a Jira ticket."""
    url = f"{config['server_url']}/rest/api/2/issue/{ticket_key}/comment"
    headers = {
        "Authorization": f"Bearer {config['_runtime_jira_token']}",
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
    else:
        logging.debug(f"No comment changes needed for task {task_id}")


async def sync_to_todoist(config, jira_tickets):
    """Sync Jira tickets and comments to Todoist asynchronously."""
    # Use a dedicated synchronous requests.Session for Todoist calls
    todoist_session = requests.Session()
    # Increase connection pool size for Todoist API and block when full
    connection_pool_size = config["settings"]["connection_pool_size"]
    adapter = HTTPAdapter(pool_connections=connection_pool_size, pool_maxsize=connection_pool_size, pool_block=True)
    todoist_session.mount("https://api.todoist.com/", adapter)
    todoist_session.mount("http://api.todoist.com/", adapter)
    
    try:
        api = TodoistAPIAsync(config["_runtime_todoist_token"], session=todoist_session)
        project_name = config["settings"]["project_name"]
        
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

            skip_statuses = set(config["settings"]["skip_statuses"])
            priority_mapping = config["settings"]["priority_mapping"]
            default_priority = config["settings"]["default_priority"]
            debug_mode = config.get("debug", False)

            for ticket in jira_tickets:
                if ticket["status"] in skip_statuses:  # Skip blocked tickets
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
                if debug_mode:
                    logging.debug(f"Ticket {ticket['key']}: task_due_date = {task_due_date} (type: {type(task_due_date)})")
                
                task_priority = default_priority  # Default priority
                jira_link = f"{config['server_url']}/browse/{ticket['key']}"
                comments = await get_jira_comments(config, ticket["key"])  # Fetch comments
                task_description = f"{jira_link}\n\n{ticket.get('description', '') or ''}"  # Add link and description

                if ticket["priority"]:
                    jira_priority = priority_mapping.get(ticket["priority"], default_priority)
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
                        if debug_mode:
                            logging.debug(f"Updating task {ticket['key']} with payload: {update_payload}")
                        tasks_to_update.append(update_payload)
                    else:
                        if debug_mode:
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
                    if debug_mode:
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


async def run_service(config):
    """Run the sync process as a service, checking at the specified interval."""
    sync_interval_minutes = config.get("sync_interval_minutes", 5)
    sleep_chunk_size = config["settings"]["sleep_chunk_size"]
    connection_pool_size = config["settings"]["connection_pool_size"]
    
    # Create session within running loop to bind to correct event loop
    connector = TCPConnector(limit=connection_pool_size)
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
                jira_tickets = await get_open_jira_tickets(config)
                logging.debug(f"Jira Tickets: {jira_tickets}")
                await sync_to_todoist(config, jira_tickets)
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
