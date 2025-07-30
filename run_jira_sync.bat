@echo off
setlocal
REM Ensure script runs in its own directory
cd /d "%~dp0"

REM Environment variables (optional - will be prompted if not set):
REM set JIRA_API_TOKEN=your_jira_token_here
REM set TODOIST_API_TOKEN=your_todoist_token_here
REM set JIRA_SERVER_URL=https://your-jira-instance.atlassian.net

REM Check Python availability
python --version >nul 2>&1 || (
    echo Python not found in PATH. Please install Python or add it to PATH.
    pause
    exit /b 1
)

REM Activate or create virtual environment
if exist "venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call "venv\Scripts\activate.bat"
) else (
    echo Creating virtual environment...
    python -m venv venv || (
        echo Failed to create virtual environment.
        pause
        exit /b 1
    )
    call "venv\Scripts\activate.bat"
)

echo Pulling latest code...
git pull origin main || goto gitfail
echo Checking out main...
git checkout main || goto gitfail

echo Installing dependencies...
python -m pip install -r requirements.txt || goto pipfail

echo Running Jira-to-Todoist sync...
python main.py || goto runfail

goto done

:gitfail
echo Git operation failed.
pause
exit /b 1

:pipfail
echo Dependency installation failed.
pause
exit /b 1

:runfail
echo Script execution failed.
pause
exit /b 1

:done
echo Sync completed successfully.
pause
exit /b 0