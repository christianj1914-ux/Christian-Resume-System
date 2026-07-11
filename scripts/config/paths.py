"""Centralized path exports for Christian Resume System.

All scripts should import paths from this module instead of defining their own
PROJECT_ROOT and subdirectory paths. This ensures consistent path resolution
across different platforms and working directories.

Usage:
    from config.paths import PROJECT_ROOT, JOB_DESCRIPTION, OUTPUT_DIR
"""

from pathlib import Path

# Root project directory (parent of scripts directory)
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Job management paths
JOBS_DIR = PROJECT_ROOT / "jobs"
JOB_DESCRIPTION = JOBS_DIR / "job_description.txt"
FEDERAL_JOB_DESCRIPTION = JOBS_DIR / "federal_job_description.txt"
APPLICATION_QUESTIONS = JOBS_DIR / "application_questions.txt"
COMPANY_RESEARCH = JOBS_DIR / "company_research.txt"
INTERVIEW_NOTES = JOBS_DIR / "interview_notes.txt"
DEBRIEF_HISTORY = JOBS_DIR / "debrief_history.txt"
COMPANY_NOTES_DIR = JOBS_DIR / "company_notes"
INTERVIEW_DEBRIEFS_DIR = JOBS_DIR / "interview_debriefs"
INTERVIEW_NOTES_BY_COMPANY_DIR = JOBS_DIR / "interview_notes_by_company"

# Source resume files
SOURCE_DIR = PROJECT_ROOT / "source"
FEDERAL_RESUME_SOURCE = SOURCE_DIR / "Christian_Estrada_Federal_Source.json"
FEDERAL_ESSAY_SOURCE = SOURCE_DIR / "Christian_Estrada_Federal_Standard_Essays.json"
GLOBAL_NOTES = SOURCE_DIR / "global_notes.txt"

# Output directory for generated documents
OUTPUT_DIR = PROJECT_ROOT / "output"

# Working directories
SCRATCH_DIR = PROJECT_ROOT / "scratch"
SCRATCH_JD_LIBRARY = SCRATCH_DIR / "jd_library"
SCRATCH_TARGET_JDS = SCRATCH_DIR / "target_jds"
SCRATCH_JOBS_ARCHIVE = SCRATCH_DIR / "jobs_archive"
SCRATCH_APPLICATIONS_CSV = SCRATCH_DIR / "applications.csv"
SCRATCH_RENDER_LOGS = SCRATCH_DIR / "run_logs"

# Backup and archive
BACKUPS_DIR = PROJECT_ROOT / "backups"
RENDER_CHECK_DIR = PROJECT_ROOT / "render_check"

# Python executable (for subprocess calls)
PYTHON_EXECUTABLE = Path(__file__).resolve().parent.parent.parent / "venv" / "bin" / "python"
if not PYTHON_EXECUTABLE.exists():
    # Fallback to system Python if venv not found
    import sys
    PYTHON_EXECUTABLE = Path(sys.executable)

# Scripts directory
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
