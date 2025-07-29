# Improved File Structure

The codebase has been restructured for better maintainability and separation of concerns.

## New Structure

```
├── src/                          # Main source code directory
│   ├── __init__.py
│   ├── auth/                     # Authentication and credential management
│   │   ├── __init__.py
│   │   └── credentials.py        # API credential testing
│   ├── api/                      # API integration modules
│   │   ├── __init__.py
│   │   ├── jira.py              # Jira API interactions
│   │   └── todoist.py           # Todoist API interactions
│   ├── sync/                     # Synchronization logic
│   │   ├── __init__.py
│   │   ├── engine.py            # Core sync logic
│   │   └── service.py           # Service runner and scheduling
│   └── utils/                    # Utility modules
│       ├── __init__.py
│       ├── config.py            # Configuration management
│       └── setup.py             # Interactive setup
├── main_new.py                   # New main entry point
├── setup_new.py                  # New setup script
├── main.py                       # Legacy main file (kept for reference)
└── setup.py                      # Legacy setup file (kept for reference)
```

## Benefits of New Structure

### 1. **Separation of Concerns**
- **Authentication**: Isolated in `src/auth/`
- **API Integration**: Separate modules for Jira and Todoist
- **Sync Logic**: Core business logic in dedicated modules
- **Configuration**: Centralized config management
- **Service Management**: Service runner with scheduling logic

### 2. **Improved Maintainability**
- Smaller, focused files (vs. 878-line monolith)
- Clear module boundaries
- Easy to locate and modify specific functionality
- Better code organization

### 3. **Enhanced Testability**
- Individual modules can be unit tested
- Clear interfaces between components
- Easier to mock dependencies
- Better isolation of concerns

### 4. **Code Reusability**
- Credential testing functions can be reused
- API modules can be extended independently
- Configuration utilities are modular

### 5. **Developer Experience**
- Easier navigation and code understanding
- Clear import structure
- Better IDE support and code completion
- Reduced cognitive load

## Migration Guide

### For Users
1. Use `python3 setup_new.py` instead of `python3 setup.py`
2. Use `python3 main_new.py` instead of `python3 main.py`
3. All existing configuration files remain compatible

### For Developers
1. Import from specific modules instead of one large file
2. Follow the new module structure for extensions
3. Use the established patterns for new functionality

## Module Descriptions

### `src/auth/credentials.py`
- `test_jira_credentials()`: Validates Jira API tokens
- `test_todoist_credentials()`: Validates Todoist API tokens

### `src/api/jira.py`
- `get_current_jira_user()`: Fetches current user info
- `get_open_jira_tickets()`: Retrieves assigned tickets
- `get_jira_comments()`: Fetches ticket comments

### `src/api/todoist.py`
- `get_todoist_comments()`: Fetches task comments
- `sync_todoist_comments()`: Syncs comments between platforms
- `create_todoist_session()`: Creates configured HTTP session

### `src/sync/engine.py`
- `sync_to_todoist()`: Main synchronization logic
- Handles task creation, updates, and deletions

### `src/sync/service.py`
- `run_service()`: Service loop with scheduling
- Graceful shutdown handling
- Signal management

### `src/utils/config.py`
- `load_config()`: Configuration loading and validation
- `get_api_credential()`: Credential resolution
- Configuration defaults and validation

### `src/utils/setup.py`
- `prompt_for_config()`: Interactive configuration setup
- User prompts and validation
- Configuration testing and saving

## Legacy Compatibility

The original `main.py` and `setup.py` files are preserved for backward compatibility, but new development should use the modular structure.
