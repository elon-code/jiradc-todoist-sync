"""
Jira API integration module.

This module handles all interactions with the Jira REST API.
"""

import logging
import requests
import aiohttp
from typing import Dict, Any, List
from datetime import datetime


def get_current_jira_user(config: Dict[str, Any]) -> str:
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


async def get_green_resolution_statuses(config: Dict[str, Any], session: aiohttp.ClientSession) -> List[str]:
    """Fetch all Jira statuses and identify green resolution statuses asynchronously."""
    url = f"{config['server_url']}/rest/api/2/status"
    headers = {
        "Authorization": f"Bearer {config['_runtime_jira_token']}",
        "Content-Type": "application/json"
    }
    async with session.get(url, headers=headers) as response:
        if response.status != 200:
            logging.error(f"Error fetching Jira statuses: {response.status} - {await response.text()}")
            response.raise_for_status()
        statuses = await response.json()
        green_statuses = [status["name"] for status in statuses if status.get("statusCategory", {}).get("key") == "done"]
        logging.debug(f"Green resolution statuses: {green_statuses}")
        return green_statuses


async def get_open_jira_tickets(config: Dict[str, Any], session: aiohttp.ClientSession) -> List[Dict[str, Any]]:
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
    async with session.get(url, headers=headers, params=query) as response:
        if response.status != 200:
            logging.error(
                f"Error fetching Jira tickets: {response.status} - {await response.text()}"
            )
            response.raise_for_status()
        response_json = await response.json()
        # Only log the response in debug mode if it's a small number of tickets
        debug_mode = config.get("debug", False)
        if debug_mode and len(response_json.get("issues", [])) <= 5:
            logging.debug(f"Jira API Response: {response_json}")
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


async def get_jira_comments(config: Dict[str, Any], ticket_key: str, session: aiohttp.ClientSession) -> List[str]:
    """Fetch comments for a Jira ticket."""
    url = f"{config['server_url']}/rest/api/2/issue/{ticket_key}/comment"
    headers = {
        "Authorization": f"Bearer {config['_runtime_jira_token']}",
        "Content-Type": "application/json",
    }
    # Use shared aiohttp session
    async with session.get(url, headers=headers) as response:
        if response.status != 200:
            logging.error(
                f"Error fetching comments for {ticket_key}: {response.status} - {await response.text()}"
            )
            return []
        response_json = await response.json()
        comments = response_json.get("comments", [])
        return [comment["body"] for comment in comments]
