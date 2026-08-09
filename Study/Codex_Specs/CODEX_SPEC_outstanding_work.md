# CODEX SPEC: Outstanding Work

Date: 2026-08-08
Author: Claude (review and plan pass)
Branch: `codex-cleanup-and-decoupling`, HEAD `6d33a60`
Predecessors: `CODEX_SPEC_system_audit_bugs_and_redundancy.md`, `CODEX_SPEC_worktree_cleanup_and_decoupling.md`

Independent verification of the completed cleanup work, one defect it introduced, and the remaining work in dependency order.

---

# Part 1: Verification of completed work

Checked independently against HEAD `6d33a60`, not taken from the completion report.

| Claim | Result |
|---|---|
| Four new commits present | Confirmed: `9f3a04f`, `2b08592`, `dfa3c87`, `6d33a60` |
| PDFs removed from `output/` | Confirmed: 60 to **0** |
| `output/` reduced | Confirmed: 523 to **431** entries, 323 to **287** `.docx` |
| Federal import isolation | Confirmed: `build_federal_resume` imports neither builder in a clean interpreter (270 modules loaded, zero leaked) |
| Qualifications uses neutral module | Confirmed: imports `interview_story_engine` directly at line 21 |
| Neutral module imports no builder | Confirmed |
| Archive lane invariant | Confirmed: 475 records, **0** empty lanes |
| P0 crash fixes intact | Confirmed: both original reproductions pass; `remove_global_low_fit_bullets` signature correct |
| Vulture unreachable / unsatisfiable | Confirmed: **0** |
| `ast.parse()` across `scripts/` | Confirmed: **0** failures |

The high-risk stages landed correctly. Output pruning, federal isolation, and the archive repair all hold under independent check.

---

# Part 2: Defect introduced by `dfa3c87`

## The extraction copied instead of moved

**Severity: P1.** No wrong output today. High probability of silent wrong edits going forward.

`scripts/build_interview_cheat_sheet.py` ends at line 6451 with a compatibility re-export:

```python
# Compatibility re-exports: shared story selection and spoken-answer logic now live in
# the neutral module so qualifications and federal workflows do not import this builder.
from interview_story_engine import (  # noqa: E402
    InterviewQuestion, StoryCard, adjusted_profile_for_role, assert_full_spoken_answer,
    closest_anchor_story_title, contains_all, expanded_story_bank, likely_question_story,
    should_use_cart, signal_score, spoken_caar_answer, spoken_cart_answer,
    spoken_pyramid_answer, spoken_story_answer, story_by_boost_key, story_for_type,
    supported_story_bank, uses_star_answer_framework,
)
```

**All 18 of those symbols are still defined earlier in the same file.** The re-export shadows them.

Measured:

- **18 of 18** symbols defined in both `build_interview_cheat_sheet.py` and `interview_story_engine.py`
- **545 duplicated lines** remaining in the cheat sheet
- **8 pairs have already textually diverged**
- **18 new pyflakes redefinition warnings**, none of which existed at `97b45ea`

Divergent pairs: `adjusted_profile_for_role`, `should_use_cart`, `spoken_caar_answer`, `spoken_cart_answer`, `spoken_pyramid_answer`, `spoken_story_answer`, `story_for_type`, `uses_star_answer_framework`.

## Why the byte-identical gate passed

The divergences are annotation-only. Example, `story_for_type`:

```diff
-    profile: build_resume.JobProblemProfile | None = None,
+    profile: resume_analysis.JobProblemProfile | None = None,
```

That is a correct and necessary adaptation, since the neutral module cannot import `build_resume`. Because the module-level re-export at line 6451 executes at import time, the engine versions win everywhere, so both the cheat sheet and the qualifications statement call the same code and the regenerated documents matched byte-for-byte. **The gate tested output, not structure. It could not have caught this.**

## Why it matters

The 545 dead lines look authoritative. Anyone editing `expanded_story_bank` at `build_interview_cheat_sheet.py:2950` will change nothing at all, because line 6451 rebinds the name. That is the same failure shape as the two defects this engagement already found: the runaway archive that looked like progress, and the blanked lane that looked like data. An edit that appears to work and silently does nothing.

It also means the refactor did not achieve its stated purpose. The cheat sheet was 6,062 lines at `97b45ea` and is 6,482 now. A move would have shrunk it by roughly 545.

## Fix

Delete the 18 original definitions from `build_interview_cheat_sheet.py`, keeping only the re-export block.

**Verified safe.** AST analysis confirms **no module-level statement before line 6451 references any of the 18 names**, so nothing resolves to an original definition at import time. Every call site already reaches the engine version through the rebinding.

Procedure:

1. Capture visible-text and SHA-256 baselines for the cheat sheet, detailed guide, and qualifications statement from the active job, exactly as `dfa3c87` did.
2. Delete each of the 18 original definitions. Keep the re-export.
3. Where a deleted definition and its engine counterpart diverged, confirm the engine version is the intended one. For all eight current divergences it is: the annotation change is required by the neutral module.
4. Regenerate all three documents. Require byte-identical visible text against the step 1 baselines.
5. Confirm `python -m pyflakes scripts/build_interview_cheat_sheet.py` reports **zero** redefinitions, down from 18.
6. Confirm the cheat sheet is roughly 545 lines shorter.

Commit: `refactor: complete story engine extraction by removing duplicated definitions`

Acceptance: `python tasks.py validate` at 492 or higher, zero pyflakes redefinitions, byte-identical documents.

## Guard against recurrence

The Stage 3 acceptance criterion was "zero undefined names and zero redefinitions." It regressed to 18 and nothing caught it, because the suite does not gate on static analysis.

Add a smoke check that runs pyflakes across `scripts/` and fails on any undefined name or redefinition. It belongs in the suite rather than in a human checklist, because a checklist run at the end of a nine-stage sequence is exactly where this slipped through.

---

# Part 3: Repository closeout

Documentation only. No behavior change.

1. **Update `CODEX_NEXT_WORK_post_remediation.md`.** It currently records 475/475 in 6m58s on August 3. Replace with the current baseline: 492/492, the completed story-engine extraction and federal isolation guard, and the output-cleanup results. Retain the three genuinely deferred items already documented there: `contains_search_term` semantics, `program_delivery` federal cluster mapping, and validation performance.

2. **Add a `CHANGELOG.md` closeout entry** covering both passes: the 16 audit findings, the archive lane repair across 475 records, source and encoding hygiene, output cleanup, the story-engine extraction, and federal isolation. Record two facts a future reader will otherwise have to rediscover:
   - `f66729c` is a validated but deliberately non-bisectable integrated baseline
   - removing the duplicate cover-letter `fail()` changed test-visible diagnostics, and tests now assert stderr rather than `SystemExit` text

3. **Relocate remaining completed root records** to `Study/Codex_Specs/`: `ATS_HEADING_REVIEW.md`, `CLAUDE_PLAN_keyword_tailoring_reliability.md`, and the three audit and cleanup specifications once their work is complete. Update every live reference. `QUEUED_WORK_PLAN.md` stays at root while its items remain open.

4. **Add narrow `.gitignore` entries** for `Game Guides/` and `Hispanic_Heritage_Passport_Project/`. Both are unrelated personal material and neither should be able to enter a system commit or a Claude review bundle. This mirrors the existing `personal/` treatment.

5. **Preserve all cleanup archives and manifests** under `scratch/cleanup_archives/`. They are the recovery path for the 96 deleted output files.

6. **Re-run the deterministic ten-snapshot lane comparison last**, after every behavior change including the Part 2 fix. Require each stored lane to equal current `job_problem_profile()` output. Non-empty is insufficient. Record snapshot IDs and per-snapshot results.

Commit: `docs: close out audit and cleanup passes`

---

# Part 4: Document-quality work

Three items, in dependency order. Each is its own commit. Sourced from `QUEUED_WORK_PLAN.md` and `Study/Codex_Specs/CODEX_PACKET_prose_nested_list.md`; read both before starting, since this specification has not independently re-derived their scope.

Sequence matters: nested-list repair is shared machinery that summary and cover-letter work both reuse. Doing it first means the later two inherit a working repair rather than each patching around it.

## 4.1 Nested-list repair convergence

- Reproduce the three known non-converging cases: East West decision language, solution-architecture language, documentation and training language.
- Make the repair's activation threshold match the detector's actual condition rather than the narrower legacy "four ands" rule. The mismatch is the reason repair does not converge.
- Require idempotence and convergence within the configured repair-pass limit.
- Preserve factual wording, outcome, scope, metric, employer, and role. This is a prose repair, not a content rewrite.
- Keep the existing East West content stopgap until it is demonstrably redundant. Do not remove it merely because the general repair now passes that case.

Commit: `fix: converge nested list prose repair`

## 4.2 Summary quality

- Leave the 45 to 70 word contract unchanged. `.context/RULES_FOR_CLAUDE.md` and `CODEX_NEXT_WORK_post_remediation.md` both record it as resolved.
- Add a summary-quality audit measuring word count, sentence length, repeated preposition pileups, and proof-anchor retention.
- **Run the audit in reporting mode first** against one archived posting per supported lane. Record counts and warnings before changing any composition behavior. The archive now has correct lanes across all 475 records, so lane-representative sampling is finally reliable.
- Repair only the composition joins producing duplicated context, double-preposition phrasing, or overlong opening sentences. Reuse the 4.1 repair where it applies.
- Add lane-level golden tests for compliant length, preserved supported proof, and absence of prohibited patterns.
- Promote checks from warning to failure only after the sampled corpus is clean.

Commit: `fix: tighten professional summary composition`

## 4.3 Cover-letter quality

- Add warning-mode checks for internal lane tokens, body-paragraph count, distinct proof usage, company reference, and honest BRIDGE and FAIL language.
- Audit representative archived postings, including Randstad, before changing composition.
- Require two or three substantive body paragraphs with distinct supported proof. Use source-backed fallback proof when selection under-fills rather than repeating a bullet.
- Replace internal lane labels with job-description nouns. Use approved company context where available and a truthful fallback where research is unavailable.
- Add golden tests for a coherent opener, distinct proof paragraphs, no internal tokens, company specificity, and non-inflated bridge language.

Commit: `fix: strengthen cover letter proof and specificity`

---

# Part 5: Deferred, with entry conditions

Each stays deferred until its stated condition is met. None should be picked up opportunistically.

**`contains_search_term` consolidation.** Two implementations differ in opposite plural directions. Consolidation can shift alignment scores, gap suppression, bullet selection, and competency selection simultaneously. Entry condition: decide the intended semantics first (singular-to-plural, plural-to-singular, or bidirectional), then run `keyword_reliability_corpus.py` before and after and review the score, gap, bullet, and competency diffs.

**`program_delivery` federal cluster mapping.** Absent from `FEDERAL_DEFAULT_CLUSTERS_BY_LANE`; the active federal fixture depends on the current fallback tie-break. Entry condition: a deliberate before-and-after cluster comparison with intentional fixture re-pinning. Worth noting that `program_delivery` is a live commercial lane with 33 archived postings, so the federal gap is a real asymmetry rather than a dead branch.

**Validation performance.** The suite takes roughly 7 minutes. Entry condition: profile per-check timing and establish a clean local baseline before optimizing. The previously identified contributors are the orphan-function scan, Claude packet self-audits, and the Claude bundle refresh. Measure with `PYTHONPYCACHEPREFIX` on local disk; bytecode writes on a slow filesystem will otherwise dominate and produce a meaningless profile.

**Randstad "core training" weave.** Do not add without explicit source confirmation from the owner. Unconfirmed additions to evidence are exactly what the source-truth rules exist to prevent.

---

# Part 6: Global rules

- One commit per slice. Everything after `f66729c` stays independently revertible.
- `python tasks.py validate` after every commit, full suite, never below **492**.
- Run pyflakes, vulture, and the AST parse gate after any source-hygiene-adjacent change, and after Part 2 in particular.
- Stop rather than rebaseline on: a lane mismatch, story-text drift, a family-parser guard failure, a validation count drop, or any new pyflakes redefinition.

## Recommended order

1. **Part 2** first. It is a live correctness hazard and the fix is verified safe.
2. **Part 3** closeout, so the repository reaches a clean documented state.
3. **Part 4** in the stated order, since 4.1 is shared machinery for 4.2 and 4.3.
4. **Part 5** only when an entry condition is genuinely met.
