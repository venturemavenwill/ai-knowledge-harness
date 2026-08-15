@echo off
REM Interpreter discovery uses goto rather than parenthesised if-blocks: cmd
REM expands %ERRORLEVEL% when it parses a whole block, so a block would report
REM the result of where instead of the result of Python and always exit 0.
setlocal
where py >nul 2>nul && goto :use_py
where python3 >nul 2>nul && goto :use_python3
where python >nul 2>nul && goto :use_python
echo ABSTENTION  Python 3.9 or newer is required but was not found on PATH. 1>&2
exit /b 2

:use_py
py -3 "%~dp0aikb.py" %*
exit /b %ERRORLEVEL%

:use_python3
python3 "%~dp0aikb.py" %*
exit /b %ERRORLEVEL%

:use_python
python "%~dp0aikb.py" %*
exit /b %ERRORLEVEL%