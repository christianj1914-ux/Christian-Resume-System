@echo off
setlocal
cd /d "%~dp0"

call :resolve_python || goto :failed
echo Workspace root: %CD%
echo Python: %RESOLVED_PYTHON%
"%RESOLVED_PYTHON%" ".\scripts\workspace_health.py" --banner --require-healthy
if errorlevel 1 goto :failed

set "RAN_ANY="
echo.
echo Choose either step, both steps, or skip both.
echo - Prepare company notes opens or refreshes the company dossier scaffold.
echo - Debrief captures fresh interview details after a conversation.
echo.
choice /c YN /n /m "Prepare company notes first? [Y/N] "
if errorlevel 2 goto :skip_notes
call :run_task prepare-company-notes || goto :failed
set "RAN_ANY=1"

:skip_notes
choice /c YN /n /m "Capture a post-interview debrief now? [Y/N] "
if errorlevel 2 goto :after_debrief
call :run_task debrief || goto :failed
set "RAN_ANY=1"

:after_debrief
if defined RAN_ANY goto :done
echo.
echo No step selected.
goto :done

:done
echo.
pause
exit /b 0

:failed
echo.
echo The launcher stopped before continuing.
pause
exit /b 1

:resolve_python
if defined RESUME_PYTHON if exist "%RESUME_PYTHON%" set "RESOLVED_PYTHON=%RESUME_PYTHON%"
if not defined RESOLVED_PYTHON if exist "%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" set "RESOLVED_PYTHON=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if not defined RESOLVED_PYTHON for /f "delims=" %%P in ('where python 2^>nul') do if not defined RESOLVED_PYTHON set "RESOLVED_PYTHON=%%P"
if not defined RESOLVED_PYTHON (
  echo ERROR: No usable Python executable found. Set RESUME_PYTHON or install Python 3.11+.
  exit /b 1
)
exit /b 0

:run_task
echo.
echo Running: python tasks.py %*
"%RESOLVED_PYTHON%" ".\tasks.py" %*
exit /b %ERRORLEVEL%
