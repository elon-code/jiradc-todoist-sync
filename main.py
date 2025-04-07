import requests
import aiohttp
import json
import urllib.parse
import asyncio
import logging
from todoist_api_python.api_async import TodoistAPIAsync  # Use the async version of the API

# Load configuration from config.json
with open("config.json", "r") as config_file:
    config = json.load(config_file)

JIRA_SERVER_URL = config["server_url"]
JIRA_API_TOKEN = config["api_token"]
TODOIST_API_TOKEN = config["todoist_api_token"]

# Configure logging
DEBUG_MODE = config.get("debug", False)  # Enable debug mode based on config
logging.basicConfig(
    level=logging.DEBUG if DEBUG_MODE else logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def get_current_jira_user():
    """Fetch the current Jira user based on the API token."""
    url = f"{JIRA_SERVER_URL}/rest/api/2/myself"
    headers = {
        "Authorization": f"Bearer {JIRA_API_TOKEN}",
        "Content-Type": "application/json"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    user = response.json()["name"]
    logging.info(f"Autofound Jira username: {user}")  # Log the autofound username
    logging.debug(f"Fetched current Jira user: {response.json()}")
    return user

# Update JIRA_USERNAME to fetch dynamically if not provided in config
JIRA_USERNAME = config.get("jira_username") or get_current_jira_user()

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
    green_statuses = await get_green_resolution_statuses()
    excluded_statuses = ["Blocked"] + green_statuses  # Removed explicit "Canceled"
    excluded_statuses_jql = ", ".join(f'"{status}"' for status in excluded_statuses)
    url = f"{JIRA_SERVER_URL}/rest/api/2/search"
    headers = {
        "Authorization": f"Bearer {JIRA_API_TOKEN}",
        "Content-Type": "application/json"
    }
    jql_query = f'assignee = "{JIRA_USERNAME}" AND status NOT IN ({excluded_statuses_jql})'
    logging.debug(f"Using JQL Query: {jql_query}")
    query = {
        "jql": jql_query,
        "fields": "summary,duedate,priority,status,issuetype,description"  # Include description field
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=query) as response:
            if response.status != 200:
                logging.error(f"Error fetching Jira tickets: {response.status} - {await response.text()}")
                response.raise_for_status()
            response_json = await response.json()
            logging.debug(f"Jira API Response: {json.dumps(response_json, indent=2)}")  # Log the full response
            issues = response_json.get("issues", [])
    if not issues:
        logging.info("No tickets found.")
    else:
        logging.info(f"Found {len(issues)} tickets assigned to {JIRA_USERNAME}.")
    return [
        {
            "key": issue["key"],
            "summary": issue["fields"]["summary"],
            "due_date": issue["fields"].get("duedate"),
            "priority": issue["fields"].get("priority", {}).get("name"),
            "status": issue["fields"].get("status", {}).get("name"),
            "issuetype": issue["fields"].get("issuetype", {}).get("name"),
            "description": issue["fields"].get("description")  # Fetch description
        }
        for issue in issues
    ]

async def get_jira_comments(ticket_key):
    """Fetch comments for a Jira ticket."""
    url = f"{JIRA_SERVER_URL}/rest/api/2/issue/{ticket_key}/comment"
    headers = {
        "Authorization": f"Bearer {JIRA_API_TOKEN}",
        "Content-Type": "application/json"
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status != 200:
                logging.error(f"Error fetching comments for {ticket_key}: {response.status} - {await response.text()}")
                return []
            response_json = await response.json()
            comments = response_json.get("comments", [])
            return [comment["body"] for comment in comments]

async def get_todoist_comments(api, task_id):
    """Fetch comments for a Todoist task."""
    try:
        comments = await api.get_comments(task_id=task_id)
        return {comment.content: comment.id for comment in comments}  # Map content to comment ID
    except Exception as error:
        logging.error(f"Failed to fetch comments for task {task_id}: {error}")
        return {}

async def sync_todoist_comments(api, task_id, jira_comments):
    """Sync Jira comments with Todoist comments."""
    todoist_comments = await get_todoist_comments(api, task_id)

    # Add or update comments from Jira
    for jira_comment in jira_comments:
        if jira_comment not in todoist_comments:
            try:
                await api.add_comment(content=jira_comment, task_id=task_id)
                logging.info(f"Added new comment to task {task_id}: {jira_comment}")
            except Exception as error:
                logging.error(f"Failed to add comment to task {task_id}: {jira_comment}. Error: {error}")
        else:
            # Update existing comment if needed (Todoist doesn't allow direct content comparison)
            todoist_comment_id = todoist_comments[jira_comment]
            try:
                await api.update_comment(comment_id=todoist_comment_id, content=jira_comment)
                logging.info(f"Updated comment in task {task_id}: {jira_comment}")
            except Exception as error:
                logging.error(f"Failed to update comment in task {task_id}: {jira_comment}. Error: {error}")
                # Skip problematic comment and continue with others
                continue

    # Delete comments in Todoist that are no longer in Jira
    for todoist_comment, comment_id in todoist_comments.items():
        if todoist_comment not in jira_comments:
            try:
                await api.delete_comment(comment_id=comment_id)
                logging.info(f"Deleted comment from task {task_id}: {todoist_comment}")
            except Exception as error:
                logging.error(f"Failed to delete comment from task {task_id}: {todoist_comment}. Error: {error}")

async def sync_to_todoist(jira_tickets):
    """Sync Jira tickets and comments to Todoist asynchronously."""
    api = TodoistAPIAsync(TODOIST_API_TOKEN)
    project_name = "Jira Tickets"
    try:
        projects = await api.get_projects()
        jira_project = next((p for p in projects if p.name == project_name), None)
        if not jira_project:
            jira_project = await api.add_project(name=project_name)
            logging.info(f"Created project: {project_name}")
        else:
            logging.info(f"Using existing project: {project_name}")
    except Exception as e:
        logging.error(f"Failed to create or retrieve project '{project_name}': {e}")
        return

    try:
        existing_tasks = await api.get_tasks(project_id=jira_project.id)
        # Normalize task keys by stripping whitespace and ensuring consistent formatting
        existing_task_map = {}
        for task in existing_tasks:
            if ":" in task.content:
                jira_key = task.content.split(":")[0].strip()
                existing_task_map[jira_key] = task
    except Exception as e:
        logging.error(f"Failed to retrieve existing tasks: {e}")
        return

    # Prepare batch updates, additions, and deletions
    tasks_to_update = []
    tasks_to_add = []
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
                "Trivial": 4
            }
            jira_priority = priority_mapping.get(ticket["priority"], 4)
            # Invert the priority for Todoist
            task_priority = 5 - jira_priority
            logging.debug(f"Ticket {ticket['key']} has Jira priority '{ticket['priority']}' mapped to Todoist priority {task_priority}")

        if ticket["key"] in existing_task_map:
            # Update existing task
            existing_task = existing_task_map[ticket["key"]]
            update_payload = {
                "task_id": existing_task.id,
                "content": task_content,
                "due_date": task_due_date,
                "priority": task_priority,
                "description": task_description
            }
            logging.debug(f"Updating task with payload: {update_payload}")
            tasks_to_update.append(update_payload)
            # Sync comments with the existing task
            await sync_todoist_comments(api, existing_task.id, comments)
        else:
            # Add new task
            new_task = {
                "content": task_content,
                "project_id": jira_project.id,
                "due_date": task_due_date,
                "priority": task_priority,
                "description": task_description
            }
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
        await asyncio.gather(*update_tasks)
        logging.info(f"Updated {len(update_tasks)} tasks.")
    except Exception as e:
        logging.error(f"Failed to update some tasks: {e}")

    try:
        await asyncio.gather(*delete_tasks)
        logging.info(f"Deleted {len(delete_tasks)} tasks.")
    except Exception as e:
        logging.error(f"Failed to delete some tasks: {e}")

async def run_service():
    """Run the sync process as a service, checking every 5 minutes."""
    while True:
        logging.info("Starting Jira to Todoist sync...")
        try:
            jira_tickets = await get_open_jira_tickets()
            logging.debug(f"Jira Tickets: {jira_tickets}")
            await sync_to_todoist(jira_tickets)
        except Exception as e:
            logging.error(f"Error during sync: {e}")
        logging.info("Sync complete. Waiting for 5 minutes...")
        await asyncio.sleep(300)

if __name__ == "__main__":
    asyncio.run(run_service())
