@echo off
setlocal EnableDelayedExpansion

:: Check admin rights (needed for installing Python/Node)
net session >nul 2>&1
set "ADMIN=0"
if %errorlevel% == 0 set "ADMIN=1"

set "PROJECT_DIR=%~dp0"
set "BACKEND_DIR=%PROJECT_DIR%backend"
set "FRONTEND_DIR=%PROJECT_DIR%frontend"
set "VENV_DIR=%BACKEND_DIR%\.venv"
set "TEMP_DIR=%PROJECT_DIR%\.tmp"

echo ============================================
echo Quan ly Tai san Viet Nam - Auto Launcher
echo ============================================

if not exist "%TEMP_DIR%" mkdir "%TEMP_DIR%"

:: --- Python ---
:CheckPython
python --version >nul 2>&1
if %errorlevel% == 0 goto PythonOK

:: Try py launcher as alias
py --version >nul 2>&1
if %errorlevel% == 0 (
    echo Using Python launcher 'py'.
    set "PYTHON_CMD=py"
    goto PythonOK
)

echo.
echo Python khong tim thay. Dang tu dong cai dat...
echo Python not found. Attempting auto-install...
if %ADMIN% == 0 (
    echo Vui long chay file nay voi quyen Administrator de tu dong cai dat.
    echo Please run this launcher as Administrator to auto-install.
    pause
    exit /b 1
)

where winget >nul 2>&1
if %errorlevel% == 0 (
    echo Installing Python via winget...
    winget install Python.Python.3.13 --silent --accept-package-agreements --accept-source-agreements
    if %errorlevel% == 0 goto RefreshPython
)

:: Fallback direct download
if not exist "%TEMP_DIR%\python-installer.exe" (
    echo Downloading Python installer...
    curl -L -o "%TEMP_DIR%\python-installer.exe" "https://www.python.org/ftp/python/3.13.0/python-3.13.0-amd64.exe" >nul 2>&1
    if errorlevel 1 (
        echo Tai ve that bai. Vui long cai dat thu cong tu https://www.python.org/downloads/
        echo Download failed. Please install manually from https://www.python.org/downloads/
        pause
        exit /b 1
    )
)
echo Installing Python silently...
"%TEMP_DIR%\python-installer.exe" /quiet InstallAllUsers=0 PrependPath=1 Include_pip=1
if errorlevel 1 (
    echo Cai dat Python that bai.
    echo Python installation failed.
    pause
    exit /b 1
)

:RefreshPython
:: Refresh PATH in current session
for /f "delims=" %%a in ('powershell -NoProfile -Command "[Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [Environment]::GetEnvironmentVariable('Path', 'User')"') do set "PATH=%%a"
python --version >nul 2>&1
if errorlevel 1 (
    echo Python van khong tim thay sau khi cai dat. Vui long khoi dong lai may va chay lai.
    echo Python still not found after install. Please restart and try again.
    pause
    exit /b 1
)
if exist "%TEMP_DIR%\python-installer.exe" del /f /q "%TEMP_DIR%\python-installer.exe"

:PythonOK
if not defined PYTHON_CMD set "PYTHON_CMD=python"
echo Python OK: 
%PYTHON_CMD% --version

:: --- Node.js ---
:CheckNode
node --version >nul 2>&1
if %errorlevel% == 0 goto NodeOK

echo.
echo Node.js khong tim thay. Dang tu dong cai dat...
echo Node.js not found. Attempting auto-install...
if %ADMIN% == 0 (
    echo Vui long chay file nay voi quyen Administrator de tu dong cai dat.
    echo Please run this launcher as Administrator to auto-install.
    pause
    exit /b 1
)

where winget >nul 2>&1
if %errorlevel% == 0 (
    echo Installing Node.js via winget...
    winget install OpenJS.NodeJS --silent --accept-package-agreements --accept-source-agreements
    if %errorlevel% == 0 goto RefreshNode
)

if not exist "%TEMP_DIR%\node-installer.msi" (
    echo Downloading Node.js installer...
    curl -L -o "%TEMP_DIR%\node-installer.msi" "https://nodejs.org/dist/v22.11.0/node-v22.11.0-x64.msi" >nul 2>&1
    if errorlevel 1 (
        echo Tai ve that bai. Vui long cai dat thu cong tu https://nodejs.org/
        echo Download failed. Please install manually from https://nodejs.org/
        pause
        exit /b 1
    )
)
echo Installing Node.js silently...
msiexec /i "%TEMP_DIR%\node-installer.msi" /qn
if errorlevel 1 (
    echo Cai dat Node.js that bai.
    echo Node.js installation failed.
    pause
    exit /b 1
)

:RefreshNode
for /f "delims=" %%a in ('powershell -NoProfile -Command "[Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [Environment]::GetEnvironmentVariable('Path', 'User')"') do set "PATH=%%a"
node --version >nul 2>&1
if errorlevel 1 (
    echo Node.js van khong tim thay sau khi cai dat. Vui long khoi dong lai may va chay lai.
    echo Node.js still not found after install. Please restart and try again.
    pause
    exit /b 1
)
if exist "%TEMP_DIR%\node-installer.msi" del /f /q "%TEMP_DIR%\node-installer.msi"

:NodeOK
echo Node.js OK: 
node --version

:: Create venv if missing
if not exist "%VENV_DIR%" (
    echo Creating Python virtual environment...
    %PYTHON_CMD% -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo Failed to create virtual environment.
        pause
        exit /b 1
    )
)

:: Create data dir if missing
if not exist "%BACKEND_DIR%\data" mkdir "%BACKEND_DIR%\data"

:: Copy .env example if no .env exists
if not exist "%BACKEND_DIR%\.env" (
    copy "%BACKEND_DIR%\.env.example" "%BACKEND_DIR%\.env" >nul
)

:: Activate venv and install backend deps
call "%VENV_DIR%\Scripts\activate.bat"
echo Installing / updating backend dependencies...
pip install -q -r "%BACKEND_DIR%\requirements.txt"
if errorlevel 1 (
    echo Backend dependency install failed.
    pause
    exit /b 1
)

:: Install frontend deps if node_modules missing
if not exist "%FRONTEND_DIR%\node_modules" (
    echo Installing frontend dependencies...
    call npm install --prefix "%FRONTEND_DIR%"
    if errorlevel 1 (
        echo Frontend dependency install failed.
        pause
        exit /b 1
    )
)

:: Start backend API in the same window
echo Starting backend API on http://localhost:8000
start /b "WealthVN Backend" cmd /c "cd /d "%BACKEND_DIR%" && call "%VENV_DIR%\Scripts\activate.bat" && python main.py"

:: Start frontend UI in the same window
echo Starting frontend UI on http://localhost:5173
start /b "WealthVN Frontend" cmd /c "cd /d "%FRONTEND_DIR%" && npm run dev"

:: Wait for servers then open browser
timeout /t 6 /nobreak >nul
start http://localhost:5173

echo.
echo App running in this window.
echo Backend API at http://localhost:8000
echo Frontend UI at http://localhost:5173
echo.
echo Nhan phim bat ky de dung ca hai server...
pause >nul

:: Clean up temp install files if any remain
if exist "%TEMP_DIR%\python-installer.exe" del /f /q "%TEMP_DIR%\python-installer.exe"
if exist "%TEMP_DIR%\node-installer.msi" del /f /q "%TEMP_DIR%\node-installer.msi"
if exist "%TEMP_DIR%" rmdir /s /q "%TEMP_DIR%" 2>nul

endlocal
