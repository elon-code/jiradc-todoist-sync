@echo off
cd %~dp0
git pull origin main
git checkout main
python -m pip install -r requirements.txt
python main.py > run_jira_sync.log 2>&1
echo Sync completed. Check run_jira_sync.log for details.