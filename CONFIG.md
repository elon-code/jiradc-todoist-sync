# Jira-Todoist Sync Configuration

This document explains the configuration options for the Jira-Todoist sync tool.

## Quick Start

1. **Set environment variables** (optional but recommended):
   ```bash
   # Windows PowerShell
   $env:JIRA_API_TOKEN="your_jira_token_here"
   $env:TODOIST_API_TOKEN="your_todoist_token_here"
   
   # Linux/Mac
   export JIRA_API_TOKEN="your_jira_token_here"
   export TODOIST_API_TOKEN="your_todoist_token_here"
   ```

2. **Update server URL** in `config.json`:
   ```json
   {
     "server_url": "https://your-jira-instance.atlassian.net"
   }
   ```

3. **Run the application**:
   ```bash
   python main.py
   ```
   
   💡 If environment variables aren't set, you'll be prompted to enter your API tokens.

## Security-First Design

🔐 **Simple and secure credential handling**

- **Environment variables**: Check first (secure, convenient)
- **Interactive prompts**: Fallback if environment variables not found
- **No credential storage**: API tokens are never saved to files

## Configuration Structure

The `config.json` file contains application settings:

```json
{
  "server_url": "https://your-jira-instance.com",
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
  }
}
```

## Git Safety

✅ **`config.json` is now safe to commit** because it contains no secrets

- Contains only non-sensitive application settings
- API tokens are handled via environment variables
- Users can clone and run immediately after setting env vars

## Troubleshooting

### "API tokens not found"
- Set environment variables: `$env:JIRA_API_TOKEN="token"` and `$env:TODOIST_API_TOKEN="token"`
- Or simply run `python main.py` and enter tokens when prompted
- Use `echo $env:JIRA_API_TOKEN` (Windows) to verify environment variables

### "Permission denied" errors
- Verify your API tokens have the correct permissions
- Check that your Jira server URL is correct in config.json
