"""
Main synchronization engine.

This module contains the core logic for synchronizing Jira tickets with Todoist tasks.
"""

import asyncio
import logging
from datetime import datetime, date
from typing import Dict, Any, List

from ..api.jira import get_jira_comments
from ..api.todoist import sync_todoist_comments, create_todoist_session
from todoist_api_python.api_async import TodoistAPIAsync


async def sync_to_todoist(config: Dict[str, Any], jira_tickets: List[Dict[str, Any]], session) -> None:
    """Sync Jira tickets and comments to Todoist asynchronously."""
    # Use a dedicated synchronous requests.Session for Todoist calls
    todoist_session = create_todoist_session(config)
    
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
                comments = await get_jira_comments(config, ticket["key"], session)  # Fetch comments
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
