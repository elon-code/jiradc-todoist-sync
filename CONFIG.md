# Jira-Todoist Sync Configuration

This document explains the configuration options for the Jira-Todoist sync tool.

## Quick Start

1. **Set environment variables** (optional but recommended):
   ```bash
   # Windows PowerShell
   $env:JIRA_API_TOKEN="your_jira_token_here"
   $env:TODOIST_API_TOKEN="your_todoist_token_here"
   $env:JIRA_SERVER_URL="https://your-jira-instance.atlassian.net"
   
   # Linux/Mac
   export JIRA_API_TOKEN="your_jira_token_here"
   export TODOIST_API_TOKEN="your_todoist_token_here"
   export JIRA_SERVER_URL="https://your-jira-instance.atlassian.net"
   ```

2. **Run the application**:
   ```bash
   python main.py
   ```
   
   💡 If environment variables aren't set, you'll be prompted to enter:
   1. Your Jira server URL first (e.g., `jira.company.com`)
   2. Your API tokens (which are immediately validated)

## Security-First Design

🔐 **Smart credential handling with validation**

- **Environment variables**: Check first (secure, convenient)
- **Interactive prompts**: Fallback if environment variables not found
- **Real-time validation**: API credentials are tested immediately when entered
- **Proper URL handling**: Uses Python's urllib.parse for robust URL formatting
- **Smart flow**: Server URL is requested first, then credentials are tested against it
- **No credential storage**: API tokens and server URL are saved to .env for convenience only

## Configuration Structure

The `config.json` file contains application settings:

```json
{
  "debug": false,
  "sync_interval_minutes": 5,
  "jira_username": "",
  "settings": {
    "default_priority": 4,
    "sleep_chunk_size": 10,
    "project_name": "Jira Tickets",
    "connection_pool_size": 20,
    "priority_mapping": { ... },
    "skip_statuses": [...],
    "exclude_statuses": [...]
  },
  "api_credentials": {
    "jira": {
      "use_env_var": true,
      "env_var_name": "JIRA_API_TOKEN",
      "server_url_env_var": "JIRA_SERVER_URL"
    },
    "todoist": {
      "use_env_var": true,
      "env_var_name": "TODOIST_API_TOKEN"
    }
  }
}
```

## Git Safety

✅ **`config.json` is now safe to commit** because it contains no secrets

- Contains only non-sensitive application settings
- API tokens and server URL are handled via environment variables
- Users can clone and run immediately after setting env vars

## Troubleshooting

### "API tokens not found"
- Set environment variables: `$env:JIRA_API_TOKEN="token"`, `$env:TODOIST_API_TOKEN="token"`, and `$env:JIRA_SERVER_URL="https://jira.company.com"`
- Or simply run `python main.py` and enter tokens and server URL when prompted
- Use `echo $env:JIRA_API_TOKEN` (Windows) to verify environment variables

### "Permission denied" errors
- Verify your API tokens have the correct permissions
- Check that your Jira server URL is correct (can be set via environment variable or prompted on first run)

### URL Formatting & Validation
- The application uses Python's `urllib.parse` for robust URL handling:
  - Adds `https://` if no protocol is specified
  - Removes trailing slashes while preserving paths and query parameters
  - Handles complex URLs correctly (e.g., `jira.company.com/secure` → `https://jira.company.com/secure`)
- **Credential Testing**: When you enter a Jira API token, it's immediately tested against your server
- **Smart Flow**: Server URL is requested first, then credentials are validated in real-time
