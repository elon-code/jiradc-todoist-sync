import requests
import json
import urllib.parse
import asyncio
import time
from todoist_api_python.api_async import TodoistAPIAsync  # Use the async version of the API

# Load configuration from config.json
with open("config.json", "r") as config_file:
    config = json.load(config_file)

JIRA_SERVER_URL = config["server_url"]
JIRA_API_TOKEN = config["api_token"]
TODOIST_API_TOKEN = config["todoist_api_token"]

def get_current_jira_user():
    """Fetch the current Jira user based on the API token."""
    url = f"{JIRA_SERVER_URL}/rest/api/2/myself"
    headers = {
        "Authorization": f"Bearer {JIRA_API_TOKEN}",
        "Content-Type": "application/json"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()["name"]

# Update JIRA_USERNAME to fetch dynamically if not provided in config
JIRA_USERNAME = config.get("jira_username") or get_current_jira_user()

def get_green_resolution_statuses():
    """Fetch all Jira statuses and identify green resolution statuses."""
    url = f"{JIRA_SERVER_URL}/rest/api/2/status"
    headers = {
        "Authorization": f"Bearer {JIRA_API_TOKEN}",
        "Content-Type": "application/json"
    }
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Error fetching Jira statuses: {response.status_code} - {response.text}")
        response.raise_for_status()
    statuses = response.json()
    # Identify green resolution statuses (e.g., "Done", "Resolved")
    green_statuses = [status["name"] for status in statuses if status.get("statusCategory", {}).get("key") == "done"]
    print(f"Green resolution statuses: {green_statuses}")
    return green_statuses

def get_open_jira_tickets():
    """Fetch open Jira tickets assigned to the user, including Jira Service Management tasks."""
    green_statuses = get_green_resolution_statuses()
    excluded_statuses = ["Blocked", "Cancelled"] + green_statuses
    excluded_statuses_jql = ", ".join(f'"{status}"' for status in excluded_statuses)
    url = f"{JIRA_SERVER_URL}/rest/api/2/search"
    headers = {
        "Authorization": f"Bearer {JIRA_API_TOKEN}",
        "Content-Type": "application/json"
    }
    # Exclude blocked, cancelled, and green resolution tickets in the JQL query
    jql_query = f'assignee = "{JIRA_USERNAME}" AND status NOT IN ({excluded_statuses_jql})'
    print(f"Using JQL Query: {jql_query}")  # Debugging: Print the JQL query
    query = {
        "jql": jql_query,
        "fields": "summary,duedate,priority,status,issuetype"  # Include issuetype field for Jira Service Management
    }
    response = requests.get(url, headers=headers, params=query)
    if response.status_code != 200:
        print(f"Error fetching Jira tickets: {response.status_code} - {response.text}")
    response.raise_for_status()
    issues = response.json().get("issues", [])
    if not issues:
        print("No tickets found. Full response:", response.json())  # Debugging: Print full response
    return [
        {
            "key": issue["key"],
            "summary": issue["fields"]["summary"],
            "due_date": issue["fields"].get("duedate"),  # Fetch due date
            "priority": issue["fields"].get("priority", {}).get("name"),  # Fetch priority name
            "status": issue["fields"].get("status", {}).get("name"),  # Fetch status name
            "issuetype": issue["fields"].get("issuetype", {}).get("name")  # Fetch issue type
        }
        for issue in issues
    ]

async def sync_to_todoist(jira_tickets):
    """Sync Jira tickets to Todoist asynchronously."""
    api = TodoistAPIAsync(TODOIST_API_TOKEN)
    
    # Create or get the Jira project in Todoist
    project_name = "Jira Tickets"
    try:
        projects = await api.get_projects()
        jira_project = next((p for p in projects if p.name == project_name), None)
        if not jira_project:
            jira_project = await api.add_project(name=project_name)
            print(f"Created project: {project_name}")
        else:
            print(f"Using existing project: {project_name}")
    except Exception as e:
        print(f"Failed to create or retrieve project '{project_name}': {e}")
        return

    # Get existing tasks in the Jira project
    try:
        existing_tasks = await api.get_tasks(project_id=jira_project.id)
        existing_task_map = {task.content.split(":")[0]: task for task in existing_tasks}  # Map by Jira key
    except Exception as e:
        print(f"Failed to retrieve existing tasks: {e}")
        return

    # Prepare batch updates, additions, completions, and deletions
    tasks_to_update = []
    tasks_to_add = []
    tasks_to_complete = []
    tasks_to_delete = []

    jira_ticket_keys = {ticket["key"] for ticket in jira_tickets}
    green_resolution_statuses = get_green_resolution_statuses()
    blocked_or_cancelled_ticket_keys = {
        ticket["key"] for ticket in jira_tickets if ticket["status"] in {"Blocked", "Cancelled"}
    }

    for ticket in jira_tickets:
        if ticket["status"] in {"Blocked", "Cancelled"}:
            continue  # Skip blocked or cancelled tickets

        # Handle Jira Service Management tasks differently if needed
        if ticket["issuetype"] == "Service Request":
            print(f"Handling Jira Service Management task: {ticket['key']}")

        task_content = f"{ticket['key']}: {ticket['summary']}"
        task_due_date = ticket["due_date"]  # Use the due date from Jira
        task_priority = 4  # Default priority (Todoist uses 1-4, with 4 being the lowest)
        task_description = f"{JIRA_SERVER_URL}/browse/{ticket['key']}"  # Add Jira ticket link

        # Map Jira priority to Todoist priority
        if ticket["priority"]:
            priority_mapping = {
                "Blocker": 1,  # Highest priority in Todoist
                "Critical": 1,
                "Major": 2,    # P2
                "Minor": 3,    # P3
                "Trivial": 4   # P4
            }
            task_priority = priority_mapping.get(ticket["priority"], 4)

        if ticket["key"] in existing_task_map:
            # Prepare task for update
            existing_task = existing_task_map[ticket["key"]]
            tasks_to_update.append({
                "task_id": existing_task.id,
                "content": task_content,
                "due_date": task_due_date,
                "priority": task_priority,
                "description": task_description
            })
        else:
            # Prepare task for addition
            tasks_to_add.append({
                "content": task_content,
                "project_id": jira_project.id,
                "due_date": task_due_date,
                "priority": task_priority,
                "description": task_description
            })

    # Identify tasks to mark as done or delete
    for task_key, task in existing_task_map.items():
        if task_key not in jira_ticket_keys:
            tasks_to_complete.append(task.id)  # Mark tasks as done for green resolution statuses
        elif task_key in blocked_or_cancelled_ticket_keys:
            tasks_to_delete.append(task.id)

    # Perform batch updates asynchronously
    update_tasks = [
        api.update_task(**task) for task in tasks_to_update
    ]
    add_tasks = [
        api.add_task(**task) for task in tasks_to_add
    ]
    complete_tasks = [
        api.close_task(task_id=task_id) for task_id in tasks_to_complete
    ]
    delete_tasks = [
        api.delete_task(task_id=task_id) for task_id in tasks_to_delete
    ]

    try:
        await asyncio.gather(*update_tasks)
        print(f"Updated {len(update_tasks)} tasks.")
    except Exception as e:
        print(f"Failed to update some tasks: {e}")

    try:
        await asyncio.gather(*add_tasks)
        print(f"Added {len(add_tasks)} tasks.")
    except Exception as e:
        print(f"Failed to add some tasks: {e}")

    try:
        await asyncio.gather(*complete_tasks)
        print(f"Marked {len(complete_tasks)} tasks as done.")
    except Exception as e:
        print(f"Failed to mark some tasks as done: {e}")

    try:
        await asyncio.gather(*delete_tasks)
        print(f"Deleted {len(delete_tasks)} blocked tasks.")
    except Exception as e:
        print(f"Failed to delete some blocked tasks: {e}")

async def run_service():
    """Run the sync process as a service, checking every 5 minutes."""
    while True:
        print("Starting Jira to Todoist sync...")
        try:
            jira_tickets = get_open_jira_tickets()
            print("Jira Tickets:")
            for ticket in jira_tickets:
                print(f"- {ticket['key']}: {ticket['summary']} (Due: {ticket['due_date']}, Priority: {ticket['priority']})")
            await sync_to_todoist(jira_tickets)
        except Exception as e:
            print(f"Error during sync: {e}")
        print("Sync complete. Waiting for 5 minutes...")
        await asyncio.sleep(300)  # Non-blocking wait for 5 minutes

if __name__ == "__main__":
    asyncio.run(run_service())
