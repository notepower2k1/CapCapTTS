@echo off
chcp 65001 >nul
title Setup Portable Python for TTS
cd /d "%~dp0"

set MODE=%1
if "%MODE%"=="" set MODE=gpu

echo ========================================
echo  Setup Portable Python Environment
echo  Mode: %MODE%
echo ========================================
echo.

if /i "%MODE%"=="cpu" (
    set PORTABLE_DIR=python-portable-cpu
    set REQ_FILE=backend_cpu\requirements.txt
) else (
    set PORTABLE_DIR=python-portable
    set REQ_FILE=backend\requirements.txt
)

REM Check Python (needed for setup tools). Some Windows installations expose
REM Python through the py launcher while the python.exe app alias is disabled.
python --version >nul 2>&1
if %ERRORLEVEL% EQU 0 goto :python_ready
py -3 --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [FAIL] Python not found in PATH. Install Python 3.11 first.
    pause
    exit /b 1
)
:python_ready

if exist "%PORTABLE_DIR%\python.exe" (
    echo [INFO] %PORTABLE_DIR% already exists. Delete folder to redo.
    pause
    exit /b 0
)

echo [1/5] Downloading embeddable Python 3.11.9...
powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip' -OutFile '%~dp0python-embed.zip' -UseBasicParsing"
if %ERRORLEVEL% NEQ 0 (
    echo [FAIL] Download failed. Check internet.
    pause
    exit /b 1
)

echo [2/5] Extracting...
powershell -Command "Expand-Archive -Path '%~dp0python-embed.zip' -DestinationPath '%~dp0%PORTABLE_DIR%' -Force"
del "%~dp0python-embed.zip"

echo [3/5] Configuring embeddable Python...
echo python311.zip> "%PORTABLE_DIR%\python311._pth"
echo .>> "%PORTABLE_DIR%\python311._pth"
echo Lib\site-packages>> "%PORTABLE_DIR%\python311._pth"
echo.>> "%PORTABLE_DIR%\python311._pth"
echo import site>> "%PORTABLE_DIR%\python311._pth"

echo [4/5] Installing pip...
powershell -Command "Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile '%~dp0get-pip.py' -UseBasicParsing"
"%PORTABLE_DIR%\python.exe" "%~dp0get-pip.py"
del "%~dp0get-pip.py"

echo [5/5] Installing dependencies ^(this takes a while^)...
if /i "%MODE%"=="gpu" (
    echo --- Installing GPU torch [CUDA 12.4] ---
    "%PORTABLE_DIR%\python.exe" -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124 --quiet
    echo.
)
echo --- Installing %MODE% backend deps ---
"%PORTABLE_DIR%\python.exe" -m pip install -r "%REQ_FILE%" --quiet

echo.
echo ========================================
echo  Done!
echo ========================================
echo.
echo This environment is for maintainers who build the Electron installer.
echo Run: npm run prepare:runtime
if /i "%MODE%"=="gpu" echo Then: npm run build:gpu
if /i "%MODE%"=="cpu" echo Then: npm run build:cpu
echo.
pause
