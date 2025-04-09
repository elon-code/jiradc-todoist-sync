@echo off
cd %~dp0
git pull origin dev
git checkout dev
python -m pip install -r requirements.txt
python main.py
pause