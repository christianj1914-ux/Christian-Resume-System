@echo off

setlocal

cd /d "%~dp0"

call :resolve_python || goto :failed

echo Workspace root: %CD%
echo Python: %RESOLVED_PYTHON%
"%RESOLVED_PYTHON%" ".\scripts\workspace_health.py" --banner --require-healthy
if errorlevel 1 goto :failed

if not exist ".\output" mkdir ".\output"

echo.
echo Choose what to build:
echo   [R] Resume only
echo   [F] Full workflow (resume + cover letter + qualifications)
echo   [D] Dry run only
echo.
choice /c RFD /n /m "Selection [R/F/D]: "
if errorlevel 3 goto :run_dry
if errorlevel 2 goto :run_full
call :run_task resume --resume-only
if errorlevel 1 goto :failed
goto :done

:run_dry
call :run_task dry-run || goto :failed
goto :done

:run_full
call :run_task resume
if errorlevel 2 goto :draft_cover_letter
if errorlevel 1 goto :failed
goto :done

:draft_cover_letter
echo.
echo Resume created, but the cover letter was saved as DRAFT.
echo Qualifications and later steps were skipped by design.
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
