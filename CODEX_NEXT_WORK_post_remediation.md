# Codex Next Work: Deferred Follow-Up

## Release B prerequisite baseline

The output-equivalence harness is frozen against Release A behavior SHA `a14fb43d58a8cc8f3817fd3ac7665fc913bb22f4`; its permanent planted-change certification is commit `210380f9eafeed18f5922cacdee9ab5d510a3203`. Two independent full captures produced 17/17 canonically identical fixtures with zero unexplained differences in 927.508 and 953.696 seconds using LibreOffice `7.6.5.2 38d5f62f85355c192ef5f1dd47c5c0c0c6d6598b` and Poppler `26.05.0`. The baseline covers all nine live commercial lanes, PASS/BRIDGE/FAIL/DRAFT states, federal standard/AI and grade paths, publication recovery, companion documents, readiness, archive refresh, tracker isolation, and the two-posting queue. No baseline archive posting triggered the canonical POOR detector, so POOR remains an explicit coverage gap.

Release B itself remains blocked. Release A has not yet completed the required real application cycle or one-week regression-free observation period, and no approval has been given for Phase B1 through B7.

## Release B entry criteria

These criteria preserve the failure that established each constraint. They are acceptance requirements, not architectural preferences.

### Phase B1: clock ownership

**Criterion.** No builder calls `datetime.now()` for a document-visible date. All such dates come from `RunContext.clock`.

**Origin.** On August 13, 2026, an equivalence comparison reported three companion fixtures as unexplained differences. The only change was the cover-letter date line, from `August 12, 2026` to `August 13, 2026`; no generated content differed. Because the baseline was captured on one calendar day and the candidate rebuilt on the next, the harness could otherwise pass only on its capture date, and equivalence CI would fail daily. Comparator normalization fixed the symptom. A clock owned by `RunContext` eliminates the category. This was the second wall-clock value to escape into a compared field, after trace timestamps.

### Phase B2: path ownership

**Criterion.** No module constructs a path by string concatenation or separator replacement. All paths originate from `WorkspacePaths` in one canonical form.

**Origin.** One capture emitted both `C:/dev/...` and `C://dev//...`. The doubled form defeated the canonicalizer's URL guard, which matched `://` before checking for a drive prefix, so queue paths escaped projection while other paths in the same record normalized correctly. Raw JSON had been normalized before parsing, turning escaped Windows `C:\\...` values into decoded `C://...` paths. A single canonical path source removes the ambiguity every downstream guard would otherwise have to tolerate.

### Decision gate status

| Condition | Status |
|---|---|
| Release A completed a real application cycle | **NOT MET.** Requires the owner. |
| One-week regression-free observation period | **NOT MET.** Begins after the real application cycle. |
| Release A SHA recorded as the architectural baseline | **MET.** `a14fb43d58a8cc8f3817fd3ac7665fc913bb22f4`. |
| Equivalence harness passes at that SHA | **MET.** Certified twice in Session 1 and twice in Session 2. |
| Explicit approval for Release B | **NOT MET.** No approval has been given. |

Session 4 may land and push the certified harness, wait for CI, and exercise the live Honeywell workflow. That live run does **not** by itself satisfy the real-application-cycle or observation-period conditions. Those conditions close only through normal use and an owner decision.

### Equivalence recertification history

The first full comparison on August 12, 2026 reported `companion_bridge.processes` as unexplained with no visible-text difference. Report schema v1 retained only the difference hash, so the original nested value could not be recovered. The result did not reproduce in two independent Release A process captures or a fresh baseline-versus-candidate capture. Report schema v2 now retains canonical nested before/after evidence, and certification requires two consecutive full green comparisons at one candidate SHA.

The same run exposed a category error in queue comparison: `pipeline_fingerprint` hashes the complete Python tree, so it identifies the candidate rather than behavior and necessarily changes when harness Python changes. Queue fingerprints and derived completion keys are now validated for internal consistency before being projected out of cross-version comparison; posting identity, decisions, states, blockers, artifacts, output, and exit behavior remain authoritative.

On August 13, 2026, comparison run `bc70b23b4b3a490089846686d5cab125` tested candidate `6475add50a3024fa6c60ff6646f176171a46c7e2` and exposed two additional projection gaps. The three companion fixtures retained the raw cover-letter build date, and the system fixture retained the transient queue run directory inside its artifact and log paths. Schema-v2 preserved the complete nested evidence, proving that neither was a behavior change. Projection v3 normalizes both categories symmetrically. The report was persisted before the invocation reached its external 30-minute ceiling; later recertification commands receive 45 minutes externally without changing repository renderer, workflow, or retry limits. The frozen companion hashes change under v3; the frozen system hash correctly remains stable because that record already stores its queue paths as `<WORKSPACE>/...`.

Format normalization is inherently reactive because it recognizes volatile forms after they surface. A frozen clock in Release B's `RunContext` is the preferred long-term design because it eliminates wall-clock variation at generation time. That future work is not authorized by this repair.

The first projection-v3 recertification run, `8347d7f6795641e887968f970f2e3dd7` at candidate `be020aca5078cdb788907a547b30fd22e1ca1305`, confirmed that build-date normalization worked but reported the system queue fixture as the sole unexplained difference: 16 identical, 0 allowed, 1 unexplained. Queue JSON had been normalized before parsing, turning escaped Windows `C:\\...` values into decoded `C://...` paths. The URL guard then treated the drive-prefixed value as a URL before checking for a drive prefix. The candidate record contained both canonical `<WORKSPACE>` console paths and raw `C://` payload paths, proving that separator doubling was nonuniform and originated upstream of comparison projection. The repair parses JSON first, recursively sanitizes decoded values, and independently classifies drive-prefixed paths before URL schemes. Only the three companion hashes change under projection v3; the frozen system record was already canonical and correctly retains its prior hash.

### CI renderer certification and runner maintenance

CI run `31767790801`, job `94667127807`, failed before comparison because Chocolatey's pinned `poppler` 26.5.0 package contained source material but no `pdftoppm.exe`/`pdfinfo.exe` pair and created no command shim. The replacement is the exact conda-forge build `poppler=26.05.0=h4b9d284_3` (package SHA-256 `378623132f942a83051cedcddd1b1e2ebf01b983d633f1da701cf86bb805009a`) in an isolated runner prefix. CI deliberately shares the production `find_soffice()` and `find_pdftoppm()` resolvers instead of maintaining a second discovery implementation.

The first conda-backed run, `31814038514` / job `94811294284`, installed and resolved the correct binaries but exposed a metadata-check defect: `conda list poppler` returned both the exact `poppler` record and its `poppler-data` dependency. The evaluator now retains all rows while requiring exactly one record whose name is exactly `poppler`.

PR certification run `31815449321`, job `94815896964`, then passed the production-parity renderer probe, the permanent planted-change proof, and the complete comparison: **17 identical, 0 allowed, 0 unexplained**. The exact observations were LibreOffice `7.6.5.2 38d5f62f85355c192ef5f1dd47c5c0c0c6d6598b` from stdout at `C:\Program Files\LibreOffice\program\soffice.com`, and `pdftoppm version 26.05.0` from stderr at `D:\a\_temp\resume-poppler-26.05.0-h4b9d284_3\Library\bin\pdftoppm.exe`. The successful conda install took 42.484 seconds; the planted proof took 53 seconds; the full comparison took 11m53s; the total job took 15m38s on runner `2.336.0`.

LibreOffice verification intentionally duplicates production's raw stdout truthiness and 15-second probe timeout because `renderer_version` is a compared field. A cleaner combined-stream rule or longer timeout could make the gate pass while production records `None`. Poppler's version is not in the compared payload; its exact baseline-derived assertion is a reproducibility drift guard. Both expectations come from this frozen manifest rather than duplicated constants.

The repository's existing `.gitattributes` policy keeps tracked batch launchers at CRLF in Windows worktrees; the seven historical launcher blobs are normalized to LF in Git. GitHub Actions are upgraded to the Node 24-compatible majors: equivalence uses checkout v6, setup-python v6, and upload-artifact v7; smoke uses checkout v6 and setup-python v6. Workflow triggers, matrices, commands, artifacts, and failure behavior remain unchanged.

The BRIDGE detailed-guide fixture records a 119-page render. That is captured Release A behavior, explicitly **not a minimum, target, or quality requirement**. A future product change should retain the full answer library while emitting stage-aware working subsets. Its reviewed page-count reduction is expected to trip equivalence and must not be rejected merely for becoming shorter. That product work is separate from Release B architecture.

## Deferred: guide stage granularity

Session 2 retained the complete `all` libraries while adding named working subsets:

| Context | HR | Hiring manager | Panel | Presentation | Technical | Final | `all` |
|---|---:|---:|---:|---:|---:|---:|---:|
| Stratix | 22 | 44 | 51 | 21 | 26 | 28 | 115 |
| Acumatica | 23 | 44 | 50 | 21 | 27 | 29 | 118 |
| State Farm | 23 | 41 | 50 | 20 | 23 | 28 | 112 |
| State Farm control | 42 | 97 | **115** | 31 | 33 | 91 | 137 |

Removing the named-stage early return was correct and is why hiring-manager and panel guides roughly doubled from their pre-Session-2 range of 18 to 27 pages. Those stages now include the story bank they previously lacked, which was the actual defect. Every named guide remains smaller than `all`, and the union of named stages retains every answer, question, story, and evidence sentence from `all` except the intentionally stage-specific instruction line.

The remaining problem is granularity, not mapping. Panel receives Primary Story Bank With Sample Answers, Additional Behavioral Answers, Extended Story-Type Reference, and Story Selection Decision Table in full. The open question is whether a stage should receive all 41 scripted answers or only the six or seven matching its competencies. The State Farm control is the clearest signal: a panel subset at 115 pages against an `all` guide of 137 pages performs almost no practical selection.

**Entry condition.** Take up this work when a stage guide built for a real interview proves unusable at its length. Do not tune against fixtures alone; record which sections or answers went unread.

**Constraint.** Select within sections rather than dropping them. Cutting whole sections merely to hit a page target recreates the original defect, where deep material exists only in a document nobody opens.

The checked-in State Farm posting is for Digital Marketing Data Analyst, while `jobs/State Farm interview_notes.txt` describes a Claims Process Engineer interview. Context scoping correctly rejects those notes for the unrelated posting, so the 112-page Digital Marketing guide exercises the standard registry rather than the State Farm workbook. Because the original Process Engineer posting is unavailable, Session 2 also used an ignored, transient control posting derived only from the checked-in notes to prove State Farm workbook reachability and filtering. Its verified page counts were HR 42, hiring manager 97, panel 115, presentation 31, technical 33, and final 91, versus `all` 137; exact `all` compatibility, ordered assignments, smaller named subsets, and complete named-stage union coverage all passed. The control is verification evidence only, not source material or a frozen production fixture.

That controlled path exposed an existing validator false positive: the State Farm workbook quotes `passionate about insurance` as wording to avoid, but the generic AI-writing scan treated the quoted negative example as generated advocacy. The validator now excludes only that exact instructional phrase from that scan; document text and every broader `passionate about` finding remain unchanged.

### Advisory page budgets

The Session 2 budgets of 15 to 30 pages for hiring-manager and panel guides are now known to be wrong against a correct mapping. They remain advisory hypotheses awaiting the stage-granularity work, not targets the mapping failed to meet. A warning must not fail a build, truncate content, remove sections, or trigger automatic remapping.

The reliability, federal parsing, alignment, archive, output-cleanup, story-engine, and federal-isolation work is complete and integrated into `main`. The post-merge full validation passed **493/493** on August 9, 2026 in 2m54s. Output cleanup removed 60 legacy PDFs and reduced `output/` from 523 to 431 entries; the 475-record job-description archive has zero empty lanes.

## Resolved evidence boundary: Randstad training

The approved Implementation source resume supports building and maintaining **core training programs**, onboarding, and release communications that reduce resistance to system change. It does not support **policy training**, **strategic delivery**, or **delivery-based** language. Use the confirmed training evidence only where a live posting calls for it; do not generalize the claim or add new source language.

## Deferred: search-term semantics

`contains_search_term` remains intentionally duplicated. The two implementations differ in opposite plural directions, so consolidation can change alignment scores, gap suppression, bullet selection, and competency selection. Entry condition: an output reports an obviously supported term as a gap, or reports the reverse. Then choose the semantics explicitly, run `keyword_reliability_corpus.py` before and after, and separately diff alignment scores, suppressed gaps, selected bullets, and selected competencies.

## Deferred: federal program-delivery defaults

`program_delivery` remains absent from `FEDERAL_DEFAULT_CLUSTERS_BY_LANE`. The active federal fixture relies on the current fallback tie-break. Entry condition: a real federal posting in that lane. Then run a before/after cluster comparison and deliberately review any fixture re-pinning. `program_delivery` is a live commercial lane with 33 archived postings, so the asymmetry is real rather than a dead branch; preserve the fallback behavior until the entry condition occurs.

## Follow-Up: validation performance

Do not change validation behavior as part of this completed reliability batch. Profile the full suite separately using the per-check elapsed output. The latest run identified the orphan-function scan, Claude packet self-audits, and Claude bundle refresh as the largest visible contributors. Establish a clean local baseline before optimizing, then preserve the focused selector behavior and the 475-or-higher full-suite gate.

## Verified Stable

- Federal workflow steps now share the ten-minute timeout, process-group termination, output quarantine, and return-code-124 behavior with the commercial workflow.
- The active federal fixture remains pinned at 12 specialized duties, 4 minimum and 14 assessed competencies, and the reviewed cluster weights and keyword tail.
- The 45-to-70-word summary range is the resolved product contract.
- The neutral interview story engine is the sole implementation of shared story selection and spoken-answer logic; the cheat-sheet module retains compatibility re-exports only.
- `build_federal_resume` imports neither `build_interview_cheat_sheet` nor `build_cover_letter` in a clean interpreter.
- The smoke suite now enforces pyflakes undefined-name and redefinition diagnostics alongside its existing runtime checks.
