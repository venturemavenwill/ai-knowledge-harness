@echo off
setlocal
where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  py -3 "%~dp0aikb.py" %*
  exit /b %ERRORLEVEL%
)
where python3 >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  python3 "%~dp0aikb.py" %*
  exit /b %ERRORLEVEL%
)
where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  python "%~dp0aikb.py" %*
  exit /b %ERRORLEVEL%
)
echo ABSTENTION  Python 3.9 or newer is required but was not found on PATH. 1>&2
exit /b 2
