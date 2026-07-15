@echo off
setlocal
cd /d "%~dp0"

if not exist "output" mkdir "output"

call :resolve_python || goto :failed
echo Workspace root: %CD%
echo Python: %RESOLVED_PYTHON%
"%RESOLVED_PYTHON%" ".\scripts\workspace_health.py" --banner --require-healthy
if errorlevel 1 goto :failed

echo.
echo This builds the interview cheat sheet and the detailed commercial interview guide.
choice /c YN /n /m "Continue? [Y/N] "
if errorlevel 2 goto :done
echo.
echo Choose the interview stage for the detailed guide:
echo   [1] HR
echo   [2] Hiring Mgr
echo   [3] Panel
echo   [4] Presentation
echo   [5] Technical
echo   [6] Final
echo   [7] All
choice /c 1234567 /n /m "Selection [1-7]: "
set "GUIDE_STAGE=hr_screen"
if errorlevel 7 set "GUIDE_STAGE=all"
if errorlevel 6 set "GUIDE_STAGE=final"
if errorlevel 5 set "GUIDE_STAGE=technical"
if errorlevel 4 set "GUIDE_STAGE=presentation"
if errorlevel 3 set "GUIDE_STAGE=panel"
if errorlevel 2 set "GUIDE_STAGE=hiring_manager"
call :run_task interview || goto :failed
call :run_task guide --stage %GUIDE_STAGE% || goto :failed
call :offer_companions || goto :failed
goto :done

:offer_companions
if /I "%GUIDE_STAGE%"=="hr_screen" call :offer_companion recruiter_screen "Also build the Recruiter Screen Prep companion? [Y/N] " || exit /b 1
if /I "%GUIDE_STAGE%"=="hiring_manager" call :offer_companion first_90_days "Also build the 90 Day One-Pager companion? [Y/N] " || exit /b 1
call :check_companion debrief_addendum
if errorlevel 1 exit /b 0
call :offer_companion debrief_addendum "Also build the Debrief Prep Addendum companion? [Y/N] " || exit /b 1
exit /b 0

:offer_companion
set "COMPANION_MODE=%~1"
set "COMPANION_PROMPT=%~2"
echo.
choice /c YN /n /m "%COMPANION_PROMPT%"
if errorlevel 2 exit /b 0
call :run_companion %COMPANION_MODE%
exit /b %ERRORLEVEL%

:check_companion
"%RESOLVED_PYTHON%" ".\scripts\build_interview_companions.py" --mode %1 --check >nul 2>nul
exit /b %ERRORLEVEL%

:run_companion
echo.
echo Running: python scripts\build_interview_companions.py --mode %*
"%RESOLVED_PYTHON%" ".\scripts\build_interview_companions.py" --mode %*
exit /b %ERRORLEVEL%

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
