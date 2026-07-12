@echo off
setlocal
cd /d "%~dp0"
echo This repo is already the canonical repo.
echo To bootstrap a new canonical repo from another source workspace, run scripts\bootstrap_canonical_repo.py with an explicit --source-root and --canonical-root.
pause
exit /b 0
