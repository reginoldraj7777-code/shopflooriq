@echo off
setlocal
cd /d "%~dp0"
set "SFIQ_PYTHON="
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "SFIQ_PYTHON=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if defined SFIQ_PYTHON goto run
if exist "%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe" set "SFIQ_PYTHON=%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe"
if defined SFIQ_PYTHON goto run
where py >nul 2>&1
if not errorlevel 1 set "SFIQ_PYTHON=py"
if defined SFIQ_PYTHON goto run
where python >nul 2>&1
if not errorlevel 1 set "SFIQ_PYTHON=python"
if defined SFIQ_PYTHON goto run
echo Python 3.11 or newer is required. Install Python and reopen this terminal.
exit /b 1
:run
"%SFIQ_PYTHON%" -c "import sys; assert sys.version_info >= (3,11), 'Python 3.11+ required'"
if errorlevel 1 exit /b 1
"%SFIQ_PYTHON%" -m scripts.recording %*
exit /b %errorlevel%
