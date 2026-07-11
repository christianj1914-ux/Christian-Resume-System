# Revised Implementation Plan: Staged Reliability Program (Authoritative)
## July 2, 2026 - Supersedes the prior Codex draft. Merges the Codex staged program, the two Claude findings documents, and the Claude review, with all evidence confirmations resolved by Christian on July 2, 2026.

## Summary

Codex's staged structure, shared models, and six corrections are adopted as written. This revision adds the nine gaps from the Claude review (most importantly the terminology injection mechanism that makes the federal coverage gate satisfiable), replaces assumed evidence facts with Christian's actual confirmations, and expands the acceptance plan with positive coverage tests. Nothing here is a per-JD fix: the fixture JDs (Foundant, Tyfone, Bonterra, IRS, one per commercial lane) are regression anchors for shared logic across the complete federal and standard workflows.

## Confirmed Evidence Facts (resolved July 2, 2026, confirmed directly by Christian)

These four confirmations authorize source updates. Each new source entry and evidence record must carry `confirmed_on: 2026-07-02` and provenance `christian-direct-confirmation`. Every unconfirmed capability remains unclaimable.

1. **East West SQL objects: CONFIRMED, broader than the Codex draft assumed.** The 200+ report portfolio included personally creating views, stored procedures, functions, and reporting data models. Claimable inside the reporting/BI context ("designed and deployed 200+ SQL-based reporting tools, including views, stored procedures, and reporting data models"). SQL Server *instance administration* (configuring, monitoring, tuning servers) was NOT confirmed and stays on the never_claim list along with clustering, replication, and failover administration.
2. **Aderant backup and recovery: CONFIRMED as mostly planning with limited hands-on.** Restores and recovery testing were performed hands-on but were not the primary duty. Ownership ceiling: "supported" or "performed" backup, restore, and recovery-testing tasks alongside disaster recovery planning; never "owned," "administered," or "led" backup/recovery infrastructure. HA/DR architecture ownership remains never_claim.
3. **Version control: CONFIRMED for both Azure DevOps/TFS and Git/GitHub as personal hands-on use, at Aptean only** (work items, repos, release tracking). Claimable as tool use and change-management practice under the Aptean role exclusively; no version-control claims at East West or any other employer. CI/CD pipeline ownership and DevSecOps program ownership were NOT confirmed and remain never_claim.
4. **Home Depot contact center framing: CONFIRMED as accurate**, including service level and interaction-volume reporting. Evidence records for the LivePerson/chat/SMS claims gain allowed terminology: "contact center operations," "service level reporting," "customer interaction data," "interaction-volume trend analysis," "forecasting." "Workforce management" as a named discipline was not specifically confirmed: classify it Adjacent (bridge language only, e.g., "analytics supporting staffing and workload decisions"), never a direct claim.

## Core Interfaces and Source Truth (adopted from Codex, two additions)

Shared models as specified: `TargetContext` (with official/display/matching title forms), `RequirementElement`, `EvidenceRecord`, `EvidenceMatch`, `CoverageReport`, `BuildOutcome`. Evidence records are built from approved commercial DOCX files and federal source JSON; processing config stores only synonym maps, capability tags, ownership limits, and never_claim patterns. The catalog indexes approved sources and is never an independent claim source.

Additions:

- **EvidenceRecord gains `allowed_terminology` and `rewrite_templates`** (slot-based, human-written full sentences with typed slots for metric, platform, scope, and JD-canonical term). These power the injection stage (phase 3b) and the prose rebuild (phase 4).
- **Display-title shortening rule:** keep any title segment whose content words also appear in the JD's requirement-bearing sections; drop only segments that appear nowhere outside the title line ("Strategic Advancement Focus" drops from display; "ERP (Apparel)" or "Enterprise" would not). Official title is preserved in full in TargetContext; matching title is used for output lookups.

## Implementation Changes

### Phase 1 - Regression foundation and emergency defect shield (unchanged from Codex, three additions)

Characterization fixtures; collision-aware genericization transformer shared by resume and interview scrubbers; detection and repair of duplicate replacements, `X to X`, missing articles, duplicate list entries, preferring "legacy ERP," "successor platform," or a rewritten platform-migration sentence; final-output assertions for substitution corruption, unsupported claims, canonical professional-development names, and stale application questions.

Additions: (a) bullet-ending punctuation normalizer in the same final-output pass; (b) header segment semantic dedupe: no two header segments may share a dominant content word ("Enterprise SaaS | Enterprise Systems" collapses); (c) correct `.context` docs to the real `scripts/config/` paths so future review threads read accurate architecture.

### Phase 2 - Target and requirement ingestion (unchanged from Codex, one addition)

Canonical title extraction via `resume_analysis.extract_job_title()` with the three-form model; commercial responsibility/qualification section parsing; federal grade, specialized-experience, competency, numbered, lettered, and semicolon-delimited element parsing; cluster/bucket system retained as fallback and ordering prior below three reliable elements; ATS terms and competency candidates derived from parsed elements only, with the three-item Core Competencies cap and skill/tool/domain restriction ("adjust training" becomes a RequirementElement, never a competency label).

Addition: **grade-clause detection.** During federal parsing, capture the target grade and the "one year equivalent to GS-X" requirement as structured fields on TargetContext for phase 3c.

### Phase 3 - Evidence matching, injection, and coverage (Codex phase 3 plus the three missing federal stages)

**3a - Matching (as Codex wrote it):** Direct/Adjacent/Transferable/Unsupported classification, no cross-employer moves, ownership verbs capped by the evidence record, never_claim prohibition, commercial element coverage driving bullet selection, summary emphasis, fit status, alignment scoring, Resume Notes, and bridge decisions. Qualification statements rebuilt around relevant elements; application questions remain a separate, explicitly supplied input.

**3b - Terminology injection (new, required before the federal gate turns on):** For every Direct element, the injector rewrites the matched evidence bullet using the announcement's canonical terms, constrained to: terms listed in the record's `allowed_terminology`; the record's own role and employer; the record's ownership ceiling; and preference for the most recent qualifying period when the evidence supports it there. Rewrites go through the record's slot templates, not free-form substitution, and the phase 1 collision transformer runs on the result. Without this stage the coverage gate is a wall with no door: the IRS build would fail because Home Depot bullets do not currently say "contact center."

**3c - Grade-equivalence framing (new):** When a grade clause was parsed, generate one framing sentence in the most recent role from evidence-record scope facts (five sites, 150+ users, independent platform selection and migration-risk authority). Template in config, facts from records; generalizes to any announcement and grade.

**3d - Competency weaving (new):** Map announced minimum and assessed competencies to capability tags; warn-level registry rule that each competency name or registered variant appears at least once in the document; misses reported in the coverage matrix, never bolted on as a list.

**3e - Coverage gates (Codex version, kept):** run on both the content model and the final rendered text. Federal: every Direct target-grade element present in dated work experience, every never_claim pattern absent, both hard. Commercial: coverage drives scoring and notes, soft gate.

**3f - Evidence intake loop (new):** every Unsupported or Adjacent classification emits a plainly worded confirmation question into the build notes ("Did X involve Y? If confirmed, this becomes claimable"). Confirmed answers update approved sources with provenance, exactly as the four July 2 confirmations did. This is how the engine improves with each announcement instead of freezing at the IRS posting's gaps.

### Phase 4 - Shared prose and validation framework (unchanged from Codex, one scope addition)

Artifact-specific sentence assembly; targeted checks for conjunction overload, nested lists, repeated opening verbs, repeated proof clauses, slot/template overlap, stacked modifiers, and resume-only mandates in spoken text; centralized professional-development names; rule IDs with severity, artifact applicability, and mechanical fixers; three deterministic repair passes then visibly marked DRAFT with plain-language feedback; DRAFT never selected downstream and never reported as sendable.

Scope addition: **the summary composers are in scope.** `build_gs14_summary` and the commercial summary/role-summary composers migrate onto the assembler, and cluster `summary_phrase` fragments are rewritten as full slotted sentences. The live IRS summary's broken grammar ("delivering implementation, enterprise systems, and technology delivery and recent senior-technical-authority scope across... environments") is the S1 evidence; the plan previously fixed every prose surface except the one that produced it.

DRAFT semantics addition: `track_applications.py` must not record a DRAFT build as an application-ready output, and `run_resume_workflow.py` must not count a DRAFT as a successful run for automatic tracker updates.

### Phase 5 - Output integrations (unchanged from Codex, two additions)

Order: federal resume and qualifications statement; commercial resume and notes; cover letter; interview cheat sheet and detailed guide. Spoken-register converter for every SAY THIS block (first person, conversational sentence length, no resume compliance sentences, deduplicated software lists, shortened repeat-proof references). Explicit application questions preserved; strong JD mismatch produces DRAFT with the suspect prompt named, never silent deletion. All Codex preservation guarantees kept (coaching frameworks, debrief intelligence, source snapshots, company-context paragraphs, role order/titles, two-page enforcement, ATS validation, honest FAIL/BRIDGE/POOR naming).

Additions: (a) **application-questions lifecycle**: `tasks.py jd-archive` and the workflow runner's JD-swap step archive or prompt about `jobs/application_questions.txt` alongside the JD, killing the stale-question class at the source; (b) **element-driven question prediction**: Adjacent-classified elements are high-probability probing questions and each gets a prepared bridge answer in the guides, replacing part of the keyword-trigger logic.

### Phase 6 - Commercial model-then-render migration (unchanged from Codex)

Provenance-bearing content model introduced only after regression protection; summary and role summaries first, then bullet selection/reordering; single render to the Word base with formatting-only passes afterward; superseded XML mutation passes removed as each model boundary becomes authoritative.

## Test and Acceptance Plan (Codex plan plus additions)

All Codex acceptance items stand (validate passes expanded; Foundant: no substitution corruption, no junk blockers, title forms correct, "adapt training" as requirement not competency; Tyfone: clean SAY THIS blocks, DRAFT on mismatched questions, "McKinsey Forward Program" consistent; IRS: 15/9/14 parse counts, coverage matrix, no false claims, no $0 salary; cover-letter replay converging within three repairs or excluded DRAFT; render-to-image inspection; two-page and Word-only preserved).

Additions:

- **Positive injection tests (the point of the program):** regenerated IRS resume contains "contact center," "service level," and "customer interaction data" inside the Home Depot block sourced from the LivePerson evidence record; "views, stored procedures," and "data models" language inside the East West block; Azure DevOps/TFS and Git/GitHub terminology only under Aptean, with a matching negative assertion that no version-control claim appears under any other employer; hands-on restore/recovery-testing language under Aderant capped at "supported/performed."
- **Negative boundary tests for the same records:** no SQL Server instance-administration claim anywhere; no clustering/replication/failover; no CI/CD or DevSecOps ownership; "workforce management" appears only in bridge phrasing if at all; Aderant recovery language never uses "owned/administered/led."
- Regenerated IRS and Foundant summaries pass the structural prose rules (no double-and chains, no nested lists, no serial list missing its final conjunction).
- Grade-equivalence sentence present in the most recent role on federal builds that parse a grade clause.
- Competency-weaving report present in the coverage matrix; zero unexplained competency misses on the IRS fixture.
- A DRAFT resume in `output/` is ignored by a subsequent cover letter build and produces no tracker update (explicit test).
- A leftover `application_questions.txt` from a prior company triggers DRAFT naming the suspect question.
- Foundant header contains no two segments sharing a dominant content word.
- CoverageReport for a fixture with known gaps emits correctly worded intake questions.

## Sequencing and Gates

Phase order 1 through 6 as listed. Hard gates: phase 3 may not start until the confirmed-facts source updates land with provenance fields (the confirmations themselves are resolved as of July 2, 2026); the federal coverage hard gate (3e) may not be enabled until injection (3b) passes its positive tests; phase 6 may not start until the full regression corpus is green through phase 5. Every phase ends with `python tasks.py validate` plus its named acceptance items, and each phase's new assertions join the permanent regression set.

## Assumptions

- "Hands-on" supports performing the named activities, never architecture ownership, administration leadership, or people management.
- The four July 2 confirmations are the complete current authorization; the intake loop (3f) is the only mechanism for future expansions, always with Christian's explicit answer and provenance recorded.
- The shared engine is implemented incrementally; urgent corruption fixes (phase 1) precede and do not depend on the model refactor (phase 6).
