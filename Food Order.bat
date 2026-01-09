@echo off
REM  --- This script launches the Options Streamlit application ---

ECHO Navigating to the project directory...
REM IMPORTANT: Replace the path below with the actual path to your project folder.
cd /d "C:\Users\suhaimi.abdullah\Desktop\Food"

ECHO Activating the Python virtual environment...
REM This assumes your environment is named 'venv' inside your project folder.
call .\venv\Scripts\activate

ECHO Launching the Options Application...
REM IMPORTANT: Replace 'xxxxx.py' if your Python file has a different name.
streamlit run app.py

ECHO The application has been closed.
pause
