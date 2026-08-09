# Codex Spec: Finish the Ledger Pass Efficiently (recovery + process fix)

## Where we actually are
- The render-boundary placement fix WORKS. Earlier Phase A attempts (07:33, 08:27, 09:39)
  built both priority resumes PASS with all six terms present. The hard part is done.
- The 4-hour loop was caused by turning "naturalness" into a hard, build-stopping assertion.
  Naturalness is not machine-decidable, so the assertion oscillated and finally aborted the
  build (resume_status = MISSING). Discard that approach entirely.

## The reframe that dissolves the whole problem
For ATS callbacks, a keyword in the Skills section counts fully. A Skills list is terse by
nature, so it never has a naturalness problem. Therefore:

- Skills placement is a FIRST-CLASS home for ledger terms, not a failure fallback.
- Prose weaving is OPTIONAL and only for terms with an obviously clean home.
- If a prose weave would produce a jammed sentence (e.g. "vendor partner, cost, and timeline",
  "and implementation project", "adopted AI pilot work"), DO NOT weave it. Put it in Skills.

This removes the naturalness problem at the source and matches the effort to the actual goal
(ATS keyword presence), not to a prose nicety.

DEFAULT TO SKILLS. The prose rewrite helper's judgment of "clean" is unreliable (it produced
"vendor partner, cost, and timeline" and a dangling "and implementation project", both of
which passed its checks). So do not let it decide prose-vs-Skills on a coin flip. Weave a term
into a sentence ONLY when it slots in without changing the sentence's grammar (essentially a
synonym swap for a word already present). Any doubt -> Skills. All six landing cleanly in the
Skills list is a better outcome than four jammed into prose; for ATS they score identically
and Skills never reads as stuffing.

## Changes (keep it small)
1. KEEP the render-boundary placement fix, core-promotion gating, and page-safe Skills
   append already in commit 0126079. Discard the uncommitted naturalness-assertion thrash on
   top of it.
2. REMOVE every build-stopping "naturalness" / "must land in summary or bullet" assertion for
   the priority terms. No subjective-quality assertion may abort a build. Ever.
3. Change the placement default: ledger terms land in the appropriate Skills group as clean
   list items (e.g. add "Project Management", "SaaS", "Vendor Management",
   "Implementation Delivery", "AI Pilots", "Global Program Coordination" to the relevant
   Skills groups, truthfully). Weave a term into a bullet/summary ONLY when there is a clean,
   grammatical home; otherwise Skills is the intended destination, not a fallback.
4. Keep the placement diagnostics (term -> bullet | summary | skills | missing, with the
   landing line printed) as a REPORT for human review. It informs; it does not gate.

## Objective machine gate for Checkpoint 1 (this is all the build enforces)
- Each of the six terms is PRESENT in the resume (bullet, summary, OR Skills, all equal):
  Blue Yonder: project management, implementation project, saas.
  Adobe: global program, vendor partner, ai pilot.
- Both priority resumes build resume PASS + cover PASS.
- Core coverage recovered (promoted term counted only when placed anywhere; never a
  required-and-missing drop).
That is the entire hard gate. If it passes, STOP and hand off to human review. Do not
self-tune prose quality in a loop.

## Human review (not a build assertion)
- Print the six landing sentences to the rebuild folder. A human (Claude's scheduled check
  plus Christian) reads them. If a prose landing is awkward, the fix is trivial and targeted:
  move that one term to Skills. It is never a reason to abort or re-derive the build.

## Process rules to prevent another 4-hour loop
- Circuit breaker: if the objective gate above fails after AT MOST 2 build attempts, STOP and
  write a short note listing the exact failing terms and candidate sentences for human
  decision. Do not continue autonomously.
- Fast inner loop: during iteration run only the focused ledger tests. Run the full
  smoke/validate/source-lint suite ONCE before the single commit, not after every tweak.
- One commit: fold the recovery into one focused commit; do not amend-and-full-rebuild
  repeatedly.
- Do not encode any subjective quality bar (naturalness, tone, "reads well") as a
  build-stopping assertion. Objective gates only: presence, PASS/FAIL status, coverage math,
  banned-phrase scan, PDF scan.

## Phase A then Phase B (unchanged structure, now with a satisfiable gate)
- Phase A: build ONLY the two priority workflows. Apply the objective gate. If it passes,
  print landings and hand off. Expected result given the reframe: all six present (some in
  Skills), both PASS. This should take one or two builds, not ten.
- Phase B: after human OK on Phase A, rebuild the remaining 18 in batches of five; finish each
  batch; stop between batches only on the old regression signature (promoted term missing +
  core drop).

## Guardrails
- Truthful only: every ledger term traces to an evidence anchor; Skills entries are real
  skills. No invented content. Weak fits stay honestly FAIL/BRIDGE.
- Word-only, no PDFs. Active jobs/ restored byte-for-byte. Do not stage generated outputs,
  scratch folders, active jobs files, or spec docs.
- Federal remains queued until this verifies.
