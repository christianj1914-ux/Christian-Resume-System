# Codex Packet: system-wide document-quality fixes

Review-pass findings plus fix plans for issues surfaced while auditing the 2026-07-18 outputs
(CreatorIQ resume, Randstad resume/cover/qualifications). Scope is system-wide: fix the
generators and source data, not the individual output files. Two items are already done as
source/data edits and are noted as such.

## OUTSTANDING WORK - current implementation order (start here; supersedes the first-pass sequence below)

MASTER SEQUENCE NOTE: after the 20-run analysis, the authoritative end-to-end order lives in
`ANALYSIS_20run_completion_and_tailoring.md` ("Master sequence for Codex"). It reconciles the F items
below with the new S1-S5 findings (S1=F10, S2=F8 correction, S4=F5 finished, S5=F2 finished, plus S3
keyword tailoring). Use that master sequence as the driver; the F sections below (especially F6, F7,
F10, F11) remain the detailed reference.

Status: F0-F5 and the interview expansion (Items A-G) are committed. The "Recommended implementation
sequence" section below is historical (first pass). Run all outstanding items, in this priority order:

1. NOW, unblock strong-fit builds. F10 step 0: demote the F4 summary rules
   (SUMMARY_SENTENCE_TOO_LONG, SUMMARY_PREPOSITION_PILEUP, and any total-length rule) from FAIL to
   WARN, shipped as its own small commit. This alone stops the hard failures blocking implementation
   and RevOps/analytics resumes (3 of the last 4 builds hard-failed here). See F10.
2. Commit the outstanding source content. The `source/*.docx` edits from this session (degree fix,
   tightened and new bullets, keywords, core training, PMP-in-progress) are uncommitted; commit them
   as a focused content commit. Do not commit gitignored `output/` files.
3. F10 full repair. Convergent per-rule repairs, extend the builder dedup to "to X ... for Y",
   pre-split the hard-coded long `optimized_role_summary` sentences, then re-promote the rules to
   FAIL only once the per-lane golden summaries pass. Fold in the PROSE_NESTED_LIST underlying
   convergence fix (`CODEX_PACKET_prose_nested_list.md`), same class; the East West content stopgap
   can then be retired or kept as harmless.
4. Polish, any order: F6 (label pre-tailoring vs final score, state the real FAIL reason), F7
   (document the cover DRAFT-vs-fallback decision), F8 (make the DRAFT-vs-FAIL gate consistent and
   stop recording a FAIL as a clean tracker row), F9 (weave a supported role specialty into the cover
   so specificity passes on merit).
5. Robustness (F11): add the source-content lint (catch first-person, overload, placeholder, cliche,
   duty-only across all source bullets upfront) and generalize the convergence guard so no FAIL prose
   rule on any artifact can hard-crash a build. The lint runs with step 2; the guard lands with step 3.

Guardrails throughout: Word-only (no PDF), F3 bullet checking stays detect/report-only, no invented
experience (certs out except PMP-in-progress), preserve the dirty tree, and every slice ends green on
`python scripts/smoke_test.py` plus `python tasks.py validate` plus a live build.

## Recommended implementation sequence (verified with repo owner)

1. Fix F1 (cover opener) + F2 (qualifications generator) + F0 guards (purge stale
   `scratch/christian_resume_*/fit_candidate.docx` caches and add a degree smoke assertion).
   These are the high-priority correctness bugs.
2. Add F3 bullet coverage as DETECT / REPORT ONLY (warn in Resume Notes). No auto-repair in this
   pass.
3. Handle F4 (summaries) and F5 (cover letter quality) as a separate, later pass, audit-first:
   prove the failure patterns with golden tests before changing any templates. Do not bundle
   F4/F5 with F1/F2.

Hard constraint: do NOT add any PDF-generation behavior while working in this area. Repo rule is
polished Word (.docx) outputs only. Nothing in this packet introduces PDF generation; keep it
that way. (The one-off PDFs produced during the audit were manual conversions for an active
application, not generator behavior.)

## Implementation guardrails and exact pointers (review pass)

Precise locations and traps confirmed by re-reading the repo. Read this before implementing.

F2 roots are both in `scripts/question_prep.py` (single file):
- Descriptor-as-subject: line ~1072,
  `f"{company} is the kind of {employer_type} environment where {problem_phrase} directly shapes the work."`
  The gerund lane phrase is inserted into a subject slot here. Also drives the "Why are you
  interested" answer, so fix and TEST that answer too, not only the five recent-interview answers.
- Bare-number proof slot: lines ~1089 and ~1091,
  `f"A concrete proof point is {brief.top_proof_anchors[0]}."` /
  `f"A concrete proof point is {brief.strongest_direct_proofs[0]}."`
  The Randstad "200+" came from an anchor that was a bare number. Require the anchor to carry its
  noun (for example "200+ dashboards") or drop the sentence; do not just suppress the literal.

F0 guardrail: the degree smoke assertion must target only the Master's line. The bachelor's is
legitimately "Bachelor of Business Administration, Management Information Systems", so any check
that forbids "Management Information Systems" outright will false-positive on the BBA. Assert
specifically on the "Master of Science, ..." line.

F3 guardrail: the new `bullet` check must be a pure report path that appends to Resume Notes. Do
NOT wire it through the converge-or-fail `repair_text(...); if not converged: fail(...)` pattern
used for role summaries, or a flagged bullet will hard-fail a build.

F1 note: hardening `jd_concrete_hook` at the function covers both use sites (the opener at line
~3232 and "The work centers on ..." at line ~3245). Fixing the function is the right approach;
the opener regression should assert both are clean.

Cross-dependency (do not lose): the PROSE_NESTED_LIST repair-convergence bug in
`CODEX_PACKET_prose_nested_list.md` also HARD-FAILS resume builds and is currently patched only
by an uncommitted worktree stopgap (the East West "decision" summary split in
`scripts/resume_content.py`). Preserve that uncommitted edit (see Assumptions) and schedule the
underlying repair fix, or decision-anchored JDs like CreatorIQ will fail to build again.

Testing: run the full `scripts/smoke_test.py` suite, not just `python tasks.py validate`. F1/F2/F3
touch shared prose and summary code with existing assertions (PROSE_NESTED_LIST around
smoke_test.py:5155, the Aptean summary around smoke_test.py:8925) that the suite is meant to catch.

## F0 (DONE, data) Degree title wrong in the Pre-Sales source resume

Root cause: the education line is carried from the per-lane source resumes in `source/`, and
the Pre-Sales/CSM source had the wrong master's title.

- `source/Estrada_Resume_PreSales_CSM.docx` read "Master of Science, Management Information
  Systems". Correct title is "Master of Science, Information Systems".
- `source/Estrada_Resume_Implementation.docx` and `source/Christian_Estrada_KPMG_Final_Tightened_EdFix.docx`
  were already correct.

Applied: the Pre-Sales source docx now reads "Master of Science, Information Systems" (the BBA
line, correctly "Management Information Systems", was left unchanged). Validated with the docx
skill validator.

Follow-up for Codex:
- Purge stale cached copies so no regenerated resume reintroduces the old title:
  `scratch/christian_resume_*/fit_candidate.docx` still contain "Management Information Systems".
- Consider making the education block a single canonical constant (one string used by every
  lane and by `build_federal_resume.py`) so the three source docs cannot drift again. Add a
  smoke assertion that every rendered resume contains exactly "Master of Science, Information
  Systems" and never "Master of Science, Management Information Systems".

## F1 (High) Cover letter opener can splice raw JD text into a broken sentence

Symptom (Randstad cover letter): the opener rendered as
"Randstad is hiring a Solutions Delivery Consultant to project Expertise. Demonstrated
experience managing large, complex accounts or projects, as well as describing and documenting
project or client requirements."

Root cause: `scripts/build_cover_letter.py`
- `jd_concrete_hook(job_description)` (def at line ~3175) scans JD lines, scores them, strips a
  few lead-in patterns, and returns the highest-scoring line more or less verbatim.
- It is inserted at line ~3232: `f"{company_name} is hiring {with_indefinite_article(role_title)} to {concrete_hook}."`
  and again at ~3245 `f"The work centers on {concrete_hook}."`

The hook is not constrained to a single clean clause: it can contain a sentence boundary
(a period, so the template sentence runs on into a second sentence), can begin mid-phrase
("to project Expertise"), and is not verb-led. Any of those produces an incoherent opener.

Fix plan:
- Constrain `jd_concrete_hook` to return one clean, verb-led clause: cut at the first sentence
  boundary, reject candidates that do not start with (or cannot be coerced to) an infinitive
  verb, strip trailing subordinate fragments, and enforce a max word count.
- If no candidate qualifies, fall back to the existing
  `build_resume.natural_problem_phrase(...)` path (already the final fallback) rather than
  emitting a raw line.
- Run the result through `prose_engine.repair_text(..., "cover")` / an assertion that the
  assembled opening sentence has exactly one sentence and starts with a lowercase verb.

Regression: add a case asserting the Randstad JD (archived snapshot
`20260718_215753_Randstad_Solutions_Delivery_Consultant_5d0064cc`) produces a single-sentence,
verb-led opener with no interior period.

## F2 (High) Qualifications statement embeds a lane phrase ungrammatically, duplicates answers, and leaves a dangling proof slot

Symptoms (Randstad qualifications statement):
1. The analytics_operations lane descriptor, "systems, data, and workflow questions turning
   into decisions people can use", is dropped into slots that expect a noun, e.g. "Randstad is
   the kind of ... environment where systems, data, and workflow questions turning into
   decisions people can use directly shapes the work" and "the need to solve systems, data,
   and workflow questions turning into decisions people can use". The phrase is a gerund clause
   and reads as broken everywhere it is used as a subject/object.
2. Two different questions ("Are there specific product offerings you specialized in?" and
   "Who is the target audience and what is the business value?") rendered word-for-word
   identical answers.
3. A dangling slot: "A concrete proof point is 200+." (number with no noun).

Root cause locations:
- Lane descriptors: `scripts/question_prep.py` lines ~344-360 (and mirrored in
  `build_interview_cheat_sheet.py` ~640). These are fine as predicates ("...is about X") but
  are being inserted as noun phrases by the qualifications templates.
- Answer rendering: `scripts/build_standard_qualifications_statement.py`
  - "why interested" / relevant-experience builders around lines 129-194
    (`relevant_experience_answer`, `generic_bridge_answer`).
  - Recent-interviewer renderer at line ~243, which calls
    `question_prep.interviewer_question_factual_script(prompt, jd, resume_text)` for non-story
    categories. That factual-script function returns the same generic body for distinct prompts
    (the duplication) and is where the lane phrase and the "concrete proof point is {number}"
    slot get assembled.

Fix plan:
- Make the lane descriptor grammatical in context: either wrap it in a fixed carrier ("turning
  <descriptor> into decisions people can use" should become a clause like "helping teams turn
  <short-noun> into decisions they can use"), or add a noun-form variant of each lane
  descriptor and use that in subject/object slots. Do not concatenate the gerund clause where a
  noun is required.
- De-duplicate `interviewer_question_factual_script`: branch on the prompt so "product/systems
  specialized in" and "target audience / business value" produce distinct answers. Add a guard
  that rejects identical rendered answers for two different prompts in one document.
- Fix the proof slot: never emit "A concrete proof point is {number}." with a bare number.
  Require the proof noun (for example "200+ SQL and Power BI dashboards"); if the noun is
  missing, drop the sentence.
- Route every generated answer through `prose_engine.spoken_register(...)` (some already are)
  and assert no answer contains the raw descriptor phrase as a standalone subject.

Regression: for the Randstad snapshot, assert all five interview answers are pairwise distinct,
contain no "A concrete proof point is <number>." pattern, and none contains the substring
"questions turning into decisions people can use" used as a sentence subject.

## F3 (Medium) Overloaded resume bullets are never structurally validated (plan)

Context: the prose validator only runs on the artifacts `{"summary","cover","spoken"}`
(`prose_engine.VALIDATION_RULES`). Resume bullets bypass it, so bullets like the East West
migration line ship unchecked:

"Reduced migration and audit risk from Aptean Intuitive to Epicor Kinetic by extracting,
querying, transforming, updating, and validating system/database records through ETL tools,
SQL checks, user access reviews, control validation, cutover coordination, and least-privilege
permission tightening after incident backtracking tied avoidable work-order losses to access
mistakes."

That single bullet stacks a five-verb chain, a six-item comma list, and a trailing cause clause
that is hard to parse.

Scope decision (verified with repo owner): DETECT / REPORT ONLY in the first pass. Resume
bullets flow through the provenance content model and are source-backed claims, so silent
auto-repair risks changing what the resume asserts. Do not auto-repair bullets in this pass.

Plan (detection, this pass):
- Add a `"bullet"` artifact and one or more density rules to `prose_engine`, for example
  `BULLET_OVERLOADED` firing when a bullet exceeds a word cap (about 34-40 words) OR has a
  leading verb chain of 4+ coordinated verbs OR has 5+ commas. Ship at severity `warn` only.
- Surface any flagged bullets in the "Audit Notes" block of the Resume Notes (same place the
  keyword-gap notes already appear) so overloaded bullets are visible before submission.
- Do NOT hook any repair into bullet rendering. The check reports; a human decides.

Plan (repair, DEFERRED to a later pass, not now):
- Only after the warn data shows the pattern is safe to automate, consider a trim-first repair
  (drop a trailing subordinate cause clause, collapse the longest list to 2-3 items) reusing the
  nested-list splitter from `CODEX_PACKET_prose_nested_list.md`. Never silently alter a
  source-backed claim; any repair must be reviewable.

Plan (validation, this pass):
- Regression cases asserting the East West migration bullet and the CreatorIQ ETL bullet are
  FLAGGED by the new warn rule (detection correctness), not repaired.
- A report check: the Resume Notes list every bullet over the thresholds.
- Manual stopgap already applied: the worst offenders in the two active-lane source resumes were
  tightened by hand so live resumes read cleanly before the rule lands.

## Already delivered alongside this packet

- Degree corrected at source (F0) and in the already-submitted CreatorIQ resume docx + PDF.
- Clean, submittable Randstad cover letter and qualifications statement (docx + PDF) were
  hand-built as a stopgap; they do not depend on F1/F2 and can be used now. F1/F2 are still
  needed so the generator stops producing broken versions.
- Overloaded source bullets tightened in `source/Estrada_Resume_PreSales_CSM.docx` and
  `source/Estrada_Resume_Implementation.docx` (ETL/migration, product-owner, SMS bullets),
  preserving facts and keywords. This is the F3 manual stopgap; the F3 generator rule is still
  needed.

## F4 (Medium) Professional and role summaries run long and clumsy (plan)

Important framing: professional summaries are NOT read from the source resumes. They are
regenerated per build by `resume_content.build_problem_first_summary` (resume_content.py:2179)
and written in by `rewrite_professional_summary_for_role` (2262). Role summaries are generated
by `optimized_role_summary`. So summary tightening is a generator change; editing source-file
summaries (including the KPMG source) changes nothing in output.

Observed defects:
- The professional summary is assembled as positioning + optional woven context + proof +
  close. The positioning-plus-context join (lines ~2195-2203) can stack two prepositional
  phrases into one sentence, which produced the CreatorIQ run-on: "...for enterprise software
  evaluations built to stay credible once implementation began for cloud software and B2B
  enterprise buyers." `woven_context_clause` also emits heavy relative clauses.
- `ensure_summary_minimum_words` (line 2207) enforces a minimum length that fights any
  tightening and can re-pad.
- The prose "summary" validator catches conjunction chains and nested lists but not sentence
  length or the double-preposition pileup, so overlong-but-not-nested summaries pass.

Plan:
1. Detection first. Add a summary rule to `prose_engine`: warn when any sentence exceeds ~30-34
   words, when the whole summary exceeds ~65-70 words, or when one sentence stacks 2+ "for"/"to"
   prepositional phrases. Ship at `warn`, then audit by regenerating summaries across the
   archived JD snapshots (one per lane) and logging word counts and flags to set thresholds
   from real data.
2. Fix construction. Dedupe prepositional phrases in the positioning-plus-context join so
   "for X ... for Y" cannot occur; if positioning already names the audience, drop the
   context's "for ... buyers"; cap the combined first sentence and split context into its own
   short sentence when over cap. Simplify `woven_context_clause` to a crisp trailing phrase.
   Convert `ensure_summary_minimum_words` from a hard floor to a target range (about 45-70 words
   across 2-3 sentences). Apply the same discipline to `startup_operator_summary`,
   `consulting_story_summary`, and `optimized_role_summary`.
3. Enforce. Route composed summaries through the nested-list splitter (from
   CODEX_PACKET_prose_nested_list.md) so an over-long first sentence splits at a clause boundary
   instead of shipping, then promote the length rule from warn to fail.
4. Validate. Golden tests for one archived JD per lane (presales_solution, customer_success,
   change_enablement, analytics_operations, corporate_strategy, implementation_delivery):
   assert the summary is within the word target, no sentence over the cap, no double-"for", and
   still contains its required proof anchors (200+, $1M+, 80+, 60+). Keep existing summary
   prose-repair smoke assertions green; read one regenerated resume per lane by hand.

## F5 (Medium) Cover letter quality beyond the broken opener (plan)

Builds on F1 (opener). The Randstad letter also had a near-empty body and internal lane-name
jargon in the prose. Generator: `scripts/build_cover_letter.py`, producing a CoverLetterModel
(opening, body_paragraphs, closing).

Observed defects:
- Thin body: proof selection surfaced a single stray line rather than 2-3 substantive
  paragraphs. Under-fills when lane-term hits are low for the JD (as with the staffing JD),
  via `proof_selection_score` / `select_opening_support_sentence` / paragraph assembly.
- Lane-name jargon rendered as English: "the role-based enablement and adoption work and
  consulting and structured problem solving this role calls for" (lane focus labels concatenated
  into a sentence template around `focus_by_lane` / `cover_lane_terms`).
- Generic close, no company-specific hook.
- No honest bridge sentence for BRIDGE/FAIL fits, even though the resume notes flag bridge gaps
  to "address in the cover letter."

Plan:
1. Guarantee body substance. Require 2-3 body paragraphs, each anchored to one JD requirement
   cluster and one distinct proof point, deduped. If proof selection under-fills for a low-hit
   JD, fall back to the candidate's canonical proofs (200+ dashboards, 60+ QBRs, 78%/22%
   process improvement, $1M+ recovery, five-site ownership) mapped to the nearest JD themes,
   instead of emitting one stray line.
2. Kill lane-name leakage. Never render lane keys or internal focus labels as prose. Replace the
   "background lines up with the {focus} this role calls for" template with a natural sentence
   built from JD nouns, and add a lint that rejects any cover paragraph containing internal
   tokens (presales_solution, change_enablement, "role-based enablement and adoption work", etc.).
3. Add a real hook. Open with a concrete company or role specific drawn from the archived
   company research (`jobs/company_notes`, `jobs/company_research.txt`) or the JD, with a safe
   fallback.
4. Honest bridge sentence. When the resume notes flag bridge gaps, generate one honest sentence
   that names the adjacent gap and frames transferable strength (as done by hand in the Randstad
   draft), instead of overclaiming.
5. Enforce prose quality. Run every paragraph through `prose_engine` "cover" repair, add the
   length/double-preposition rule from F4, and add a structural check: exactly one opening, 2-3
   body paragraphs, one closing, opener a single verb-led sentence (ties to F1).

Validation:
- Golden tests for 3-4 archived JDs (including the Randstad snapshot and a strong-fit one):
  opener is a single coherent sentence, body has 2-3 paragraphs each with a distinct proof, no
  internal lane tokens present, and a company-specific reference exists.
- Keep existing cover smoke assertions green; read one letter per lane by hand.

Sequencing for F4 and F5: two-pass, per repo workflow. Review pass adds the detection rules and
lints and runs the audit across archived JDs; plan pass finalizes thresholds and templates;
implementation pass hands builder changes plus golden tests to Codex to run against the smoke
suite.

## F6 (Low, messaging) Audit output contradicts itself on a FAIL that clears the alignment floor

Observed on the BELAY - Assistant Solutions Advisor run (a genuinely weak/adjacent fit). The
output is not wrong, but it reads as contradictory and confusing:

- Two different alignment numbers in one run: the pre-build gate prints "Alignment Score: 89/115 -
  Adjacent Fit" (which drives the gate action), and the post-build audit prints "Alignment score
  is 90/115. This clears the fail floor." The 1-point gap is the pre-tailoring vs final-resume
  score (the build removed 25 role bullets and reordered), but nothing labels them as such. The Hard Rock Digital run makes this more
  consequential: the gate printed "84/115 - Stretch Fit" (below the 86 floor, "treat as FAIL"),
  while the post-build audit printed "86/115. This clears the fail floor." That 2-point tailoring
  swing crossed the fail-floor boundary, so the gate advice and the final status disagree on
  whether the resume even clears the floor.
- "Final audit: FAIL" appears right next to "This clears the fail floor." The FAIL is driven by
  keyword-placement and job-language checks (executive-level missing; "business" and "development"
  buried in Skills only; weak summary/top-section keyword hits), not the alignment floor
  (`build_resume.py` around lines 3644-3670, where a FAIL can stand with
  `total_score >= ALIGNMENT_FAIL_FLOOR`).

Fix (messaging only, no scoring change):
- Label the two scores: "pre-tailoring alignment 89" for the gate and "final alignment 90" for the
  audit, so the delta is legible.
- When status is FAIL but alignment clears the floor, print a one-line FAIL reason that points at
  the actual gate ("FAIL: alignment clears the floor at 90, but keyword-placement/job-language
  checks did not pass, see notes") rather than leaving "clears the fail floor" next to "FAIL".

## F7 (Low, decision) Cover-letter DRAFT on low-overlap JDs: fallback vs intended gate

Same BELAY run: the cover letter saved as DRAFT with "Proof paragraph is too short to carry
evidence weight" and "fewer than 4 job-description keyword hits", then the workflow stopped by
design. For a genuinely weak-fit JD this is arguably correct behavior. But F5's plan called for a
canonical-proof fallback to guarantee a substantive proof paragraph. Decide and document which
wins: either the F5 fallback fills the proof paragraph to weight even on low-overlap JDs (so the
DRAFT is driven only by keyword hits, not thinness), or the short-proof DRAFT gate is intended for
weak fits and the fallback should not fake substance. Recommend the latter for integrity, but make
the behavior explicit so it is not read as an F5 gap.

## F8 (Medium, workflow consistency) DRAFT halts the workflow but FAIL proceeds and adds a tracker row

Observed across two runs. BELAY: the cover letter came out DRAFT and the workflow stopped, skipping
qualifications and the tracker ("excluded from downstream builders and tracker updates"). Hard Rock
Digital: the resume and cover letter both came out FAIL, yet the workflow continued, built the
qualifications statement, and added an application-tracker row. Only "DRAFT" is gated
(`run_resume_workflow.py:588`, the regex matches `Final audit: DRAFT`); a FAIL audit is not, so
`run_tracker_auto_add()` runs. The result is backwards: a FAIL, which is not better than a DRAFT,
gets more downstream processing and a clean-looking tracker entry, while a DRAFT halts. It also
contradicts the gate's own advice ("evaluate before applying; consider better-fit roles before
investing full preparation time"). A third run sharpens the inconsistency: the APC - AI Technical
Project Manager cover hit the SAME "Proof paragraph is too short to carry evidence weight" preflight
that made BELAY a DRAFT, but APC came out FAIL and continued (added a tracker row), while BELAY
(which additionally hit "fewer than 4 job-description keyword hits") became DRAFT and halted. So the
same proof-too-short warning gates differently depending on the keyword-hits preflight, and the
DRAFT-halt trigger is really the keyword-hits check, not proof length. Make the DRAFT-versus-FAIL
trigger explicit and consistent.

Fix (decision plus consistency): reconcile the downstream gating so DRAFT and FAIL are handled
coherently. Either treat a FAIL resume or cover the same as DRAFT (stop downstream, do not auto-add
a tracker row), or continue but stamp the tracker row with the FAIL/STRETCH fit status and a
"needs work before submission" flag so a stretch application is not recorded as a clean one. At
minimum, do not process a FAIL more eagerly than a DRAFT.

## F9 (Medium, extends F5) Cover specificity fails even when the candidate supports the listed specialty areas

Hard Rock run: "SPECIFICITY WARNING: Cover letter does not reference any of the role's specialty
areas: data analysis, cross-functional delivery, reporting." All three are areas Christian genuinely
has, yet the generated cover referenced none of them. The specificity test correctly failed, but the
generator did not weave in a role specialty the candidate can support. Refinement (extends F5): when
building the cover body, intersect the JD's specialty areas with the candidate's supported evidence
and ensure at least one supported specialty appears in the letter, so the specificity test passes on
merit rather than being left as a warning. Do not insert unsupported specialties (gaming and
administering stay in bridge notes).

## F10 (HIGH, build-breaker) F4 summary FAIL-rules do not converge and hard-fail the build

Do this one first. Same class as the old PROSE_NESTED_LIST convergence bug, now inside the shipped
F4 summary work, and confirmed across TWO different F4 rules on two strong-lane roles:
- Direct Travel - Senior Technical Implementation Consultant:
  `SystemExit: Commercial model summary repair did not converge. Rule IDs: SUMMARY_PREPOSITION_PILEUP`.
- ADP - Senior Implementation Consultant:
  `SystemExit: Commercial model role-summary repair did not converge for East West Manufacturing.
  Rule IDs: SUMMARY_SENTENCE_TOO_LONG` (the East West role-summary first sentence is 39 words, over
  the 34-word cap; the repair cannot split it to convergence).
- Toast - Senior Analyst, RevOps/GTM Analytics: `SUMMARY_PREPOSITION_PILEUP` again.

Frequency note: across the last four commercial builds, F10 hard-failed three (Direct Travel, ADP,
Toast) and only one (APC, which happened to generate an analytics-framed summary) slipped through.
It spans both the implementation and analytics/RevOps lanes. This is the dominant blocker now, not
an edge case, which is why step 0 (demote to WARN) should ship before any other packet item.

Root cause is a sequencing violation of the original F4 plan: the summary quality rules were
promoted to FAIL severity, but the builders and repairs were NOT made robust enough first, so the
"promote to fail only once the per-lane golden summaries pass" precondition was skipped. The
generators still emit over-length and pileup summaries (the hard-coded `optimized_role_summary`
branches in `resume_content.py` include 39-plus word single sentences), and the repair reuses
CLAUSE_DENSITY_REPAIR, which cannot reliably resolve either a preposition pileup or an over-length
sentence, so `repair_text` never converges and `build_resume.py` calls `fail()`.

Mechanism (reproduced):
- The generated summary stacks prepositional phrases, e.g. "...driving software delivery and
  process standardization to raise adoption confidence and data reliability across day-to-day
  operations for cloud software and B2B enterprise buyers" (a "to ... for ..." pileup).
  `_double_preposition_pileup` (`scripts/prose_engine.py:163`) flags it, and the rule is FAIL
  severity (line 239).
- The repair reuses CLAUSE_DENSITY_REPAIR (the semicolon / and-chain / nested-list splitter), which
  is not built for preposition pileups. On one variant it "converges" only by producing a broken
  fragment ("...software delivery. Process standardization to raise adoption confidence..."); on
  another summary variant it cannot reduce the pileup at all, so `repair_text` never converges and
  `build_resume.py` calls `fail()`, hard-stopping the whole build.

Fix, in order:
0. Immediate unblock (do first): demote the F4 summary quality rules (SUMMARY_SENTENCE_TOO_LONG,
   SUMMARY_PREPOSITION_PILEUP, and any total-length rule) from FAIL to WARN so no summary quality
   issue can hard-stop a build. This restores pre-F4 behavior (summaries never blocked builds) while
   still surfacing the signal in Resume Notes, and it unblocks strong-fit roles like Direct Travel
   and ADP right now.
1. Repairs: give each summary rule a dedicated, convergent repair, split an over-length sentence at
   a clause boundary into grammatical sentences (no fragments), break a for/to pileup at a
   preposition boundary; guarantee idempotence and convergence. Add the same non-convergence guard
   the PROSE_NESTED_LIST fix uses.
2. Builders/source: stop generating the offenders. Extend the F4 builder dedup to cover "to X ...
   for Y" pileups, and pre-split the hard-coded long single sentences in the `optimized_role_summary`
   branches (`resume_content.py`) and `build_problem_first_summary` so no generated summary sentence
   exceeds the 34-word cap.
3. Only re-promote the rules to FAIL once the per-lane golden summaries all pass (the precondition
   that was skipped the first time).

Tests: for every lane and every summary variant, generated professional and role summaries converge
to a grammatical result with no sentence over the cap and no fragment; assert no summary rule at FAIL
severity can leave `repair_text` non-convergent (mirror the PROSE_NESTED_LIST regression guard);
include the East West role summary and the Direct Travel professional summary as explicit cases.

## F11 (Medium, robustness) Validate source content upfront, and guarantee no FAIL rule can crash any artifact

Two recurring-issue classes this session surfaced only reactively (when a specific JD happened to
select the offending content), which makes them look like random failures. Close them at the root:

1. Source-content lint. The content-quality checks (first-person, placeholder, cliche, AI-writing,
   duty-only opener, and the F3 bullet-overload rule) currently run only on the rendered resume
   during a build, so a bad source bullet surfaces only when a JD selects it, e.g. the ADP
   first-person "customizations I proposed", and the overloaded bullets that appeared one at a time
   across BELAY, Hard Rock, and APC. Add a lint that runs these checks across every bullet in the
   `source/*.docx` resumes (a `tasks.py` subcommand and/or a smoke test) so content issues are caught
   once, at the source, not per-JD. Run it after the source-content commit and fix anything flagged.
   Implementation note: inspect the actual DOCX bullet paragraphs and reuse the existing helpers
   (`contains_first_person()`, the cliche/placeholder/AI-writing/duty-only checks, and
   `prose_engine.validate_text(..., "bullet")`); do NOT run raw regexes over flattened resume text,
   which misclassifies company-context paragraphs and false-positives uppercase "US" as
   first-person "us". Expect the lint to surface more than the one first-person bullet (possibly
   cliche/AI-writing/overload in the newer bullets), so budget a short follow-up content fix.
2. Generalized convergence guard. F10 fixes summary-rule non-convergence and adds a guard for it.
   Generalize the invariant: assert that NO prose rule at FAIL severity, on ANY artifact (summary,
   cover, spoken), can leave `repair_text` non-convergent, so a future FAIL-rule addition can never
   again hard-crash a build the way SUMMARY_PREPOSITION_PILEUP and PROSE_NESTED_LIST did.

Tests: the source lint passes on both source resumes (no first-person, no overloaded bullet, no
placeholder/cliche/duty-only opener); a property test asserts every FAIL-severity prose rule has a
convergent repair across all artifacts.

## Already applied (content stopgap, across the BELAY and Hard Rock runs)

Overloaded source bullets flagged by F3 were tightened, matching the earlier Implementation-lane
work; uncommitted, fold into the source content commit:
- `source/Estrada_Resume_PreSales_CSM.docx`: the de-facto-product-owner bullet and the $1M+ recovery
  bullet (BELAY run).
- `source/Estrada_Resume_Implementation.docx`: the "Cut migration and audit risk" ETL bullet (still
  43 words after the earlier tighten, now 29) and the "Partnered with plant controllers" finance
  bullet (Hard Rock run); and the "Improved delivery predictability by producing Statements of
  Work" bullet (31 words / 6 commas, now 29 / 4) from the APC run.
- Both source resumes: fixed a first-person pronoun the F10-step-0 test surfaced, "customizations
  I proposed" -> "proposed customizations" (the ADP build's remaining blocker after the summary
  demotion). Applies to `source/Estrada_Resume_Implementation.docx` and
  `source/Estrada_Resume_PreSales_CSM.docx`. Fold into the same source-content commit.
