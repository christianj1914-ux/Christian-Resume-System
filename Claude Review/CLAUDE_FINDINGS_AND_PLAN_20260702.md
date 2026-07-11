# Claude Findings and Implementation Plan - July 2, 2026 (Expanded, System-Wide)

Scope: (1) a reusable federal specialized-experience tailoring engine that adapts to every federal JD automatically, (2) cover letter failure elimination, (3) natural-sounding content generation. Every fix below is a change to shared logic, config, or validation - never a hand-edit to one output. The IRS GS-14 posting is used as evidence throughout, but no fix targets that resume specifically. Planning only; all implementation is for Codex.

Evidence base: live IRS Federal Resume and Federal Qualifications Statement outputs, `jobs/federal_job_description.txt`, `scripts/build_federal_resume.py`, `scripts/build_cover_letter.py`, `scripts/build_resume.py`, `scripts/writing_eval.py`, `config/language_rules.py`, and failure traces in `scratch/cover_letter_traces/`.

---

## PART 0: System-Wide Placement Rules

For every fix in this plan, the change lands in the shared layer so all outputs inherit it:

- Language and grammar rules go in `config/language_rules.py` and `scripts/writing_eval.py`, which resume, federal resume, cover letter, checklist, and interview builders already share through `utils.enforce_prose_quality()`.
- Evidence and targeting rules go in `config/job_profiles.py` or a new `config/federal_evidence.py`, never inline in a builder script.
- Keyword and readiness fixes go in `build_resume.py` helpers (`audit_keywords`, `resume_readiness_report`), which every downstream builder consumes.
- JD ingestion fixes (role-title normalization) go at the single point where `jobs/job_description.txt` is parsed, so filenames, prose, lookups, and tracker rows all see the same clean values.
- Every new hard rule gets a matching assertion in `scripts/smoke_test.py` or a new regression script, so the rule cannot silently regress.

---

## PART 1: Federal Specialized-Experience Tailoring Engine

### 1.1 Why the current logic cannot meet the "leave nothing to interpretation" bar

The current federal pipeline works at the wrong granularity. `FEDERAL_REQUIREMENT_CLUSTERS` (build_federal_resume.py ~447) is a fixed, hand-built taxonomy of about a dozen clusters (implementation_delivery, data_migration, executive_alignment, ...). `federal_requirement_audit` (~1450) reads the JD only to *weight* those pre-existing clusters and derive keyword targets. Bullet selection (`selected_bullet_candidates_by_role` ~1682) then scores source bullets against cluster weights and keywords, and `tailor_text` (~1673) applies light fixed rewrites.

Consequence: the JD's own specialized experience elements are never treated as first-class requirements. The IRS announcement lists 15 discrete GS-14 specialized experience elements. Four of them ("administering, configuring, monitoring, tuning... Microsoft SQL Server," "high availability and disaster recovery... clustering, replication, failover," "stored procedures, views, functions, and data models," "DevSecOps... automated deployment, version control") never appear in a dated position block, and the JD's dominant vocabulary ("contact center" appears in five separate elements, plus "workforce management," "service level reporting") appears nowhere in the resume, even though the Home Depot chat/SMS/LivePerson work is direct evidence for it. No fixed cluster taxonomy can anticipate the vocabulary of every announcement. The engine has to read each announcement's elements and tailor to them.

### 1.2 Target architecture: requirement elements as the unit of tailoring

New pipeline stages, all generic, all announcement-driven:

**Stage A - Announcement parser.** Extend the existing scaffolding (`FEDERAL_SECTION_PATTERNS` ~345, `extract_it_competencies` ~1074) to itemize, not just detect:

- Split the specialized experience section into discrete requirement elements (the JD formats them as sentence-per-line or semicolon-separated; parse both, plus lettered/numbered lists).
- Capture per-grade blocks separately (GS-12 minimums vs GS-13 vs GS-14 specialized experience) so the engine knows which elements gate the target grade.
- Capture the announced competency lists (the nine IT minimum competencies and the assessed KSAs) as named items.
- Detect the target grade and the "one year equivalent to GS-X" clause.
- Fallback: if parsing yields fewer than 3 elements, fall back to the current cluster-weight behavior and print a loud build note that element-level tailoring was skipped. Never fail the build because an announcement is formatted oddly.

**Stage B - Element decomposition and term canon.** For each element, extract its atomic capability phrases (verb + object pairs: "administering... SQL Server environments," "designing... ETL processes," "developing... stored procedures") and normalize terms through a canonical-term map (new, in config): "MS SQL Server" = "Microsoft SQL Server," "T-SQL" maps under SQL, "HA/DR" expands, "contact center" groups with "call center." This map is announcement-independent and reusable across every federal JD.

**Stage C - Machine-readable evidence ontology.** This is the keystone. Today the supported-experience boundaries live as prose in AGENTS.md and RULES_FOR_CLAUDE.md ("East West supports Aptean Intuitive ownership... SQL-based validation..."; "Home Depot supports LivePerson LiveEngage... chat and text messaging workflows..."). Convert them into structured config (`config/federal_evidence.py`, shared with the commercial pipeline where useful):

- Per employer/role: a list of supported capability claims, each with: canonical capability tags, the JD-term synonyms it may be expressed with, the strongest allowed phrasing, scope facts (five sites, 150+ users, 80+ clients, 200+ reports, 60+ workshops), and date range.
- A hard `never_claim` list per capability area: SQL Server clustering/replication/failover administration, CI/CD pipeline ownership, direct quota ownership, people leadership, and the rest of the forbidden-claims list from RULES_FOR_CLAUDE.md, encoded as patterns the validator can assert are absent from any output.
- This makes Direct / Adjacent / Transferable / Unsupported classification computable instead of judgment-per-run, and it applies to every future announcement automatically.

**Stage D - Element-to-evidence matcher.** For each parsed requirement element, match its capability phrases against the evidence ontology and classify:

- Direct: a supported claim covers the capability, synonyms align.
- Adjacent: a supported claim covers a neighboring capability (DR *planning* vs DR *administration*); usable only with bridge phrasing that stays inside the supported claim.
- Unsupported: no claim covers it, or it hits `never_claim`. Recorded, surfaced, never written into the document.

Output: a per-element mapping table (element text, status, matched evidence entry, matched role/bullet reference).

**Stage E - Terminology injection.** For every Direct element, guarantee the announcement's own nouns land in a dated position block, not just the Technical Skills line (skills lists get zero qualification credit from HR specialists):

- Extend `tailor_text` / `rewrite_supported_text` to be driven by the element mapping: each evidence entry carries slot-based rewrite templates, and the injector substitutes the announcement's canonical terms where the evidence entry lists them as allowed synonyms. Example that this engine would have produced for the IRS JD automatically: Home Depot bullets rewritten to say "contact center operations," "customer interaction data," "service level" and "forecasting," because the evidence ontology marks those as allowed expressions of the LivePerson/chat/SMS analytics claim.
- Injection is constrained: only into the role the evidence entry belongs to, only with terms the entry allows, and with the one-year rule respected - if an element must be demonstrated at the target grade level, the injector prefers bullets in the most recent qualifying period when the evidence supports it there.
- Never move a claim across employers; never intensify a verb beyond the entry's strongest allowed phrasing.

**Stage F - Coverage gate and fit feedback.** New validation, run before the document is written:

- Every Direct element's canonical terms must hit at least once inside WORK EXPERIENCE text. Miss = hard build error naming the element (this is the check that would have caught all four IRS gaps).
- Every `never_claim` pattern must be absent from the full document. Hit = hard build error.
- Coverage matrix goes to the build notes: each element quoted, status, evidence location or honest non-claim. This is the per-announcement leave-nothing-to-interpretation audit.
- Unsupported-element density feeds the existing fit classification: many unsupported elements at the target grade pushes toward Stretch/Poor and the FAIL filename convention, exactly as the commercial pipeline already does. The IRS posting's DBA-heavy elements would correctly classify it as a stretch on those dimensions rather than tempting the generator to paper over them.

**Stage G - Grade-equivalence framing.** Driven by the detected grade clause: generate one framing sentence in the most recent role from evidence-ontology scope facts ("senior technical authority for enterprise systems across five sites and 150+ users, with independent responsibility for platform selection, migration risk, and delivery"). Template lives in config, facts come from the ontology, so it adapts to any grade and any future role added to source truth.

**Stage H - Competency weaving.** Map each announced competency (the nine IT minimums plus assessed KSAs) to capability tags in the ontology; validation warns for any competency whose name or close variant never appears in the document. Weave nouns into existing bullets; no bolt-on competency lists.

**Stage I - Federal Qualifications Statement rebuild.** Restructure the generator around the Stage D mapping: each specialized experience element quoted, followed by the matching dated experience narrative or an honest statement of adjacent/no experience. Suppress the generic commercial question banks (the current IRS output carries SaaS/AI interview questions that are not part of the announcement) whenever a federal JD is active. The stitched-clause CORE/SPECIALIZED paragraphs are replaced by per-element entries composed with the Part 3 sentence rules.

### 1.3 Mechanical federal rules (also system-wide)

- Salary rendering rule: no federal output may print `$0` or an empty salary (the Interim Systems Administrator block does today). Show actual pay or omit the field, enforced by a validator on every federal build.
- The federal summary is composed through the Part 3 grammar-safe assembler (its current output is grammatically broken; see 3.1).
- Keep `FEDERAL_REQUIREMENT_CLUSTERS` as the fallback scorer and as a prior for bullet ordering; requirement elements take precedence whenever Stage A succeeds.

### 1.4 Evidence intake loop (how the engine gets smarter without inventing)

When Stage D classifies an element Unsupported or Adjacent, the build notes emit a confirmation question for Christian ("Did the 200+ report portfolio include stored procedures, views, or data models? If yes, which?"). Confirmed answers update the source resumes and the evidence ontology, and every future announcement benefits. This turns the current one-off "can I claim this?" judgment into a growing, auditable evidence base. Immediate confirmations worth collecting now, because the IRS JD exposed them: SQL Server administration duties vs querying/reporting, stored procedures/views/functions/data models, backup and recovery execution vs planning, version-control usage in delivery work. Anything unconfirmed stays out of every output.

---

## PART 2: Cover Letter Reliability (System-Wide)

### 2.1 What the traces prove

`scratch/cover_letter_traces/` captures repeated hard failures followed by manual reruns: Bonterra July 1 23:03 failed on `cover letter body uses too many semicolons and reads like a stitched list instead of prose`; Foundant July 2 15:30 failed on three checks at once (`opening paragraph is 9 words; expected 16-80`, `first paragraph must name a company-specific role context`, `closing must be forward-looking and include conversation, discuss, or welcome`), then the user re-ran the build five times over 32 minutes until it passed. The retry loop is the reported "hangup."

### 2.2 Root causes

**S1 - Composer and validators share no contract, and there is no repair loop.** `build_cover_letter.py` composes once (`compose_cover_letter_proof_first_from_brief`), then runs four independent validation layers (`validate_cover_letter_text`, `cover_letter_preflight`, `enforce_prose_quality`, `assert_cover_letter_qc` plus `cover_letter_shape_issues`), any of which raises `SystemExit` (~5690-5740). The opening generator can emit 9 words while `opening_quality_problem` (~4093) demands 16-80; proof sentences lifted from resume bullets carry semicolons while `cover_letter_shape_issues` (~6174) caps them at 0-1; the closing template can omit the token that ~6129 requires. The generator rolls dice against its own referee, and when it loses, the run dies with nothing written.

**S1 - Keyword-gap noise creates false blockers.** Traces show `Resume bridge gaps: multiple: missing; impact: missing; quickly: missing; social: missing`. Generic tokens survive `build_resume.audit_keywords`, become readiness `hard_blockers`, force bridge mode (`force_bridge=True`, ~6381), and pollute every downstream consumer of the readiness report - cover letters, checklists, tracker refresh, and interview prep all read this same helper.

**S2 - Decorated role titles leak into prose.** The Foundant run's title "Associate Implementation Consultant - Strategic Advancement Focus" produced `possible JD artifact found: - Strategic Advancement Focus role centers on...`. `safe_role_title` (~1488) trims only by length and bullet artifacts, never user-added suffix decorations, so they reach filenames, prose, and resume-output lookups across all builders.

**S3 - Overlapping rules across four layers.** The same concern (weak opener, generic praise, context grounding) is checked in multiple places with slightly different regexes, so one defect yields three stacked failure messages and the 6,458-line file resists reasoning.

### 2.3 Fix plan, in dependency order

1. **Keyword stopword hardening** (shared, smallest diff, unblocks everything): extend the stopword/generic-token filter in `build_resume.audit_keywords` so adverbs and bare generic nouns ("multiple," "impact," "quickly," "social," "nonprofit" as lone tokens) can never become gap blockers. Because every builder consumes `resume_readiness_report`, this one fix cleans cover letters, checklists, tracker fit data, and interview outputs at once. Validation: rerun readiness on the Bonterra and Foundant JDs; hard_blockers must contain only real requirement terms.
2. **Role-title normalization at JD ingestion** (shared): strip " - Suffix" decorations and parenthetical focus labels at the single point where the JD is parsed, using the heuristic that a suffix absent from the JD body or matching decoration words (Focus, Track, Urgent, Remote) is not part of the title. All filenames, prose, lookups, and tracker rows inherit the clean title. Validation: rebuild Foundant; zero JD-artifact warnings.
3. **Single validation-rules registry** (shared): move every hard QC constant and rule (word ranges, required closing tokens, semicolon/colon caps, banned phrases, paragraph counts per mode) into one registry module that the composer templates AND all four validator layers import. The composer is then constructed against the same constants that judge it, eliminating the mismatch class rather than instances. The registry also becomes the natural home for the federal coverage-gate rules from Part 1, so resume and cover validation converge on one mechanism.
4. **Deterministic repair loop before failing** (cover letters now, reusable by other prose outputs later): after composition, run QC; for each failure apply the registered mechanical fixer and re-validate, up to 3 passes. Fixers: expand a short opening with the already-computed company/role context sentence; split semicolon-joined clauses into sentences; swap the closing for an approved forward-looking close from the bank; deduplicate thesis sentences. If repairs cannot converge, write a `DRAFT`-suffixed docx plus the trace instead of raising SystemExit with nothing, so a human finishes a 90% letter instead of rerunning a black box.
5. **Consolidate the four validation layers** behind the registry so each rule runs once and each failure message names its rule ID. Keeps behavior, removes duplication.

---

## PART 3: Natural-Sounding Content (System-Wide)

### 3.1 The core defect: fragment stitching without a grammar check

Builders assemble sentences by splicing phrase-bank fragments (`join_phrases` over cluster `summary_phrase` values and similar banks) and no structural check runs after assembly. The live IRS summary, produced by `build_gs14_summary` (~1569-1605), shows the signature:

> "...12+ years delivering implementation, enterprise systems, and technology delivery and recent senior-technical-authority scope across multi-site manufacturing, SaaS, eCommerce, legal technology environments."

Three defects in one machine-assembled sentence: "delivering... delivery" redundancy, a double-"and" chain, and a serial list missing its final "and." Sentence two stacks "includes A and B, C, and D backed by..." The Federal Qualifications Statement CORE and SPECIALIZED sections repeat the pattern, and the commercial summary and cover letter composers use the same splicing approach. Recruiters primed to spot AI text read exactly this: grammatical near-misses, abstraction chains ("risk-aware cross-functional coordination," "acquisition-ready requirements documentation," "senior-technical-authority scope"), uniform rhythm, and repeated content (the East West block says "de facto product owner for Aptean Intuitive" in two separate bullets).

`config/language_rules.py` bans words (spearheaded, robust) but not syntax. The system filters vocabulary while generating structures no human writes.

### 3.2 Fix plan (all in shared modules, so every output inherits)

1. **S1 - Grammar-safe sentence assembler** in `scripts/utils.py`, used by every builder that composes prose (federal summary, commercial summary, cover letters, qualifications statements, checklist narratives): one list per sentence maximum; Oxford comma with mandatory final "and"; hard cap of one coordinating "and"-chain per sentence; ~28-word sentence cap; and the key rule - a fragment that is itself a list may never be embedded inside another list. Any builder currently calling `join_phrases` inside an f-string migrates to this helper.
2. **S1 - Structural AI-tell checks in `writing_eval.py`** (automatically inherited by every output through `enforce_prose_quality`): double-conjunction chains (three "and"s in one sentence), serial lists missing the final conjunction, hyphenated modifier chains of 3+ words, repeated opener verbs on consecutive bullets (the Aptean block opens two straight bullets with "Owned"), and near-duplicate phrase detection within a role block (catches the doubled "de facto product owner"). Warn on prep outputs, fail on sendable outputs, matching the existing enforcement split.
3. **S2 - Phrase banks become full sentences with typed slots.** Rewrite `FEDERAL_REQUIREMENT_CLUSTERS` summary/qualification phrases, the commercial summary banks, and the cover letter proof/opening/closing banks as complete human-written sentence templates with a small number of typed slots (metric, platform, scope, term-from-JD). Assembly becomes slot-filling, so every possible output sentence was once written and read by a human. This is also what Stage E of the federal engine needs: evidence entries carry slotted templates, and JD-term injection fills the term slot.
4. **S2 - Rhythm variation rules** in the registry: summaries must contain at least one sentence under 15 words; consecutive bullets in a role must not share an opening verb; bullet lengths within a role must vary by at least 20%. Short declarative sentences are the cheapest human signal available: "Owned the ERP platform for five plants. Kept it stable through a migration and a reorganization."
5. **S3 - Ban the abstraction-chain register** in `config/language_rules.py`: flag any 3+ word hyphenated modifier ("senior-technical-authority," "risk-aware cross-functional") for rewrite into plain agent-verb-object language ("acted as the senior technical authority for...").
6. **S3 - Keep the two-pass human loop.** After the structural fixes land, `claude-packet --mode resume` and `--mode cover` reviews on regenerated outputs remain the final naturalness gate. Mechanical checks catch machine syntax; packet review catches tone.

The top-1% positioning does not need new claims. Five-site ERP ownership through a migration and a reorganization, 80+ international clients, 200+ reporting tools, 60+ executive sessions - the differentiator work is making these facts read like a person stating what happened. Nothing in this plan adds an unsupported claim, and the federal engine makes unsupported claims mechanically impossible to emit (Stage F `never_claim` gate).

---

## PART 4: Implementation Order, Validation, Regression

Ordered so each step de-risks the next; every step ends with `scripts/smoke_test.py` plus the named validation.

1. **Keyword stopword fix** (2.3.1). Validate: Bonterra/Foundant readiness shows only real terms.
2. **Role-title normalization at ingestion** (2.3.2). Validate: Foundant rebuild, zero artifact warnings; filenames clean.
3. **Grammar-safe assembler + structural writing checks** (3.2.1, 3.2.2). Validate: regenerate IRS federal summary and one commercial resume; zero structural findings; two-page fit preserved.
4. **Validation-rules registry** (2.3.3) and migrate cover letter validators onto it. Validate: behavior-identical run on last five JDs (traces compare equal except rule IDs).
5. **Cover letter repair loop + DRAFT fallback** (2.3.4). Validate: replay Bonterra and Foundant compositions; both must converge without manual reruns.
6. **Evidence ontology config** (Stage C) encoding AGENTS.md supported-experience boundaries and the never-claim list. Validate: smoke assertions that each employer's entries load and never-claim patterns compile.
7. **Federal announcement parser + element matcher** (Stages A, B, D). Validate: parser itemizes the IRS posting into 15 specialized elements, 9 minimum competencies, 14 assessed competencies; matcher classifies with zero Unsupported items claimed.
8. **Terminology injection + coverage gate + grade framing + competency weaving** (Stages E-H). Validate: regenerate IRS resume; coverage matrix shows every Direct element hit inside WORK EXPERIENCE; never-claim gate passes; `$0` salary gone; two-page fit holds.
9. **Federal Qualifications Statement rebuild** (Stage I). Validate: per-element mapping present; commercial question banks absent on federal runs.
10. **Regression harness**: golden-JD corpus (Bonterra, Foundant, Tyfone, Deel, IRS, plus one per commercial lane and one additional federal announcement from `scratch/jd_library/` if available) running compose + validate end to end for resumes and cover letters, asserting zero hard failures, zero never-claim hits, zero structural prose findings. Wire into pre-commit or `run_resume_workflow.py`.
11. **Phrase-bank rewrite to slotted full sentences** (3.2.3) last, behind the regression harness so tone changes cannot break shape rules unnoticed.

## PART 5: Confirmations Needed From Christian (blocking items only)

These gate specific evidence-ontology entries; everything else proceeds without input:

1. Did SQL work at East West or Aderant include administration duties (configuring, monitoring, tuning SQL Server instances), or only querying, validation, and reporting?
2. Did the 200+ report portfolio involve stored procedures, views, functions, or data modeling? Which?
3. Was backup/recovery at Aderant executed hands-on, or planning and documentation only?
4. Was version control (Azure DevOps/TFS or other) used in your own delivery work, and how?

Unconfirmed items stay out of the ontology and therefore out of every output, permanently and automatically.
