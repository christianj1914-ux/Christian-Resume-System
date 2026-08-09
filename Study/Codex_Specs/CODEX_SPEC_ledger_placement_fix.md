# Codex Spec: Fix Ledger Placement (corrective pass)

## Context
The prior pass (commits fbd903e..3f5c54d) landed the denominator hygiene correctly but the
evidence ledger did NOT place any truthful terms, and the core-promotion regressed coverage.
Verified facts:
- `source/evidence_terms.py` loads (24 entries); terms are found in the JDs;
  `jd_preferred_surface` returns the correct literal strings ("SaaS", "project management").
  So recognition and surface-mapping WORK.
- The two priority resumes contain NONE of their six ledger target terms:
  Blue Yonder missing `project management`, `implementation project`, `saas`;
  Adobe missing `global program`, `vendor partner`, `ai pilot`.
- Core coverage dropped on multiple roles because Fix 3 promoted `project management` and
  `professional services` into the must-have core set, but placement never wrote them, so
  they now count as required-and-missing (Blue Yonder PM core 100->80 missing exactly
  "project management"; Advyzon, Manhattan Enablement, Adobe Solutions similar). USAA flipped
  PASS->FAIL with rising coverage, consistent with a newly-required core term going missing.

Diagnosis: the ledger is wired into the coverage/mirror SURFACE but never into the document
WRITE path. And core-promotion must never count an unplaced term as required.

## Keep
- Commit 1 denominator hygiene (fbd903e) is correct. Keep it.
- The ledger data file and `jd_preferred_surface` are correct. Keep them.

## Fix 1 (the real bug): wire the ledger into the WRITE path
- When `keyword_placement_audit` / coverage finds a JD term that matches a ledger concept
  (strong, or moderate with context) and the resume lacks the literal form, the placement
  step must ACTUALLY WRITE that literal form into the document, using the existing
  non-forcing ladder:
  1. weave into the bullet carrying the ledger `anchor` evidence (natural, in-sentence),
  2. else another evidence-supported bullet or the summary,
  3. else add it to the Skills group (this is a legitimate final home, not a cap-blocked
     no-op).
- The prior "keep Skills flat at 23" behavior is likely why nothing landed: Skills placement
  became a no-op or a same-count swap that dropped the term. Correct rule: Skills MAY grow to
  hold a supported ledger term; the guard is against a keyword-dump, not against ever adding
  a term. If replacing a weak Skills item, the replaced item must not itself be covering a
  JD term (do not rob Peter to pay Paul).
- Instrument: after build, assert each ledger term that was supposed to place is present via
  `contains_search_term`. If a term the audit demanded did not land anywhere, that is a hard
  build warning, not a silent miss.

## Fix 2: gate core-promotion on actual placement
- A promoted core term (`project management`, `professional services`) may be counted as a
  required core term ONLY if it is actually present in the final document. Never count a
  promoted-but-unplaced term as required-and-missing.
- Simplest correct implementation: run placement first, then compute core over terms that are
  either genuinely central OR successfully placed. If a promoted term truly cannot be placed
  for a given role, it is not required for that role.
- Effect: core coverage stops dropping for a term the system itself failed to write.

## Build order and incremental checkpoints (do NOT run all 20 blind)
The last pass wasted a full 20-run because a broken placement path was only discovered at the
end. Build in gated phases and stop at the first failed checkpoint.

- Phase A (fast, minutes): after the two code fixes, build ONLY the two priority resume
  workflows: `16_Blue_Yonder_-_Program_Manager` and `19_Adobe_-_Senior_Program_Manager_GSO`
  (resume + cover + qualifications each). Restore active jobs/ files after each swap.
- CHECKPOINT 1 (hard gate): assert the six target terms are present in the two resumes
  (Blue Yonder: project management, implementation project, saas; Adobe: global program,
  vendor partner, ai pilot), each traced to a ledger anchor; core coverage recovered to its
  pre-pass level; both remain resume PASS + cover PASS. NATURALNESS: because placement was
  inert until now, the natural-fit guards (same-stem, evidence-fit, no-identity-injection)
  have never run on a real insertion. Each of the six placed terms must read as natural
  prose in its bullet/summary, not a jammed or redundant insertion (no "delivered technical
  delivery", no identity-line injection, no term bolted onto a mismatched bullet). Print the
  sentence each term landed in so it can be eyeballed. If ANY of these fail, STOP, fix, and
  rebuild only the two priorities again. Do not touch the other 18 until Checkpoint 1 passes.
- Phase B: only after Checkpoint 1 passes, rebuild the remaining 18 in batches of 5. After
  EACH batch, record core/breadth before/after and scan for known-bad phrases and PDFs.
- CHECKPOINT 2..n (per batch): if a batch shows a core regression driven by a promoted-but-
  unplaced term (the prior bug's signature), STOP and fix before continuing. Do not push
  through a batch that reproduces the regression.
- Write each phase's results to the rebuild folder as they complete (per-target visible-text
  extracts + a running summary.csv), so an external check can read progress mid-run rather
  than only at the end.

## Acceptance (must verify, not assert)
- The two priority resumes contain their six target terms:
  Blue Yonder: `project management`, `implementation project`, `saas`.
  Adobe Sr PM: `global program`, `vendor partner`, `ai pilot`.
  Each placed naturally (prefer a real bullet; Skills only if no bullet fits), each tracing
  to its ledger anchor.
- Breadth rises because terms were PLACED, not only because the denominator shrank. Report,
  per priority role, how many of the newly-present terms came from a bullet vs Skills.
- Core coverage on Blue Yonder PM, Advyzon, Manhattan Enablement returns to >= its pre-pass
  level (no promotion-without-placement drop). USAA returns to PASS unless it has a genuine,
  separately-explained evidence blocker (state which).
- Priority roles remain resume PASS + cover PASS.
- Re-run all 20; report before/after core and breadth, and for every remaining miss say
  whether it is: placed now, genuine domain gap, or noise removed.
- No invented content: every placed term traces to a ledger anchor. No known-bad phrases.
  Word-only. Do not stage generated outputs, active jobs/ files, or spec docs.

## Guardrails
- Exact matching preserved. Non-forcing, same-stem, evidence-fit, no-identity-injection
  guards still win: if a term genuinely has no truthful home, it stays missing rather than
  being forced or faked.
- Weak fits stay honestly FAIL/BRIDGE. The ledger fixes phrasing of terms Christian owns; it
  never manufactures a domain he lacks.
- Federal remains queued after this lands and verifies.
