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
echo   [B] Batch queue (multiple commercial posting files)
echo   [D] Dry run only
echo   [Q] Questions only (rebuild qualifications statement from current JD + questions)
echo.
choice /c RFBDQ /n /m "Selection [R/F/B/D/Q]: "
if errorlevel 5 goto :run_questions
if errorlevel 4 goto :run_dry
if errorlevel 3 goto :run_batch
if errorlevel 2 goto :run_full
call :run_task resume --resume-only
set "TASK_EXIT=%ERRORLEVEL%"
if "%TASK_EXIT%"=="124" goto :timed_out
if "%TASK_EXIT%"=="2" goto :review_required
if not "%TASK_EXIT%"=="0" goto :failed
goto :done

:run_questions
call :run_task qualifications
set "TASK_EXIT=%ERRORLEVEL%"
if "%TASK_EXIT%"=="124" goto :timed_out
if "%TASK_EXIT%"=="2" goto :review_required
if not "%TASK_EXIT%"=="0" goto :failed
goto :done

:run_dry
call :run_task dry-run
set "TASK_EXIT=%ERRORLEVEL%"
if "%TASK_EXIT%"=="124" goto :timed_out
if "%TASK_EXIT%"=="2" goto :review_required
if not "%TASK_EXIT%"=="0" goto :failed
goto :done

:run_full
call :run_task resume
set "TASK_EXIT=%ERRORLEVEL%"
if "%TASK_EXIT%"=="124" goto :timed_out
if "%TASK_EXIT%"=="2" goto :review_required
if not "%TASK_EXIT%"=="0" goto :failed
goto :done

:run_batch
echo.
choice /c RF /n /m "Build every queued posting as Resume-only or Full workflow? [R/F]: "
if errorlevel 2 goto :run_batch_full
call :run_task resume-queue --resume-only
set "TASK_EXIT=%ERRORLEVEL%"
goto :handle_batch_result

:run_batch_full
call :run_task resume-queue
set "TASK_EXIT=%ERRORLEVEL%"

:handle_batch_result
if "%TASK_EXIT%"=="124" goto :timed_out
if "%TASK_EXIT%"=="2" goto :review_required
if not "%TASK_EXIT%"=="0" goto :failed
goto :done

:review_required
echo.
echo The workflow completed with an artifact that requires review.
echo See the Python message above for the artifact-specific result and next action.
goto :done

:timed_out
echo.
echo The workflow failed because a required step exceeded its time limit.
echo Review the Python message and full log above before rerunning.
goto :failed

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
