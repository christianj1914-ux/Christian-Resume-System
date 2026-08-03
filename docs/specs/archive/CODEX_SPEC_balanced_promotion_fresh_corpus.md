# Fresh-Corpus Balanced-Promotion Measurement and Decision (phased)

Status: historical planning record, superseded by
`CODEX_SPEC_survivor_placement_and_promotion.md`. The final authoritative 35-build measurement passed
with zero supported-core disruption, and the conditionally pre-approved balanced promotion was
implemented.

## Implemented result
- Authoritative batch: `scratch/fresh_keyword_corpus_exact_surface_final_20260731_0735/`
- Production fingerprint: `fcec9dcb4cbd3c9c8c1ba0ddd17686d16585c419f363d9626796fa174f3c8d84`
- Isolation and completeness: 35/35 successful, 35/35 exactly two pages, packaged audits passed,
  active job inputs and `output/` inventory byte-identical.
- Safety: PASS; zero false/non-requirement blockers, zero breadth-only blocking, and direct/workflow
  policy parity across every row.
- Disruption: 0/35 builds (0.0%). Exact-surface placement closed Fisher Phillips
  `operational transformation`, Pragmatike `project management`, and Delta `digital transformation`.
- The original four were resolved: Amplify counterpart context, Direct Travel exact placement,
  Stord domain alternative family, and HD Supply unsupported domain gap.
- Decision: Option A. The objective clean gate passed and the conditionally pre-approved promotion
  set the centralized default to balanced. Advisory and exhaustive remain explicit overrides; the
  archived figure of 47 and earlier disruption measurements are historical only.
- Phase 6 system-wide quality work moved the Aptean fixture to Fit PASS, 100% core coverage, zero
  balanced blockers, and exactly two pages while retaining apparel/fashion/textile as a genuine
  unsupported domain family. No automatic ownership-lift infrastructure was needed.

This specification reconciles the original fresh-corpus proposal, harness-isolation findings, and
the promote-versus-recommend decision. Measurement, the production default change, and conditional
placement remain separate.

## Why
The combined upgrade kept advisory as the default because "47 genuine supported core misses remain in
historical builds." That figure was measured against archived output DOCX files, not resumes rebuilt
by the finished pipeline. Same-JD proof of the discrepancy: `keyword_reliability_recent_after.csv`
Aptean row (archived 16:59 output) is 79% core with 10 supported-unwritten; the fresh Aptean rebuild
(01:29) is 100% core with 0 supported-unwritten. The 47 is a stale-output upper bound, and the
GoodShip rows still listing `process`/`configuration` as blockers confirm the CSV predates final
reconciliation. The promotion decision must be re-run on fresh builds.

## Validated implementation constraints (from Codex grounding)
1. Harness isolation. The existing harness `scratch/run_20_workflow_rebuild.py` is not isolated: it
   rewrites the active job files, generates into `output/`, then copies into a batch folder, and the
   corpus analyzer always resolves resumes from `output/`. A trustworthy rerun therefore requires a
   measurement harness that redirects the builder's job, output, scratch, and render paths before
   import, with one isolated output directory per fixture so duplicate targets (the two GoodShip
   snapshots) cannot overwrite or influence each other. Hard requirement of Phase 1.
2. Code freeze during measurement. Phases 1 through 3 measure a specific pipeline fingerprint. Any
   change to content generation (Phases 5 and 6) invalidates that fingerprint. Freeze production code
   for the duration of Phases 1 through 3; if content-generation behavior changes before Phase 4,
   re-run the full fresh-corpus safety measurement under the new fingerprint before promoting.
   Correcting an earlier note: Phase 6 cannot run concurrently with the measurement.
3. Centralized default switch. The default policy string "advisory" is currently duplicated across at
   least six sites (`build_resume.py` ~590, ~599, ~6677; `run_resume_workflow.py` ~515, ~561, ~569).
   Phase 4 must introduce a single `DEFAULT_KEYWORD_POLICY` constant that replaces those literals so
   the default is consumed from one place; otherwise a partial flip creates direct/workflow parity
   drift.

---

## Phase 1 - Isolated rebuild harness (measurement only)
- Extend the rebuild harness to support `recent` and `legacy20` fixture sets, resume-only execution,
  resumable per-fixture runs, bounded parallelism, and an explicit batch directory.
- Patch the builder's job, output, scratch, and render paths before import so no active file is
  touched. Give each fixture, including duplicate targets, its own isolated output directory.
- Hash the active job files and the `output/` inventory before and after the batch; fail closed if any
  active deliverable or input changes byte-for-byte.
- Build under advisory so every resume is produced, then recompute advisory, balanced, and exhaustive
  readiness from the same packaged DOCX.
- Emit a batch manifest per fixture: fixture id, build timestamp, pipeline fingerprint, source-lane
  selection, exit state, DOCX path, notes path, page count.
- Exit gate: all 35 fixtures build or are recorded as failed; active deliverables and job files are
  provably unchanged.

## Phase 2 - Fresh-manifest analyzer and metrics (measurement only)
- Extend the corpus analyzer with a fresh-manifest input mode. In this mode it must use the manifest's
  exact DOCX path and never search `output/` or fall back to a source resume.
- Preserve existing CSV fields and add: `population=fresh_rebuild`; build timestamp and pipeline
  fingerprint; supported core and supported breadth misses recorded separately; validating requirement
  text and catalog concept per blocker; placement-plan membership and final landing; blocker
  disposition (`planned_but_unwritten`, `supported_not_planned`, `unsupported_not_blocking`);
  direct/workflow gating parity.
- Regenerate fresh recent and legacy CSVs plus a combined summary. Retain the archived CSVs clearly
  labeled as historical baselines, and correct the corpus summary, progress CSV, and combined spec so
  the archived "47" is explicitly identified as a stale-output upper bound.
- Exit gate: every fresh row is complete and bound unambiguously to its JD via the manifest.

## Phase 3 - Decision and Claude review packet (measurement only; no production change)
Split the eligibility test into two distinct questions, because "zero supported core blockers across
all 35" conflates safety with tailoring completeness:

- Safety (is balanced correct to run at all): false or non-requirement core blockers are zero; no
  breadth-only blocker; no malformed-term INCOMPLETE; direct and workflow policy outcomes are
  identical; packaged-document audits pass; every build is exactly two pages. Balanced is only ever
  eligible when all of these hold.
- Genuine-blocker rate (a user experience judgment, not a correctness bug): the count of fresh builds
  that balanced would stop on a genuinely supported, genuinely unwritten core requirement. Balanced
  blocking these is the feature working as intended, not a false positive. This number informs how
  disruptive balanced-as-default would feel, but it does not by itself make balanced unsafe.

Inconclusive handling: missing builds, non-two-page outputs, pipeline-fingerprint drift,
packaged-audit mismatches, or incomplete rows make the result inconclusive; advisory stays unchanged.

Produce a Claude decision document presenting both options with fresh evidence:
- Option A, promote balanced: safety criteria all pass. List the exact default, help, and
  documentation changes and the required parity regression run. Note the genuine-blocker rate so the
  user can weigh disruption.
- Option B, keep advisory: safety criteria fail, or the genuine-blocker rate is high enough that the
  user prefers advisory. List surviving blockers grouped by fixture, term, evidence concept,
  requirement text, placement-plan status, and landing failure.

Claude recommends one option from the fresh evidence. Production defaults remain unchanged until the
recommendation is explicitly approved. Placement logic is not modified in this phase.

## Phase 4 - Promote balanced to default (production change; separate approval required)
Runs only if Phase 3 recommends Option A and the user approves. This is the one production behavior
change and is deliberately isolated from measurement.
- Flip the default policy from advisory to balanced through the single `DEFAULT_KEYWORD_POLICY`
  constant (see constraint 3), which must already have replaced the six duplicated literals; keep
  advisory and exhaustive selectable.
- Re-run the direct-builder and workflow-runner parity regression under the new default.
- Update command help, `SYSTEM_REFERENCE.md`, `ARCHITECTURE_MAP.md`, and the review bundle to state
  balanced as the default and advisory as an explicit override.
- Exit gate: parity holds under the new default; the switch is confirmed reversible in one step.

## Phase 5 - Targeted placement pass for genuine survivors (conditional)
Runs only if Phase 3 finds genuine supported-core blockers (`supported_not_planned` or
`planned_but_unwritten`) that the user wants closed rather than left as review flags.

Survivor triage first (required before any placement change). The 2026-07-30 fresh run left four
survivors, and two carry `concept: none` (Stord `robotics integration`, HD Supply `customer
integration`), which is contradictory for a supposedly supported blocker. Classify each survivor into
one of three buckets and act accordingly, do not treat all four as plain placement gaps:
- Supported and landable, with a catalog concept (Amplify `product owner` -> `product_ownership`;
  Direct Travel `cross functional` -> `cross_functional_delivery`): real placement target below. Also
  confirm the term genuinely belongs in core rather than breadth (verify `cross functional` is not a
  generic competency that Increment 2 should route to breadth).
- Supported but no catalog concept yet (candidate: Stord `robotics integration` if the Amazon Robotics
  launch evidence covers it): add the catalog concept and its permitted surfaces first, then place.
- Genuinely unsupported (candidate: HD Supply `customer integration` if no approved evidence supports
  it): reclassify so it never blocks balanced, exactly as Aptean apparel does. Removing false blockers
  here also lowers the measured disruption rate.
- For each remaining supported survivor, trace whether the placement plan omitted the concept or
  planned it but failed to land it, using the disposition field from Phase 2.
- Fix the specific placement or planning gap under the existing rewrite-safety and provenance gates
  from the prior increments. No new invented content.
- Re-run Phases 1 through 3 on the affected fixtures and confirm the survivor set shrinks without new
  regressions.

## Phase 6 - Independent top-third quality follow-ups (separate from the policy decision)
The Aptean Fit FAIL is no longer keyword or ownership related; the current notes show three separate
quality findings that are worth their own pass and are independent of the balanced decision:
- "Top-third skim does not clearly echo the role's core business problem."
- Early-placement gaps: role-identity and requirement terms (for example `erp consultant`,
  `requirements gathering`) not visible in the summary or first bullets.
- Skills relevance warning: weak-signal Skills items diluting the section.

Scope, honesty-bounded and system-wide (Aptean is a fixture only):
- Improve the summary/first-role opening so it names the role's core business problem when the
  evidence supports it, reusing the existing provenance and writing-quality gates. Do not invent a
  problem framing the evidence does not support.
- Promote genuinely supported role-identity and requirement surfaces into the summary or first bullets
  through the existing placement engine rather than leaving them only in Skills, subject to the
  two-literal-per-bullet cap and prose checks.
- Apply the Skills relevance/redundancy/density diagnostics already shipped so weak-signal items are
  pruned or down-ranked, protecting source skills and sole coverage carriers.
- Gate any rewrite on provenance, ownership ceilings, two-page fit, and writing quality. Where a
  finding cannot be resolved truthfully, leave it and let Fit remain FAIL for that stated reason.

Sequencing: Phase 6 changes generated content, so it must not run during the Phases 1 through 3
measurement window (it would move the pipeline fingerprint), and it must not run concurrently with
Phase 5 since both touch placement and top-third behavior. If Phase 5 or 6 changes content before a
balanced promotion, re-run the fresh-corpus safety measurement under the new fingerprint first.

---

## Tests
- Fresh-manifest mode never resolves from active `output/`; fails closed on missing or duplicate
  fixture artifacts; keeps duplicate target snapshots independent.
- Supported core and supported breadth misses are separated; blocker provenance and placement
  disposition are recorded.
- Active job files and deliverables are byte-for-byte unchanged after a batch.
- Phase 4 default flip is reversible in one step and preserves direct/workflow parity.
- Phase 6 rewrites pass provenance, ownership-ceiling, two-page, and writing-quality gates and never
  invent content.
- Run source lint, 440+ validation checks, both fresh corpora, policy parity checks, manifest
  integrity checks, and representative render inspection.

## Assumptions and guardrails
- Phases 1 through 3 and Phase 6 are measurement or honesty-bounded quality work; only Phase 4 changes
  production policy, and only on explicit approval.
- The canonical populations remain the analyzer's current recent-15 and legacy-20 fixture lists, each
  evaluated independently with no stale same-company output influencing generation.
- Advisory, balanced, and exhaustive differ only in gating; advisory-built content is valid for all
  three readiness evaluations.
- Unsupported evidence or domain gaps never count as balanced blockers.
- Exact ATS matching stays strict; source resumes gain no keyword variants or ownership rewrites;
  titles, role order, company context, reorganization sentences, Education, Professional Development,
  formatting, two-page length, and Word-only output are unchanged.
