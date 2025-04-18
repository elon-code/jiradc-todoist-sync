@echo off
cd %~dp0

REM Activate virtual environment if it exists, otherwise create it
if exist venv\Scripts\activate (
    call venv\Scripts\activate
) else (
    python -m venv venv
    call venv\Scripts\activate
)

git pull origin dev
git checkout dev
python -m pip install -r requirements.txt
python main.py
pause