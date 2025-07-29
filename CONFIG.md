# Jira-Todoist Sync Configuration

This document explains the configuration options for the Jira-Todoist sync tool.

## Quick Start

1. **Set up API tokens** (required first step):
   ```bash
   python3 setup.py
   ```
   Or manually set environment variables:
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
   python3 main.py
   ```

## Security-First Design

🔐 **API tokens are NEVER stored in configuration files by default**

- **Environment variables**: Primary method (secure, flexible)
- **Runtime prompting**: Fallback if environment variables not found
- **Config file storage**: Available but discouraged (must be explicitly enabled)

## Configuration Structure

The `config.json` file contains application settings but **no API tokens**:

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
  },
  "api_credentials": {
    "jira": {
      "use_env_var": true,
      "env_var_name": "JIRA_API_TOKEN"
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
- API tokens are handled via environment variables
- Users can clone and run immediately after setting env vars

## Advanced Options

### Custom Environment Variable Names
```json
{
  "api_credentials": {
    "jira": {
      "use_env_var": true,
      "env_var_name": "MY_CUSTOM_JIRA_TOKEN"
    }
  }
}
```

### Local Override (Not Recommended)
If you prefer to store tokens in a config file:

1. Create `config.local.json` (gitignored):
   ```json
   {
     "api_token": "your_jira_token",
     "todoist_api_token": "your_todoist_token",
     "api_credentials": {
       "jira": { "use_env_var": false },
       "todoist": { "use_env_var": false }
     }
   }
   ```

2. The app will load this automatically

### Configuration Hierarchy
1. `config.local.json` (if exists, highest priority)
2. `config.json` (main configuration)
3. Environment variables (if `use_env_var: true`)
4. Runtime prompting (fallback)

## Migration from Previous Versions

If you have an old `config.json` with API tokens:

1. **Run setup**: `python3 setup.py`
2. **Remove tokens** from `config.json`
3. **Set `use_env_var: true`** in the api_credentials section

## Security Best Practices

1. ✅ **Use environment variables** (default)
2. ✅ **Never commit API tokens** to git
3. ✅ **Regularly rotate** your API tokens
4. ✅ **Use the setup script** for easy configuration
5. ❌ **Avoid storing tokens** in configuration files

## Troubleshooting

### "API tokens not found"
- Ensure environment variables are set in the same shell session
- Use `echo $JIRA_API_TOKEN` (Linux/Mac) or `echo $env:JIRA_API_TOKEN` (Windows) to verify
- Run `python3 setup.py` for guided setup

### "Permission denied" errors
- Verify your API tokens have the correct permissions
- Check that your Jira server URL is correct
