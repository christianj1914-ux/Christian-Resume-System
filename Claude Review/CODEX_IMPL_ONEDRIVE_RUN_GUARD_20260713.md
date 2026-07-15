# Codex Implementation Note: OneDrive Run Guard in canonical tasks.py

Date: 2026-07-13
Author: Claude (planner/reviewer pass)
Target repo: C:\dev\Christian-Resume-System (canonical only)

## Objective

Close the one residual retirement gap: a manual `python tasks.py ...` run from the
retired OneDrive archive copy still bypasses the `.bat` redirect stubs. Add a
fail-fast guard to the canonical `tasks.py` so that any tree carrying the
`DO_NOT_RUN_FROM_ONEDRIVE.txt` sentinel refuses to run.

The guard lives in canonical because canonical is the maintained source of truth.
It is inert in canonical (no sentinel there) and trips automatically in any copy
that has the sentinel, so it travels with the code and never needs to be
maintained in the archive.

## Do not do

Do not edit the OneDrive copy of `tasks.py` or anything else under
`C:\Users\chris\OneDrive\Desktop\Christian Resume System`. That tree is retired
and archival only. This change is canonical-side.

## File and location

- File: `tasks.py` (repo root)
- `Path` is already imported (line 20) and `PROJECT_ROOT = Path(__file__).resolve().parent`
  already exists (line 29). Reuse `PROJECT_ROOT`; do not add a new root constant.
- Insert a small helper immediately above `def main() -> int:` (currently line 862),
  then call it as the first statement inside `main()`.

## Change 1: add the helper (immediately above `def main()`)

```python
def _onedrive_run_guard(root: Path = PROJECT_ROOT) -> int | None:
    """Refuse to run from the retired OneDrive archive copy.

    The canonical repo has no sentinel, so this returns None there and the run
    proceeds normally. If tasks.py is ever executed from a tree that carries
    DO_NOT_RUN_FROM_ONEDRIVE.txt (the retired OneDrive copy), return exit code 2
    instead of running any command.
    """
    if (root / "DO_NOT_RUN_FROM_ONEDRIVE.txt").exists():
        print(
            "Refusing to run: this is the retired OneDrive archive copy. "
            "Use the canonical repo at C:\\dev\\Christian-Resume-System."
        )
        return 2
    return None
```

## Change 2: call it first inside `main()`

Current head of `main()` (line 862 onward):

```python
def main() -> int:
    if len(sys.argv) < 2:
        print_help()
        return 0
    command = sys.argv[1].lower()
```

Change to:

```python
def main() -> int:
    guard = _onedrive_run_guard()
    if guard is not None:
        return guard
    if len(sys.argv) < 2:
        print_help()
        return 0
    command = sys.argv[1].lower()
```

The guard runs before the argv-length check on purpose, so even a bare
`python tasks.py` from the OneDrive copy refuses rather than printing help. It
returns an int (not `raise SystemExit`) to match the `main() -> int` contract;
`__main__` already does `raise SystemExit(main())` at the bottom of the file.

## Validation (run in canonical)

1. `python tasks.py help` prints normal help, exit 0.
2. `python tasks.py validate` still passes at the current count (expected 296/296).
3. `python tasks.py federal-dry-run` unchanged.
4. Guard-trip smoke check, using a throwaway sentinel:
   - Create `DO_NOT_RUN_FROM_ONEDRIVE.txt` at the canonical repo root.
   - Run `python tasks.py help` and confirm it prints the refusal and exits 2
     (`echo %ERRORLEVEL%` on Windows, `echo $?` in bash).
   - Delete that throwaway sentinel immediately so canonical stays runnable.
   - Confirm `git status` shows no stray `DO_NOT_RUN_FROM_ONEDRIVE.txt` before commit.

## Regression coverage

Add a unit test alongside the existing suite (or `tests/test_onedrive_guard.py`
if there is no natural home) that exercises the helper directly, since it takes an
injectable `root`:

```python
from pathlib import Path
import tasks

def test_onedrive_guard_absent(tmp_path: Path) -> None:
    assert tasks._onedrive_run_guard(tmp_path) is None

def test_onedrive_guard_present(tmp_path: Path) -> None:
    (tmp_path / "DO_NOT_RUN_FROM_ONEDRIVE.txt").write_text("retired", encoding="utf-8")
    assert tasks._onedrive_run_guard(tmp_path) == 2
```

This keeps the guard covered without needing a subprocess and without touching
module-level `PROJECT_ROOT`.

## Notes

- The `.bat` launchers in canonical call `python tasks.py ...` and therefore
  inherit the guard automatically; no `.bat` edits are needed.
- Optional, only if Christian wants an escape hatch for deliberate archive
  testing: honor an env var (for example `RESUME_ALLOW_ONEDRIVE=1`) to skip the
  guard. Left out by default to keep the guard simple and hard to bypass by accident.
