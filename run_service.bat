@echo off
chcp 65001 >nul
setlocal EnableExtensions EnableDelayedExpansion

set "ROOT_DIR=%~dp0"
if "%ROOT_DIR:~-1%"=="\" set "ROOT_DIR=%ROOT_DIR:~0,-1%"
if "%APP_HOST%"=="" (
    set "APP_HOST=0.0.0.0"
)
if "%APP_PORT%"=="" (
    set "APP_PORT=8191"
)
set "UV_INSTALL_DIR=%ROOT_DIR%\.tools\uv"
set "UV_BIN=%UV_INSTALL_DIR%\uv.exe"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "PYTHONWARNINGS=ignore:pkg_resources is deprecated as an API:UserWarning"
set "PYTHON_VERSION=3.12.13"

call :ensure_uv
if %errorlevel% neq 0 exit /b 1

call :ensure_venv
if %errorlevel% neq 0 exit /b 1

pushd "%ROOT_DIR%"
"%UV_BIN%" sync
if %errorlevel% neq 0 (
    popd
    echo uv sync failed.
    exit /b 1
)
"%UV_BIN%" pip install --python "%ROOT_DIR%\.venv\Scripts\python.exe" -r "%ROOT_DIR%\requirements.cuda.txt"
if %errorlevel% neq 0 (
    popd
    echo CUDA torch dependency install failed.
    exit /b 1
)
popd

if not exist "%ROOT_DIR%\.venv\Scripts\python.exe" (
    echo Virtual environment python not found after uv sync.
    exit /b 1
)

echo Running in foreground. Close this window to stop the service.
echo Logs: console only
echo Listening on host: %APP_HOST%
echo Listening on port: %APP_PORT%

pushd "%ROOT_DIR%"
"%ROOT_DIR%\.venv\Scripts\python.exe" -m translator_server.main
set "RUN_EXIT=%errorlevel%"
popd
exit /b %RUN_EXIT%

:command_exists
where %~1 >nul 2>nul
exit /b %errorlevel%

:ensure_uv
call :command_exists uv
if %errorlevel%==0 (
    for /f "delims=" %%I in ('where uv') do (
        set "UV_BIN=%%I"
        goto :uv_ready
    )
)

if exist "%UV_BIN%" goto :uv_ready

echo uv not found, installing it with the official installer...
if not exist "%UV_INSTALL_DIR%" mkdir "%UV_INSTALL_DIR%"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$env:UV_UNMANAGED_INSTALL='%UV_INSTALL_DIR%'; irm https://astral.sh/uv/install.ps1 | iex"
if %errorlevel% neq 0 (
    echo Failed to install uv automatically.
    exit /b 1
)

if not exist "%UV_BIN%" (
    echo Failed to install uv automatically.
    exit /b 1
)

:uv_ready
exit /b 0

:ensure_venv
if exist "%ROOT_DIR%\.venv\Scripts\python.exe" if exist "%ROOT_DIR%\.venv\pyvenv.cfg" exit /b 0

if exist "%ROOT_DIR%\.venv" (
    echo Existing virtual environment is incomplete. Recreating .venv ...
    rmdir /s /q "%ROOT_DIR%\.venv"
    if exist "%ROOT_DIR%\.venv" (
        echo Failed to remove broken .venv. Please close processes using it and try again.
        exit /b 1
    )
)

pushd "%ROOT_DIR%"
"%UV_BIN%" venv --python %PYTHON_VERSION%
set "VENV_EXIT=%errorlevel%"
popd
exit /b %VENV_EXIT%
