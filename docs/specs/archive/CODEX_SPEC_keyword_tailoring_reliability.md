# Keyword Tailoring and Recognition Reliability Upgrade

Status: implemented 2026-07-29 and freshly reverified 2026-07-30. Reconciled across a Codex review
pass, a Claude logic/edge-case review, and a second Codex pass. Advisory remains the production
default pending explicit approval of the separately measured balanced-policy switch.
Supersedes CLAUDE_PLAN_keyword_tailoring_reliability.md.

## Scope
These are system-wide defects in the shared recognition and placement logic, not a per-posting
problem. Every fix applies to all commercial resume builds across every role and company, and to both
source lanes (Implementation and Pre-Sales/CSM). The July 27-29 sample (15 builds across 14 targets:
Aptean, Amplify, both GoodShip snapshots, Limbic, Direct Travel, RevsUp, OneTrust, Fisher Phillips,
Azalea Health, TRIA, Fleetio, Pragmatike, APEI) is representative, not exhaustive. No change may be
keyed to a single employer, role title, or JD; all logic keys off classified requirement concepts,
the shared evidence catalog, and role-lane profiles so it generalizes to future postings. Aptean is
used below only as a worked example to make behavior concrete.

## Summary
The July 27-29 review confirms four primary defects that recur across the sample and are structural
to the shared code path:
- Evidence-anchored terms are excluded from prose weaving by an unreachable branch.
- Placement occurs after bullet deletion and across the authoritative content-model boundary.
- Denylist-based extraction admits fragments and generic words into coverage.
- Ledger issues are reported through duplicate paths.

In general terms, for any role the system must realize the supported JD phrases that map to Christian's
verified evidence, place them in the right surface (summary, bullet, or Skills), and count only real
requirement concepts toward coverage. As a concrete instance, the Aptean ERP Consultant build must
realize supported phrases such as project delivery, implementation projects, system configuration,
inventory management, customer-facing/customer-focused delivery, and professional-services consulting,
while apparel/fashion/textile remains one honest domain-gap family. The same behavior must hold for
the equivalent supported/unsupported phrases in every other role (for example SaaS, end-to-end,
feature adoption, and client onboarding seen in the RevsUp, Direct Travel, and OneTrust builds).

Source resumes will not receive keyword-variant bullets. They will be expanded only for genuinely
new, verified evidence.

## Root-cause anchors (code references)
- `scripts/build_resume.py` `weave_supported_keywords_into_top_bullets` ~3820: `if evidence_anchor_for_term(surface): continue` routes anchored terms to Skills only and makes the anchor-aware bullet scoring at ~3874 and ~3892 unreachable.
- `scripts/build_resume.py` assembly ~5556-5654: bullet deletion (5556-5557) and two-page selection (5577) run before weaving (5602, 5654), and weaving runs after the single-render content boundary (5592). `aggressively_close_supported_keyword_gaps` (5569) writes only to Skills.
- `scripts/resume_analysis.py` `audit_keywords` (~1392) and `ats_scan_terms` (~1557): denylist-gated n-grams admit frequent single tokens and malformed phrases.
- `scripts/build_resume.py`: ledger issues appended twice, at ~5754-5757 (audit_notes) and ~4754-4755 (resume_readiness_report).
- `source/evidence_terms.py`: concept `system configuration` carries variants `["system configuration", "configuration"]`; the stem lands while the JD bigram is never realized.

## Core Implementation

### 1. Replace noisy extraction with classified concepts
In `scripts/resume_analysis.py`:
- Classify every candidate as validated requirement concept; skill, tool, method, or competency;
  domain term; or excluded fragment/noise.
- Build core coverage only from validated requirements.
- Build breadth only from validated skills/tools/methods and domain terms.
- Use the existing requirement parser and deterministic phrase-shape rules; add no heavyweight NLP
  dependency.
- Reject: bare adjectives and participles such as `focused`, `trusted`, `operational`; dangling
  verbs such as `identify`; generic standalone nouns such as `profile`, `outcome`, `strategy`;
  malformed phrases such as `same delivery`, `between customer`, `sql advanced excel`; and employer,
  benefit, education, and culture boilerplate.
- Preserve legitimate acronyms through an explicit allowlist: ERP, SaaS, CRM, SQL, ETL, UAT, KPI,
  API, RFP, SOW, QBR.
- Reconcile singular/plural variants under one concept while retaining the JD literal surface for
  ATS matching.
- Keep `customer-focused` when it appears as a validated requirement and maps to customer-delivery
  evidence; exclude only bare `focused`.
- Group related unsupported surfaces such as apparel, fashion, and textile into one readable domain
  gap.

### 2. Make the evidence catalog machine-actionable
Extend `source/evidence_terms.py` with: stable concept ID; permitted JD literal surfaces; source
employer and role; normalized source-paragraph fingerprint; compatible bullet themes; permitted
placement types; preferred competency label; evidence strength and ownership limitations.

Add only source-verified concepts exposed by recent builds, including inventory management,
root-cause analysis, data validation, customer-facing delivery, customer-focused delivery,
multiple-project delivery, process discovery, operational transformation, business outcomes,
non-technical stakeholder communication, and professional-services consulting.

Use this catalog consistently for recognition, literal mirroring, bullet selection, rewriting,
Skills, and reporting. Derive or retire overlapping competency-trigger definitions so separate
taxonomies cannot drift.

The permitted-surface list is the sanctioned mechanism for "same evidence, different JD wording."
When a supported concept already exists but a posting words it differently, add that JD surface to
the concept's permitted-surface list and realize it at generation time. Do not add paraphrase bullets
to the source resume files; the source files are the provenance root and must stay free of
keyword-variant padding so fingerprint validation remains meaningful.

### 3. Validate evidence fingerprints
Extend `python tasks.py source-lint` (`scripts/source_lint.py`) to resolve every catalog entry
against its expected source resume, employer, and role; hash normalized paragraph text rather than
raw DOCX bytes; fail when an anchor is missing, ambiguous, or its fingerprint has changed; and report
the affected concept and expected role without silently remapping it. A source-resume edit must
therefore be followed by intentional evidence review and fingerprint refresh.

### 4. Replace split placement with one planned pass
Before two-page bullet deletion:
1. classify JD concepts;
2. map supported concepts to source evidence;
3. rank concepts by requirement centrality, repetition, title relevance, and evidence strength;
4. score source bullets for proof quality and literal-realization opportunities;
5. protect the strongest carrier for each supported must-have;
6. select and reorder bullets;
7. assign remaining terms to role summaries, bullets, or Skills;
8. apply provenance-checked rewrites;
9. render the content model once;
10. run one final placement audit.

Specific corrections:
- Remove the anchored-term `continue` that makes anchor-aware prose scoring unreachable.
- Remove `priority_ledger_assertion_terms` (`build_resume.py` ~4027) and its Blue Yonder / Adobe
  identity branches. Express those expectations through normal classified concepts, evidence
  mappings, and corpus regression fixtures. Remove any comparable employer- or title-specific
  recognition, coverage, or placement hardcodes found during implementation.
- Make anchored terms eligible for role-summary and bullet placement; use Skills when prose is
  unsafe or unnecessary.
- Collapse `aggressively_close_supported_keyword_gaps` and the later Skills fallback into this
  planned pass.
- Move every content mutation before the authoritative render boundary, or move that boundary after
  placement.
- Compute ledger diagnostics once and deduplicate notes before output.
- If protected bullets cannot all fit within two pages, retain the highest-centrality proof, release
  the lowest-centrality carrier, and record the lost supported term as a tailoring conflict.

### 5. Realize exact surfaces safely
- Keep final matching exact; improve what the writer emits.
- Prefer in-place rewrites when the evidence-bearing bullet already supports the requested phrase.
- Limit each bullet to at most two newly realized JD literal phrases.
- Use role summaries for identity/context phrases such as professional-services consultant and SaaS
  implementation; bullets for project delivery, system configuration, inventory management,
  customer-facing work, and outcomes; Skills for concise competency surfaces when prose would become
  dense or repetitive.
- Reject a rewrite when it lacks same-role source provenance; changes ownership; introduces a new
  metric, tool, industry, or outcome; creates repeated stems or keyword stacking; or exceeds
  bullet-length or two-page limits.
- After every rewritten bullet, run the existing prose repair/validation rules and the relevant
  writing-quality evaluation (`utils.enforce_prose_quality`, `writing_eval`). A rewrite must pass
  both provenance and readability checks.
- For stem-versus-phrase cases such as `configurations` versus `system configuration`, prefer one
  natural replacement; use Skills only if that replacement fails. Do not insert both.

### 6. Improve competency handling
- Insert only evidence-supported, skill-shaped labels.
- Reject job titles, adjectives, generic nouns, and sentence fragments.
- Protect original source skills and sole carriers of validated JD concepts.
- Replace the blanket "more than 25 Skills items" warning with checks for unsupported items,
  redundancy, low-signal ratio, category crowding, and actual page pressure.
- Permit a clean category to exceed its soft target when all items are relevant and coverage-bearing.

## Policy, Gating, and Compatibility

### Policy modes
Add `--keyword-policy <balanced|advisory|exhaustive>` to commercial resume and dry-run commands:
- `advisory`: reports all findings and never stops dependent documents.
- `balanced`: blocks only supported-but-unwritten core/must-have concepts; supported breadth misses
  produce review warnings.
- `exhaustive`: blocks any supported core or breadth concept left unwritten.

Unsupported domain gaps never trigger Tailoring INCOMPLETE under any mode.

### Fit and tailoring states
Keep separate structured fields: `Fit status` (PASS, BRIDGE, FAIL, POOR) and `Tailoring status`
(COMPLETE, REVIEW, INCOMPLETE). Add Tailoring status to `ResumeReadiness`, and thread it through both
`BuildResult` and `ResumeAssemblyResult` so console output, dry-run output, and Resume Notes all read
a consistent value.

### Filename compatibility
- Do not add Tailoring status to filenames.
- Preserve the existing Fit suffix contract and `status_suffixes = (" BRIDGE", " FAIL", " POOR")`
  (`build_resume.py` ~2525).
- Leave downstream target-name matching intact (`build_cover_letter.find_resume_output`,
  `build_application_checklist.latest_tailored_resume`).
- Gate the active workflow using structured readiness returned by the resume build, not filename
  tokens.
- Direct cover-letter and qualifications builders must recompute readiness from the matching resume
  and active JD, then apply the selected policy before writing dependent documents.
- The application checklist may inspect an incomplete resume but must display its Tailoring status
  prominently.

### Balanced-default rollout
Implement the modes first with advisory as the temporary shadow default. Run balanced policy across
the July 27-29 and existing 20-role corpora without stopping builds; record every projected blocker.
Promote balanced to the production default only when: there are zero false core blockers; every
projected blocker is confirmed as evidence-supported and genuinely unwritten; no PASS/BRIDGE build is
blocked solely by a breadth term; no malformed or generic term produces INCOMPLETE; and direct and
workflow-dependent document gates behave identically. If those conditions fail, advisory remains the
default until classification is corrected. Balanced remains selectable throughout calibration.

## Reporting
Resume Notes will contain: Fit status and Tailoring status; core and breadth coverage; placed
supported terms with location and evidence anchor; supported-but-unwritten terms; genuine
evidence/domain gaps; excluded noise; and bullet-protection or page-fit conflicts. Preserve existing
`ats_coverage` fields for compatibility while adding categorized details. Each issue must appear once.
Update command help, `SYSTEM_REFERENCE.md`, `ARCHITECTURE_MAP.md`, and generated review materials
after behavior stabilizes.

## Validation and Acceptance

### Worked-example regression (Aptean)
This is the concrete acceptance case; the same pass/fail pattern (realize supported phrases, exclude
noise, keep true domain gaps out, report once) must be applied per target across the corpus below.
- Place project delivery, implementation projects, system configuration, inventory management,
  customer-facing/customer-focused delivery, and professional-services consulting naturally.
- Place other supported requirements only through evidence-compatible wording.
- Exclude standalone `focused`, `internal`, `high-quality`, and `process-related` from denominators.
- Keep apparel/fashion/textile absent as one grouped domain gap.
- Maintain exactly two pages and all source-truth requirements.
- Report every ledger issue no more than once.
- Ensure no rewritten bullet adds more than two JD literals.

### Recent-build regressions
Rebuild Amplify, both GoodShip snapshots, Limbic, Direct Travel, RevsUp, OneTrust, and Fisher
Phillips. Under projected balanced mode: supported-unwritten core count must be zero after tailoring;
breadth-only concepts must not block; and known fragments such as `rather`, `have`, `between
customer`, `same delivery`, and `sql advanced excel` must never enter coverage.

### Automated tests
Add tests for: term classification and noise rejection; acronym preservation; singular/plural
reconciliation; source fingerprint validation and drift failure; anchored terms reaching prose
placement; protected-bullet survival through condensation; exact literal realization;
two-literal-per-bullet enforcement; provenance rejection; prose-quality rejection; Skills fallback;
duplicate-note prevention; all three policy modes; Fit/Tailoring independence; filename and
downstream matcher compatibility; direct-builder and workflow gating parity; and final audit after
the single render boundary.

Also add tests for the employer-neutrality boundary: employer-neutral production behavior (no
recognition/coverage/placement branch keys off employer identity); evidence-catalog employer
anchoring remains intact; reorganization-fact preservation for East West and Aptean; and confirmation
that removing `priority_ledger_assertion_terms` does not regress its former priority terms (project
management, implementation project, SaaS for the Blue Yonder fixture; global program, vendor partner,
ai pilot for the Adobe fixture) now that they route through the general classified-concept path.

### Corpus and visual verification
- Run the July 27-29 corpus and existing 20-role corpus.
- Record before/after core coverage, breadth coverage, supported-unwritten count, genuine-gap count,
  excluded-noise count, Skills count, maximum category size, page count, Fit status, Tailoring
  status, and projected policy outcome.
- Stop a batch if a supported core concept disappears, source evidence is lost, filenames no longer
  resolve downstream, or two-page compliance regresses.
- Run `python scripts/smoke_test.py`; `python tasks.py validate`; `python tasks.py source-lint`;
  relevant resume builders; `python tasks.py commands`.
- Render and inspect representative implementation, customer-success, project-management,
  process-improvement, and technical-consulting outputs.

## Employer References and Source-Truth Boundaries
- Recognition, classification, coverage, and placement logic must never branch on employer identity.
- Employer-specific regression fixtures are permitted in tests but must exercise generic production
  behavior only.
- Employer-anchored evidence-catalog entries remain required, because they identify where Christian's
  approved proof originated. They are data, not employer-specific branching.
- Preserve the mandatory "Position impacted by company reorganization." facts for East West and
  Aptean, and preserve company-context paragraphs and all other source-truth checks.
- The employer-neutral rule must not remove or weaken factual employer references in approved resume
  content.

## Incremental Rollout and Progress Tracking
Land the change in ordered increments, not all at once. Each increment has a single focus and an exit
gate that must pass before the next begins. Run the July 27-29 corpus after every increment and
record the metric row (coverage, supported misses, genuine gaps, excluded noise, Skills density, page
count, Fit, Tailoring, policy outcome) so any regression is attributable to one increment. Update the
status box as each lands.

Progress report after each increment. Do not begin the next increment until the current exit gate
passes, then report: increment status and completed checklist; files and major functions changed;
tests and builders run; July 27-29 corpus metric delta; supported misses, genuine gaps, and excluded
noise; Fit, Tailoring, page-count, and policy changes; regressions or blockers; and the next
increment. Update the checkboxes below as each increment lands.

- [x] Increment 1 - Recognition classifier and shape gate. Add the four-class classifier; run the
  phrase-shape gate before `repeated_keyword_is_signal`; subsume the nine overlapping noise/taxonomy
  structures in `resume_analysis.py` (appendix item 1). Exit gate: no noise token (focused, trusted,
  operational, internal, external, same delivery, between customer, sql advanced excel) enters core or
  breadth on the corpus; `smoke_test.py` lane assertions pass.
  Completed 2026-07-29: the 15-run July 27-29 sample moved from 13 known core-noise and
  5 known breadth-noise occurrences across 12 affected snapshots to zero; the focused
  classifier, denominator-hygiene, and lane-profile tests pass.
- [x] Increment 2 - Duplicate ledger-report fix. Compute ledger diagnostics once; dedupe notes. Exit
  gate: each ledger issue appears at most once in Resume Notes across the recent builds. (Small and
  independent; landing it early makes later diagnostics readable.)
  Completed 2026-07-29: the assembly-time duplicate append path was removed and final note
  emission is defensively deduplicated; focused PASS-note and ledger-note tests pass. Coverage,
  Fit, page count, and policy behavior are unchanged.
- [x] Increment 3 - Evidence catalog and readers. Extend the catalog schema and concepts; retire
  `JD_TERM_MIRROR` and back `jd_preferred_surface` with permitted surfaces; update all five catalog
  readers to consume the new fields; consolidate `SIMPLE_COMPETENCY_KEYWORDS` and
  `CONDITIONAL_COMPETENCY_ITEMS`; extend `source-lint` to fail on fingerprint drift. Exit gate:
  `source-lint` fails on a deliberately altered fingerprint; new fields affect behavior, not inert;
  lane smoke assertions pass.
  Completed 2026-07-29: the catalog now supplies stable IDs, permitted surfaces, source
  provenance and normalized fingerprints, placement types, competency labels, evidence strength,
  and ownership limits. All readers consume the richer schema; the static mirror table is retired;
  supplemental competency triggers no longer duplicate cataloged evidence concepts. Source lint
  passes current sources and rejects deliberate fingerprint drift. Full smoke passes 433/433.
- [x] Increment 4 - Placement engine. Remove the anchored-term `continue`; build the single
  pre-boundary placement plan; inject protected-carrier awareness into
  `select_experience_bullets_for_two_page_resume`; move both weaves and
  `aggressively_close_supported_keyword_gaps` before the render boundary and consolidate them; remove
  `priority_ledger_assertion_terms` and comparable employer hardcodes; update the existing weave tests
  in `smoke_test.py`. Exit gate: anchored supported terms reach prose; Aptean supported phrases land;
  Adobe and Blue Yonder former priority terms do not regress; exactly two pages.
  Completed 2026-07-29: placement is planned before condensation, the strongest evidence carrier
  is protected inside two-page selection, anchored concepts can reach prose, and bullet/Skills
  realization now occurs before the authoritative content boundary. The separate Skills-only
  closure and employer-specific Adobe/Blue Yonder assertion branches are removed. The Aptean
  worked example renders at two pages with zero supported core misses; its only core misses are
  apparel, fashion, and textile (one unsupported domain family). Full validation passes 434/434.
- [x] Increment 5 - Literal realization and rewrite safety. Exact in-place JD-surface realization;
  two-literal-per-bullet cap; provenance, ownership, prose-repair, and writing-quality gates on every
  rewrite; Skills handling and count-warning replacement. Exit gate: exact JD surfaces realized with
  no stem repetition or keyword stacking; prose-quality checks pass.
  Completed 2026-07-29: bullet realization is capped at two newly added JD literals and rejects
  source-role provenance drift, new ownership verbs, changed metrics, prose-engine failures, and
  writing-evaluation failures. Skills diagnostics now measure invalid/low-signal items, redundant
  labels, and actual page pressure instead of warning on raw count alone. The Aptean fixture retains
  zero supported core misses and two-page layout; full validation passes 435/435.
- [x] Increment 6 - Policy, state, reporting. Add `--keyword-policy` with advisory as shadow default;
  split Fit and Tailoring status; thread Tailoring through `ResumeReadiness`, `ResumeAssemblyResult`,
  and `BuildResult`; gate dependent docs through structured readiness with filename compatibility;
  restructure Resume Notes. Exit gate: direct-builder and workflow gating behave identically; no
  Tailoring token in filenames; downstream target matching intact.
  Completed 2026-07-29: advisory, balanced, and exhaustive policies are available on workflow,
  resume, and dry-run paths. Fit and Tailoring are separate structured states threaded through
  `ResumeReadiness`, `ResumeAssemblyResult`, and `BuildResult`; filenames retain Fit suffixes only.
  Direct cover-letter and qualifications builders recompute readiness and match workflow gating.
  Aptean is Tailoring REVIEW under advisory/balanced with no core blocker; exhaustive blocks its
  supported breadth misses. Full validation passes 436/436.
- [x] Increment 7 - Corpus verification, balanced promotion decision, docs. Run both corpora; record
  before/after metrics; confirm the balanced-promotion criteria (zero false core blockers, no
  breadth-only blocking, no malformed INCOMPLETE, direct/workflow parity); promote balanced only if
  met; update `SYSTEM_REFERENCE.md`, `ARCHITECTURE_MAP.md`, command help, and review materials. Exit
  gate: acceptance criteria in the Validation section satisfied.
  Reverified 2026-07-30 from 35 independently rebuilt packaged DOCX files under fingerprint
  `25c359cd2cee013996a435d8edf089712b3622934e8a2c475788fe1158970eb9`:
  35/35 builds succeeded, 35/35 rendered at exactly two pages, packaged audits and direct/workflow
  policy outcomes agreed, and active inputs/deliverables stayed byte-identical. Balanced safety
  passed with zero false or non-requirement blockers. Four genuine `planned_but_unwritten` core
  blockers remain across 4/35 builds (11.4% disruption). Aptean is Fit PASS with 100% core coverage,
  zero balanced blockers, and apparel/fashion/textile preserved as one unsupported domain family.
  Advisory remains the default because the production switch requires separate explicit approval.
  Full validation passes 444/444 checks. The authoritative metrics and review packet are in
  `scratch/fresh_keyword_corpus_final_corrected_20260730/decision/`.

## Guardrails
- Genuine domain gaps remain unsupported and are never inserted (Aptean apparel/fashion/textile is
  one example); this rule holds for the unsupported domain family of any role.
- All recognition, classification, coverage, and placement logic generalizes through requirement
  concepts, the shared evidence catalog, and lane profiles rather than employer identity.
- Exact ATS matching remains strict.
- Source resumes gain only genuinely new verified evidence. Alternate JD phrasings for evidence that
  already exists are captured in the evidence catalog's permitted-surface list and realized at
  generation time, not added as paraphrase bullets to the source files.
- Job titles, role order, company-context paragraphs, reorganization facts, Education, Professional
  Development, formatting, two-page length, and Word-only output remain unchanged.
- Existing unrelated workspace changes are preserved.

## Appendix: implementation notes (code-grounded)
These are specific integration points found while tracing the current code. They make the sections
above concrete and prevent the noise or drift from returning through a table nobody updated.

1. Unify the fragmented noise/taxonomy tables, do not sit beside them. `resume_analysis.py` holds at
   least nine overlapping structures the classifier must subsume: `BULLET_PLACEMENT_EXCLUDED` (~116),
   `AUDIT_NOISE_KEYWORDS` (~401), `AUDIT_PRIORITY_KEYWORDS` (~521), `CONSULTING_TAXONOMY_PHRASES`
   (~579), `STOP_WORDS` (~584), `AUDIT_BLOCKED_PHRASES` (~622), `AUDIT_PHRASE_TAIL_PRIORITY_WORDS`
   (~711), `SUMMARY_PLACEMENT_TERMS` (~786), plus gate functions `is_low_signal_audit_keyword`
   (~1353), `is_generic_soft_keyword` (~1538), `breadth_term_is_noise` (~1861), and the inline
   `phrase_blockers` set in `ats_scan_terms`. Leaving any as a parallel denylist reopens the leak.

2. The core-noise root gate is specific. `audit_keywords` (~1392) accepts single tokens of length >= 4
   that pass `repeated_keyword_is_signal` (~1374). That frequency acceptance is what admits "focused",
   "trusted", and "operational" into CORE coverage. The classifier's shape gate must run before this
   frequency acceptance, not after it.

3. Reuse, do not duplicate, `classify_keyword_gap_support` (`build_resume.py` ~3094). Its existing
   return values (`supported-direct-unresolved`, `unsupported-do-not-insert`) already encode part of
   the new taxonomy. Re-express it on top of the single new classifier rather than adding a parallel
   one.

4. Back `jd_preferred_surface` (~235) and retire the static `JD_TERM_MIRROR` (~1587) with the
   catalog's permitted-surface list. These are the existing surface-mirroring mechanism; the catalog
   must replace it, not run in parallel.

5. Both weave passes run after the render boundary. `weave_supported_keywords_into_summary`
   (`build_resume.py` ~5602) and `weave_supported_keywords_into_top_bullets` (~5654) both execute
   after the content-model boundary (~5592). The "move all mutations before the boundary" instruction
   must cover both, plus the Skills-only `aggressively_close_supported_keyword_gaps` (~5569).

6. The protected-bullet hook is `select_experience_bullets_for_two_page_resume` (~5577). It runs
   before the weaves and currently has no knowledge of pending placements. The "protect strongest
   carrier" logic must be injected here.

7. Existing tests will break, not just be added to. `smoke_test.py` already calls
   `weave_supported_keywords_into_top_bullets` (~4933) and `weave_supported_keywords_into_summary`
   (~5117, ~5147) directly. Changing their behavior or signature requires updating these assertions.

8. Every evidence-catalog reader must be updated when the schema is extended. Current readers:
   `evidence_supported_surfaces` (~211), `evidence_anchor_for_term` (~230), `jd_preferred_surface`
   (~235), `classify_keyword_gap_support` (~3094), `ledger_terms_for_placement` (~3947). Adding keys
   is inert unless these consume the new fields (permitted surfaces, placement rules, fingerprint).

9. Competency triggers live in a separate config. `job_profiles.py` `SIMPLE_COMPETENCY_KEYWORDS`
   (~24) and `CONDITIONAL_COMPETENCY_ITEMS` (~68) are their own taxonomy for Skills. Consolidate them
   around the shared catalog too. Note the project rule: after editing `job_profiles.py`, run
   `scripts/smoke_test.py` and confirm the lane-detection assertions still pass.

10. Minor drift symptom: `replace_paragraph_prefix` is defined in both `build_resume.py` (~2346) and
    `resume_content.py` (~425). Not core to this work, but it is the kind of duplication the
    consolidation should discourage.
