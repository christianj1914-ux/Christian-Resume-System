# CODEX SPEC: Integration and Deferred Work

Date: 2026-08-08
Author: Claude (review and plan pass)
Branch: `codex-cleanup-and-decoupling`, HEAD `be2d736`
Predecessors: `Study/Codex_Specs/CODEX_SPEC_system_audit_bugs_and_redundancy.md`, `CODEX_SPEC_worktree_cleanup_and_decoupling.md`, `CODEX_SPEC_outstanding_work.md`

All planned implementation work is complete and verified. Suite at 493/493, working tree clean, static gates clean.

**One genuinely outstanding item remains, and it has not appeared in any prior plan: none of this work is on `main`.** Everything else is deferred by choice.

---

# Part 1: Integration (outstanding, do this)

## Measured state

| Relationship | Value |
|---|---|
| `codex-cleanup-and-decoupling` ahead of `main` | **77 commits** |
| `main` ahead of `codex-cleanup-and-decoupling` | **0 commits** |
| `main` ahead of `origin/main` | **15 commits** |
| `origin/main` ahead of `main` | **0 commits** |
| Merge base of `main` and HEAD | `42faaa2`, which is `main`'s tip |
| Working tree | clean, 0 entries |
| `codex-systemwide-docfixes` contained in HEAD | **yes**, verified ancestor |

`main` is at `42faaa2` ("Polish fit gating and cover specificity"). Because the merge base equals `main`'s tip and `main` has zero commits HEAD lacks, **this is a clean fast-forward with no conflict risk anywhere in the chain.**

Total integration debt: `origin/main` is **92 commits behind** the validated work (15 already on local `main`, plus 77 on the feature branch).

## Why this matters

Eighteen of those 77 commits are this engagement: three P0 crash fixes, the archive lane repair across 475 records, source and encoding hygiene, the output cleanup, the story-engine extraction, and the federal isolation guard. Until they reach `main`, the branch is the only copy, and any future work started from `main` silently reintroduces every bug that was fixed.

The two crash fixes matter most here. `remove_global_low_fit_bullets` and `merge_low_fit_bullets_before_delete` raise `NameError` on `main` today for any job description whose bullets trip their patterns.

## Procedure

1. Confirm the working tree is clean and the suite passes at 493 on `codex-cleanup-and-decoupling`.
2. `git checkout main`
3. `git merge --ff-only codex-cleanup-and-decoupling`

   Use `--ff-only` deliberately. If it refuses, the assumption above no longer holds, and that is worth understanding before forcing anything.
4. Run `python tasks.py validate` on `main`. Require 493.
5. Run one real end-to-end build on `main`: `python tasks.py resume` against the active job description, then confirm the output opens, fits two pages, and carries no Carlito leakage.
6. `git push origin main`
7. Delete the merged branches once `origin/main` reflects the work:
   - `git branch -d codex-systemwide-docfixes` (verified ancestor, fully contained)
   - `git branch -d codex-cleanup-and-decoupling`

   Use `-d` rather than `-D`. If git objects, the branch is not actually merged and that needs investigating.

Acceptance: `origin/main` at `be2d736` or later, 493 passing on `main`, one clean end-to-end build, both feature branches deleted.

Do not squash. The commit history is the audit trail for two remediation passes, and `f66729c` is already documented as the one intentionally integrated commit.

---

# Part 2: Deferred work, with entry conditions and a recommendation

None of these should be picked up opportunistically. Each has a condition that makes it worth doing, and until that condition is met the correct action is to leave it alone.

## 2.1 `contains_search_term` consolidation

**Recommendation: stay deferred. Highest priority of the four if a symptom appears.**

Two implementations differ in opposite plural directions: one expands singular to plural, the other reduces plural to singular. Consolidating changes alignment scores, gap suppression, bullet selection, and competency selection **simultaneously**, which is why no incremental version of this change exists.

Entry condition, in order:

1. Decide the intended semantics explicitly: singular-to-plural, plural-to-singular, or bidirectional. This is a product decision, not a refactor.
2. Run `keyword_reliability_corpus.py` against the archived corpus before the change and capture the baseline.
3. Make the change.
4. Re-run and diff four things separately: alignment scores, suppressed gaps, selected bullets, selected competencies.
5. Accept only if every diff is explainable in terms of the chosen semantics.

Symptom that should trigger it: a resume where an obviously relevant job-description term is reported as a gap despite matching source evidence, or the reverse. That is the observable form of the two implementations disagreeing.

## 2.2 Federal `program_delivery` cluster mapping

**Recommendation: stay deferred. Trigger is a specific event, not a date.**

`program_delivery` is absent from `FEDERAL_DEFAULT_CLUSTERS_BY_LANE`. The active federal fixture depends on the current fallback tie-break, so adding the mapping shifts fixture output.

This is a real asymmetry rather than a dead branch: `program_delivery` is a live commercial lane with **33 archived postings**, second only to `implementation_delivery`. So the lane matters; it simply has no federal counterpart yet.

Entry condition: the next federal application in a program delivery lane. At that point, run a before-and-after cluster comparison, add the mapping, and re-pin the fixture deliberately. Doing it earlier means re-pinning a fixture against a hypothetical posting.

## 2.3 Validation performance

**Recommendation: stay deferred, and be slow to act on it.**

The suite runs 493 checks in roughly 6m16s. Previously identified contributors are the orphan-function scan, the Claude packet self-audits, and the Claude bundle refresh.

Entry condition: profile per-check timing and establish a clean local baseline before changing anything. Measure with `PYTHONPYCACHEPREFIX` on local disk, because bytecode writes on a slow or networked filesystem dominate and produce a meaningless profile. That effect is what made an early audit reading of "30 second imports" an environment artifact rather than a finding.

The caution: this suite is the thing that has caught regressions throughout two remediation passes, and optimizing test infrastructure is a well-known way to quietly lose coverage. Six minutes is a reasonable price. Only act if the runtime is actually changing behavior, such as discouraging a full run before commits.

## 2.4 Randstad "core training" weave

**Recommendation: this is not deferred work. It is an open question for the owner, and it should be closed rather than carried.**

The item is blocked on explicit source confirmation that the training language is supported by an approved source resume. There are two honest outcomes:

- Christian confirms the source supports it, at which point it becomes ordinary work with a normal evidence anchor.
- It is not supported, and the item is deleted permanently.

Carrying it indefinitely on a deferred list is the worst option, because an unresolved evidence question that stays visible tends to get resolved optimistically later. The source-truth rules exist to prevent exactly that.

---

# Part 3: Optional follow-ups, not currently planned

Recorded so they are not rediscovered as findings later. None is worth doing on its own.

**`output/` will refill.** Phase 6a fixed the tests that wrote debug artifacts into `output/`, but normal use adds bundles. The `--prune-bundles` machinery now exists with preview as the default. Running it periodically is a habit, not a task.

**`render_check*/` retention.** Seven-day retention exists in `cleanup_output.py`. It runs only when invoked.

**The `docx_visible_text` and `paragraph_texts` consolidation from the original audit's Finding 10** was completed for the readers in the live path. If a future script needs DOCX text, use the canonical helpers in `utils.py` rather than writing a sixth copy.

**Import time for `build_federal_resume`** was measured before and after isolation. If it is ever measured again, use a local `PYTHONPYCACHEPREFIX`.

---

# Part 4: Summary

Outstanding and worth doing now: **Part 1 only.** A fast-forward merge, a validation run, one end-to-end build, a push, and two branch deletions.

Everything in Part 2 is correctly deferred. Three of the four have entry conditions tied to observable events rather than dates, which is the right shape for work that is not urgent. The fourth, the Randstad weave, should be closed with a yes or no rather than carried.

The system is in a good state. The most valuable next action after merging is to use it for a real application and let genuine friction, rather than a backlog, decide what gets built next.
