"""
Authentication and credential testing module.

This module provides functions to test API credentials for both Jira and Todoist.
"""

import aiohttp
from typing import Tuple
from todoist_api_python.api_async import TodoistAPIAsync


async def test_jira_credentials(server_url: str, api_token: str) -> Tuple[bool, str]:
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


async def test_todoist_credentials(api_token: str) -> Tuple[bool, str]:
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
