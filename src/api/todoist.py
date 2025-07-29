"""
Todoist API integration module.

This module handles all interactions with the Todoist API.
"""

import logging
import requests
from typing import Dict, Any, List
from requests.adapters import HTTPAdapter
from todoist_api_python.api_async import TodoistAPIAsync


async def get_todoist_comments(api: TodoistAPIAsync, task_id: str) -> Dict[str, str]:
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


async def sync_todoist_comments(api: TodoistAPIAsync, task_id: str, jira_comments: List[str]) -> None:
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


def create_todoist_session(config: Dict[str, Any]) -> requests.Session:
    """Create a configured requests session for Todoist API calls."""
    todoist_session = requests.Session()
    # Increase connection pool size for Todoist API and block when full
    connection_pool_size = config["settings"]["connection_pool_size"]
    adapter = HTTPAdapter(pool_connections=connection_pool_size, pool_maxsize=connection_pool_size, pool_block=True)
    todoist_session.mount("https://api.todoist.com/", adapter)
    todoist_session.mount("http://api.todoist.com/", adapter)
    return todoist_session
