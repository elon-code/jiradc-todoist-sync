import requests
import json
import urllib.parse
from todoist_api_python.api import TodoistAPI

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

def get_open_jira_tickets():
    """Fetch open Jira tickets assigned to the user."""
    url = f"{JIRA_SERVER_URL}/rest/api/2/search"
    headers = {
        "Authorization": f"Bearer {JIRA_API_TOKEN}",
        "Content-Type": "application/json"
    }
    # Use JIRA_USERNAME directly without URL-encoding
    jql_query = f'assignee = "{JIRA_USERNAME}" AND status != Done'  # Enclose in double quotes
    print(f"Using JQL Query: {jql_query}")  # Debugging: Print the JQL query
    query = {
        "jql": jql_query,
        "fields": "summary,duedate,priority"  # Include due date and priority fields
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
            "priority": issue["fields"].get("priority", {}).get("name")  # Fetch priority name
        }
        for issue in issues
    ]

def sync_to_todoist(jira_tickets):
    """Sync Jira tickets to Todoist."""
    api = TodoistAPI(TODOIST_API_TOKEN)
    
    # Create or get the Jira project in Todoist
    project_name = "Jira Tickets"
    try:
        projects = api.get_projects()
        jira_project = next((p for p in projects if p.name == project_name), None)
        if not jira_project:
            jira_project = api.add_project(name=project_name)
            print(f"Created project: {project_name}")
        else:
            print(f"Using existing project: {project_name}")
    except Exception as e:
        print(f"Failed to create or retrieve project '{project_name}': {e}")
        return

    # Get existing tasks in the Jira project
    try:
        existing_tasks = api.get_tasks(project_id=jira_project.id)
        existing_task_map = {task.content.split(":")[0]: task for task in existing_tasks}  # Map by Jira key
    except Exception as e:
        print(f"Failed to retrieve existing tasks: {e}")
        return

    # Add or update tasks in the Jira project
    for ticket in jira_tickets:
        task_content = f"{ticket['key']}: {ticket['summary']}"
        task_due_date = ticket["due_date"]  # Use the due date from Jira
        task_priority = 4  # Default priority (Todoist uses 1-4, with 4 being the lowest)
        
        # Map Jira priority to Todoist priority
        if ticket["priority"]:
            print(f"Jira Priority for {ticket['key']}: {ticket['priority']}")  # Debugging: Print Jira priority
            priority_mapping = {
                "Blocker": 1,  # Highest priority in Todoist
                "Critical": 1,
                "Major": 2,    # P2
                "Minor": 3,    # P3
                "Trivial": 4   # P4
            }
            task_priority = priority_mapping.get(ticket["priority"], 4)

        if ticket["key"] in existing_task_map:
            # Update existing task
            existing_task = existing_task_map[ticket["key"]]
            try:
                api.update_task(
                    task_id=existing_task.id,
                    content=task_content,
                    due_date=task_due_date,  # Update due date
                    priority=task_priority  # Update priority
                )
                print(f"Updated task: {task_content} (Due: {task_due_date}, Priority: {task_priority})")
            except Exception as e:
                print(f"Failed to update task for {ticket['key']}: {e}")
        else:
            # Add new task
            try:
                api.add_task(
                    content=task_content,
                    project_id=jira_project.id,
                    due_date=task_due_date,  # Add due date
                    priority=task_priority  # Add priority
                )
                print(f"Added task: {task_content} (Due: {task_due_date}, Priority: {task_priority})")
            except Exception as e:
                print(f"Failed to add task for {ticket['key']}: {e}")

if __name__ == "__main__":
    print(f"JIRA_USERNAME: {JIRA_USERNAME}")  # Debugging: Print the username being used
    jira_tickets = get_open_jira_tickets()
    
    # Print tickets to confirm they are being read correctly
    print("Jira Tickets:")
    for ticket in jira_tickets:
        print(f"- {ticket['key']}: {ticket['summary']} (Due: {ticket['due_date']}, Priority: {ticket['priority']})")
    
    sync_to_todoist(jira_tickets)
