# Codex Spec: Federal Mandatory-Field Render Guarantee (first federal pass)

## Context
First change to the federal workflow. Deliberately small and safe; federal is high-stakes.
The two-page federal resume cap is INTENTIONAL and stays (confirmed by Christian). This pass
does not touch the cap, the selection logic, or the qualifications statement. It only closes
one eligibility gap.

## Problem (grounded in code)
`federal_plain_text_validation()` in `scripts/build_federal_resume.py` (~line 2579) treats
these as hard BLOCKERS: missing required sections, missing email, missing role date ranges,
missing `Supervisor:` lines. But it treats these as soft WARNINGS only:
- `if "Hours Per Week" not in visible:` -> warning (line ~2592)
- `if "$" not in visible:` (salary) -> warning (line ~2594)

Hours-per-week and salary are hard-validated at the SOURCE (each role must have a numeric
hours_per_week and a salary), but whether they RENDER into the final document is not enforced.
With the two-page trim dropping content to fit, a position could lose its hours or salary in
the output and the build would still pass. For USAJOBS, a position without hours-per-week and
salary cannot be credited toward a grade level, which is an eligibility failure. Supervisor
lines are already a blocker; hours and salary are equally mandatory and should match.

## Change
In `federal_plain_text_validation()`, promote the hours-per-week and salary checks from
`warnings` to `blockers`, consistent with the existing supervisor/date/email blockers.

Make them robust and per-role, not just document-wide:
- The resume already renders one block per employer (see `_employer_text_block`). For EACH
  rendered position, assert the block contains a Hours-Per-Week value AND a salary figure.
  A single position missing either is a blocker naming that employer, e.g.
  "Federal eligibility blocker: <Employer> is missing Hours Per Week in the rendered resume."
- Salary detection should be a real pattern (e.g. `\$\d[\d,]*`), not a bare `$`, so an
  unrelated `$` elsewhere cannot satisfy it.
- Keep the existing source-level hard validations exactly as they are.

## Guardrails
- Do NOT weaken the two-page cap or any existing blocker. This only ADDS blockers.
- If a real federal build now fails because hours/salary did not render, that is a genuine
  rendering/trim defect to FIX in the layout path, not to downgrade back to a warning. (If
  the trim is dropping a mandatory header to fit two pages, the header must be protected from
  trimming the same way dates/supervisor are; note it and fix rather than relax the check.)
- No changes to the qualifications statement, KSA responses, cover, or interview docs in this
  pass.
- Truthfulness and all existing behavior unchanged.

## Tests
- A federal resume whose visible text is missing Hours Per Week for a position fails
  validation with a per-employer blocker.
- A resume missing a salary figure fails validation.
- A complete resume (all positions have hours + salary) passes.
- The bare-`$` false positive is rejected (a `$` outside a salary context does not satisfy the
  salary check).
- Existing federal smoke/validate tests still pass.
- Run: `python scripts\smoke_test.py`, `python tasks.py validate`, `python tasks.py source-lint`,
  and `python scripts\run_federal_resume_workflow.py --dry-run`.

## Verification
- Build the federal resume against the current active `jobs/federal_job_description.txt`
  (or a representative saved posting). Confirm it still resolves to exactly two pages, all
  positions show Hours Per Week and salary in the visible text, and the build passes.
- Confirm the qualifications statement still builds within its 3-page budget (unchanged).
- Report the visible per-employer header lines so the mandatory fields can be eyeballed.

## Roadmap (queued for later federal passes, NOT this one)
1. KSA-response quality: prefer supported specialized-experience narratives over
   `generic_ksa_response` boilerplate, since HR scores these.
2. Two-page selection: when trimming to fit, prioritize bullets that match the announcement's
   specialized-experience / KSA terms so the limited space maximizes the rating (the code
   already warns when supported experience is not visible in the two-page resume).
3. Federal cover/interview conventions: the cover and interview docs delegate to the
   commercial engines; add announcement number, series/grade, and formal federal tone.
4. Federal questionnaire keyword aid: a conservative, federal-appropriate version of the
   commercial coverage discipline for self-rating questionnaires.

## Assumptions
- One focused commit. Do not stage generated outputs, active jobs/ files, or spec docs.
- Two-page cap stays. Federal remains on the same branch; no merge.
