@echo off
cd %~dp0
git checkout main
python main.py > run_jira_sync.log 2>&1
echo Sync completed. Check run_jira_sync.log for details.