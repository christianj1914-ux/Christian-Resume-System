# Analysis and plan: getting more job postings all the way through, with better content

Deep analysis of the 20 workflow runs Christian captured on 2026-07-20 (HEAD 42faaa2, after F10
step 0 and the F6-F9 polish). Goal: (1) make the workflow complete for more postings, prioritizing
Delta / Adobe / Blue Yonder, and (2) improve resume and cover-letter content quality. No
applications submitted yet.

## FINAL EXECUTION ORDER FOR CODEX (authoritative; this is the handoff)

This is the single ordered plan. Each numbered item is its own commit; every slice ends green on
`python scripts/smoke_test.py`, `python tasks.py validate`, `python tasks.py source-lint`, and a live
build. Detailed specs and root causes are in the S-sections below and in
`CODEX_PACKET_systemwide_docfixes.md` (F items). The `codex-systemwide-docfixes` branch already holds
uncommitted verification patches; commit those first (see step 0).

0. Recover and commit. Restore the active `jobs/` files from the pre-run backup (the interrupted run
   left the active job on Delta Marketing PO). Commit the existing uncommitted verification patches
   (build_resume weave-safety, build_cover_letter plant-controllers repair, question_prep motivation
   suppression, the 3 new smoke regressions) as a focused commit.
1. S1 + S3 weave-safety invariant (build crash; highest priority). Generalize
   `summary_weave_candidate_is_safe()`: any summary mutation (weave, repair) must re-validate the full
   summary contract (exactly 3 sentences, each under the word cap, no pileup) before acceptance, else
   fall back. Confirm it checks word count, not just sentence count. Regression: USAA, Delta Crew PO,
   HD Supply eProc, Blue Yonder Functional Architect build clean.
2. S4 cover generation finish. Plant-controllers is repaired; still needed: replace the lane-token "My
   background lines up with the {lane tokens} ... role calls for" sentence with natural prose, produce
   2-3 real body paragraphs each with a distinct relevant proof, and stop mismatched proofs.
3. S5 done; keep the global-notes motivation suppression as a guard.
4. S6 positioning reframe. Set the CONFIRMED motivation line as the new first line of
   `source/global_notes.txt` (see the S6 section, exact text). Lead the professional summary and
   headline with the broad capability identity (specialize per lane), reframe Aderant as enterprise
   application support, keep the Aptean client count at the documented 80+.
5. S7 lane expansion (fixes the false failures). Add 4 functional lanes: `program_delivery`,
   `product_ownership`, `process_improvement`, `technical_support_admin` (5 -> 9), with title-priority
   routing so PM/product/support roles stop mis-routing to `implementation_delivery`. Optionally extend
   `analytics_operations` signals with supply-chain terms. Do NOT add life-sciences or a general-IT
   lane. S3 keyword weaving and S6 per-lane specialization key off these lanes.
6. F6, F7, F11 (messaging, DRAFT-policy docs, source lint + convergence guard; extend F11's lint to
   flag stale generic phrasing in global_notes).
7. Content sweep (PROSE_STACKED_MODIFIER; "durable adoption" repetition), then the full 20-run rebuild
   with per-target archive folders (broad Blue Yonder / Delta output names collide).

Interview/mindset prep and daily practice are CONTENT already produced in `interview_prep/` (the
reframe, the answer bank's Part 0, the daily-practice positioning anchor); the only system-side piece
is that the generated TMAY/positioning should default to the broad capability and specialize per lane
(part of S6). Federal workflow is a separate, later workstream (scoped near the end of this doc).

Guardrails throughout: Word-only (no PDF), no invented content or unsupported keywords, F3 bullet
checks stay report-only, weak fits stay honestly FAIL/BRIDGE.

## Run scoreboard (20 runs)

REQ = requirement coverage (fit). ALIGN = final alignment /115 (86 is the fail floor). Cover = was
a cover letter generated.

| # | Role | REQ | ALIGN | Outcome | Cover |
|---|------|-----|-------|---------|-------|
| 1 | CivicPlus - Implementation Consultant | 25/40 | 86 | FAIL | no |
| 2 | USAA - P&C Product Mgmt Analyst | 32/40 | - | CRASH (3-sentence) | no |
| 3 | JBAndrews - Solutions Engineer | 20/40 | 87 | FAIL | no |
| 4 | Delta - Sr Operations Analyst | 24/40 | 89 | BRIDGE | yes |
| 5 | Delta - Crew Technology Product Owner | 20/40 | - | CRASH (3-sentence) | no |
| 6 | Delta - Marketing Tech Sr Product Owner | 20/40 | 82 | FAIL | no |
| 7 | Intuitive - Sr Logistics Compliance Analyst | 14/40 | 83 | FAIL | no |
| 8 | Advyzon - Technical Consultant | 26/40 | 92 | PASS | yes |
| 9 | Stord - Sr Deployment Technical PM | 33/40 | - | PASS | yes |
| 10 | Stord - Staff Technical PM | 36/40 | - | BRIDGE | yes |
| 11 | HD Supply - Sr Mgr eCommerce Ops | 20/40 | 77 | FAIL | no |
| 12 | HD Supply - Sr Mgr eProcurement & Strategy | 20/40 | - | CRASH (3-sentence) | no |
| 13 | Blue Yonder - Functional Solution Architect | 29/40 | - | CRASH (3-sentence) | no |
| 14 | Blue Yonder - Solutions Advisor | 32/40 | 93 | FAIL | no |
| 15 | Blue Yonder - Services Advisor (Pre-Sales) | 20/40 | 87 | FAIL | no |
| 16 | Blue Yonder - Program Manager | 35/40 | 89 | FAIL | no |
| 17 | Manhattan - Sr IT Delivery Mgr | 32/40 | 84 | FAIL | no |
| 18 | Manhattan - Sr Enablement Consultant | 35/40 | 94 | PASS | yes |
| 19 | Adobe - Sr Program Manager GSO | 28/40 | 95 | FAIL | no |
| 20 | Adobe - Solutions Consultant | 20/40 | 81 | FAIL | no |

Totals: 3 PASS, 2 BRIDGE, 11 FAIL, 4 CRASH. Cover letters generated: 5 of 20 (only the PASS/BRIDGE
runs). That is the "still failing, and no cover letters" you are seeing.

## The three root causes (these explain everything above)

### S1 (HIGH, build crash) The summary "exactly 3 sentences" rule fights the F10 split repair

Four runs hard-crash with: `Professional Summary must use exactly 3 recruiter-friendly sentences;
found 4`. The professional summary is required to be exactly three sentences. But the F10
preposition-pileup repair resolves a pileup by SPLITTING a sentence, which turns 3 sentences into 4
and produces a fragment. Example from the USAA crash:

> "...10+ years turning AI-assisted workflow questions. Data-trust issues into clearer decisions,
> measurable process improvement, and usable reporting..."

"Data-trust issues into clearer decisions..." is an ungrammatical fragment, and the split made it a
4-sentence summary, so it hard-fails. F10 step 0 (demote to warn) plus the partial builder tightening
fixed some JDs (Toast, ADP now build clean), but for these four the builder still emits a pileup and
the split-based repair breaks both grammar and the 3-sentence contract.

Root fix (builder, not repair): generate a clean, 3-sentence summary with no preposition pileup and
no over-length sentence in the first place, so no split is ever needed. Splitting is fundamentally
incompatible with a fixed 3-sentence structure; the summary builder must produce compliant text
directly. Retire the summary split-repair path and rely on builder correctness plus a warn.

### S2 (HIGH, no cover letters) FAIL/CRASH resumes skip the cover letter entirely

Cover letters were generated for exactly the 5 PASS/BRIDGE runs and zero of the 15 FAIL/CRASH runs.
The F6-F9 gating now stops the workflow after a non-passing resume ("later steps were skipped by
design"). This is the F8 change over-corrected: I recommended not recording a FAIL as a clean
tracker row; it was implemented as "skip all downstream (cover + qualifications) on FAIL."

That is backwards for how Christian applies. The gate's own advice literally says "Write the cover
letter first rather than last. The cover letter is where stretch candidates make their case." Yet the
workflow now refuses to write one for exactly those stretch/FAIL cases. And many FAILs are not even
weak fits (see S3), so strong-fit roles like Adobe Sr PM (95/115) and Blue Yonder Program Manager
(35/40 req, 89/115) get no cover.

Root fix: build the cover letter (and qualifications) even when the resume is FAIL, surfacing the
warnings, and gate only the tracker auto-add / "clean application" recording behind PASS/BRIDGE.
A FAIL should produce a cover marked "needs review," not no cover.

### S3 (HIGH, tailoring: convert good-fit FAILs to PASS) Summary and top bullets do not surface JD keywords

The FAIL-versus-PASS line for floor-clearing roles is the keyword-placement / job-language audit, not
fit. Compare: Adobe Sr PM 95/115 -> FAIL ("Professional Summary weak job-language, 0 keyword hits");
Advyzon 92/115 -> PASS. Blue Yonder Program Manager 89/115 and 35/40 req -> FAIL ("weak job-language,
1 keyword hit; teams delivery missing; technical missing; customer buried in Skills only"). These are
good fits whose generated summary and top bullets speak Christian's generic language instead of the
posting's.

Root fix (tailoring): weave the posting's high-value keywords into the professional summary and the
top two or three experience bullets when they are truthfully supported, so the job-language audit
passes on merit. This is the single highest-leverage change for "getting more postings all the way
through." It must stay honest: only surface terms Christian's evidence supports (do not insert
unsupported bridge terms, which the system already correctly refuses, e.g. "gaming", "executive-level",
"school").

### Content-quality notes (fold in)
- The summary fragments in S1 are the clearest "does not make sense" content. Fixing S1 at the builder
  removes them.
- `PROSE_STACKED_MODIFIER` warning on the Aptean role summary ("Drove pre-sales and full-life[cycle]...")
  appeared (Adobe Solutions Consultant). Minor; sweep stacked hyphenated modifiers in role summaries.
- Once Christian attaches the PASS/BRIDGE documents, do a direct content read of the actual resume and
  cover text (the console logs do not contain full body text) to catch anything the audits miss.

## Priority-three deep dive

### Blue Yonder (your strongest priority by fit)
- Program Manager, 35/40 req, 89/115: strong fit, FAILs only on keyword placement (S3) and gets no
  cover (S2). Fixing S2 + S3 gets this through with a cover. Highest-value Blue Yonder target.
- Solutions Advisor, 32/40, 93/115: strong fit, same S2 + S3 blockers.
- Functional Solution Architect (Supply Chain), 29/40: good fit (matches your ERP/implementation
  depth), blocked by the S1 crash. Fix S1 and it should build.
- Services Advisor (Pre-Sales), 20/40, 87/115: weaker fit; your RFP/pre-sales helps but 20/40 is a
  stretch. Pursue after the top three.
Net: fixing S1 + S2 + S3 gets 3 of 4 Blue Yonder roles through with cover letters. This is the best
return of the three companies.

### Adobe
- Sr Program Manager GSO, 28/40, 95/115 (highest alignment in the whole set): the alignment says this
  is a real fit, but the summary has 0 keyword hits, so it FAILs and gets no cover. Pure S3 + S2 fix.
  Your most viable Adobe role.
- Solutions Consultant, 20/40, 81/115 (below floor): genuine stretch. Lower priority.

### Delta (genuinely the weakest of the three by fit)
- Sr Operations Analyst, 24/40, 89/115: already reaches BRIDGE and builds a cover. The most viable
  Delta role today; polish it with S3 keyword weaving.
- Crew Technology Product Owner, 20/40: crashes (S1); even fixed, 20/40 is a stretch that needs a
  strong bridge cover.
- Marketing Tech Sr Product Owner, 20/40, 82/115 (below floor): stretch.
Net: Delta roles are 20-24/40 fits. Sr Operations Analyst is the one to prioritize; the Product Owner
roles are bridge applications that live or die on the cover letter (so S2 matters for them).

## Fit triage across all 20 (where to spend effort)

Strong fits (req 30+), pursue: Stord Staff TPM (36, BRIDGE), Manhattan Sr Enablement Consultant (35,
PASS), Blue Yonder Program Manager (35), Stord Sr Deployment TPM (33, PASS), USAA P&C Product Analyst
(32, crashes on S1), Blue Yonder Solutions Advisor (32), Manhattan Sr IT Delivery Mgr (32).

Good fits (req 25-29): Blue Yonder Functional Solution Architect (29, crash), Adobe Sr PM (28),
Advyzon Technical Consultant (26, PASS), CivicPlus Implementation Consultant (25).

Stretch (req <=24), bridge or skip: Delta Sr Ops (24, bridge), Delta Crew PO (20), Delta Marketing PO
(20), JBAndrews Solutions Engineer (20), HD Supply eCommerce (20, align 77 - skip), HD Supply eProc
(20), Blue Yonder Services Advisor (20), Adobe Solutions Consultant (20), Intuitive Logistics
Compliance (14 - clear skip).

Honest read: your strongest-fit roles right now are Stord, Manhattan, and Blue Yonder Program Manager
/ Solutions Advisor, and those are exactly the ones being lost to S2 (no cover) and S3 (keyword
placement), not to fit. Delta is your weakest priority; focus Delta effort on the Sr Operations
Analyst.

## Content quality of the passed/bridge documents (from the attached files)

Resumes: the professional summaries are now clean, all three sentences, grammatical, under the word
cap, no fragments. That confirms the summary fix works for these JDs. Minor nit: the closing sentence
repeats a word ("...adoption turn into durable adoption..." on Advyzon and Stord); dedupe it.

The cover letters and the qualifications "why interested" sections are the broken content. Even
though these five applications passed, their cover letters and qual openers would embarrass on
sending. These are separate content-generation gaps, and they mean the earlier F2/F5 commits added
gates but did not finish generation.

### S4 (HIGH, content) Cover letters are canned, sometimes broken, and role-agnostic
Across all five letters:
- Every letter contains the identical role-agnostic sentence "The work only lands when client
  requirements, configuration choices, and follow-through stay aligned through go-live." It makes no
  sense for Delta (customer-experience operations) or Manhattan (learning and enablement), which are
  not configuration/go-live roles.
- Every letter contains the identical filler "What motivates me is using technology to help people
  and organizations work better."
- Grammar break in both Stord letters: "partnering with the and plant controllers on financial
  close" ("the and" dropped a word, probably "the CFO and plant controllers").
- Internal lane-token jargon rendered as prose: "the stakeholder enablement and adoption
  follow-through and structured consulting delivery this ... role calls for" (the F5 lane-token leak,
  still present).
- Thin body: a single orphaned proof line, not a paragraph.
- Mismatched proof: Advyzon (a wealth-management fintech) gets a warehouse / Amazon Robotics proof,
  and "Stood up a new warehouse in the enterprise systems" reads oddly.
F5 needs real generation work, not just gates: a role-specific opening tied to the JD, two to three
substantive body paragraphs each with a distinct, relevant proof, zero internal lane tokens, and no
canned role-agnostic sentences.

### S5 (HIGH, content) Qualifications "why interested" and proof slots are still broken (F2 unfinished)
The interview-story answers ("Talk me through an implementation", "Would you say the flow is
similar") are good now, concrete and company-named, from the committed interview expansion. But the
"Why are you interested" and non-story sections still carry the old F2 bugs:
- Dangling proof slot: "A concrete proof point is 60+ executive workshops and." (Delta, Manhattan) -
  ends on "and." mid-phrase.
- Wrong employer type: "Delta is the kind of consulting firm environment where..." (Delta is an
  airline).
- Descriptor-as-subject: "...where cross-functional operating decisions directly shape the work" and
  "the need to solve problems in cross-functional operating decisions".
- Split fragment: "the need to solve problems in system change. User adoption, and that is already
  visible" (Manhattan) and "...ERP implementation, go-live. Adoption work, and that is already
  visible" (Stord) - a list was split mid-phrase into a fragment.
F2's fix reached the recent-interview answers but not the "why interested" builder, the proof-anchor
slot, or the employer-type phrase. Finish those.

## Plan: Claude and Codex

### Master sequence for Codex (entire system, priority order)

This reconciles the new findings (S1-S5) with the outstanding items in
`CODEX_PACKET_systemwide_docfixes.md` (F items). Where an S and an F overlap, they are the same work,
deepened by the new evidence. Work top to bottom; each is its own commit; every slice ends green on
`python scripts/smoke_test.py` + `python tasks.py validate` + the relevant archived/live build.

1. S1 = F10 full repair (HIGH, build crash). The correct fix is builder-side, not repair-side:
   generate a compliant 3-sentence summary with no preposition pileup and no over-length sentence for
   every lane and JD, and retire the split-based summary repair, which creates fragments and a 4th
   sentence that collides with the "exactly 3 sentences" rule. Apply the same no-split discipline to
   the qualifications "why interested" text (S5 shows the same mid-list split there). Re-promote the
   summary rules to fail only once golden summaries pass. Regression: USAA, Delta Crew PO, HD Supply
   eProc, and Blue Yonder Functional Architect build with grammatical 3-sentence summaries.
2. Source content commit. Commit the dirty `source/*.docx` edits (degree, tightened/new bullets,
   keywords, core training, PMP-in-progress, first-person fix) as a focused content commit.
3. S2 = F8 correction (HIGH, no cover letters). F8 was implemented as "skip all downstream on FAIL";
   correct it to build the cover letter and qualifications even on FAIL, gating only the tracker
   auto-add / clean-application recording behind PASS/BRIDGE. A FAIL cover is marked needs-review, not
   skipped. Regression: a FAIL run produces a cover letter and qualifications.
4. S4 = F5 finished (HIGH, cover content). Real cover generation: a role-specific opening from the JD,
   two to three substantive body paragraphs each with a distinct relevant proof, no canned
   role-agnostic sentences ("configuration choices ... through go-live", "What motivates me..."), no
   internal lane tokens, fix the "the and plant controllers" break, and no mismatched proof (no
   warehouse story for a fintech). This also satisfies F9 (cover specificity). Regression: no two cover
   letters share the canned sentences; no lane tokens; body has 2-3 distinct-proof paragraphs.
5. S5 = F2 finished (HIGH, qualifications content). Fix the dangling "A concrete proof point is ...
   and." slot, the "{company} is the kind of {employer_type}" phrase (Delta is not a consulting firm),
   the descriptor-as-subject, and the split fragment in "why interested". Regression: no qual answer
   ends on a dangling "and."; no descriptor phrase is a sentence subject; employer type is accurate or
   omitted.
6. S3 keyword tailoring (HIGH, converts good-fit FAILs to PASS). Weave truthfully-supported JD keywords
   into the professional summary and top two or three bullets so the job-language audit passes; keep
   the unsupported-bridge refusal intact. Regression: Adobe Sr PM and Blue Yonder Program Manager move
   from FAIL to PASS/BRIDGE on keyword placement without inserting unsupported terms.
7. F6, F7, F11 (polish and robustness; details in `CODEX_PACKET_systemwide_docfixes.md`): score-label
   messaging and FAIL-reason clarity (F6), the low-overlap DRAFT decision (F7), and the source-content
   lint plus generalized convergence guard so no FAIL prose rule on any artifact can crash a build (F11).
8. Content sweep: eliminate `PROSE_STACKED_MODIFIER` in role summaries and the "durable adoption"
   word-repetition in the summary close.

Guardrails throughout: Word-only (no PDF), no invented content or unsupported keywords, F3 bullet
checks stay report-only, weak fits stay honestly FAIL/BRIDGE.

### Claude (me), supporting the system-first path
- Draft the S3 tailoring spec (which JD keyword sources, where they may appear in summary/bullets, and
  the honesty rules) for Codex to implement.
- Review Codex's S1-S5 implementation plan and diffs before and after each slice.
- After the fixes land, re-run the archived JDs (the 20 here, plus Delta/Adobe/Blue Yonder) to verify
  builds complete, covers generate, and content reads cleanly.
- Hand-tuning individual applications is deferred at Christian's request (system-first).

## Appendix: S3 keyword-tailoring spec (for Codex)

Goal: convert good-fit roles that clear the alignment floor but FAIL on keyword placement (Adobe Sr
PM 95/115, Blue Yonder Program Manager 89/115, Solutions Advisor 93/115) into PASS/BRIDGE, honestly.

- Target list: reuse what the audit already computes. The build prints, per JD, the exact missing or
  buried keywords ("Keyword placement gap: program management is missing", "customer is buried in
  Skills only", "Professional Summary has weak job-language alignment (0 keyword hits)"). Use those as
  the tailoring target set; do not invent a parallel keyword extractor.
- Honesty filter (hard rule): only surface a keyword if Christian's evidence supports it. Intersect
  the JD target keywords with his supported evidence / proof-bank terms. Never surface a term already
  flagged `[unsupported-do-not-insert]` (gaming, executive-level, school, etc.); those stay in bridge
  notes and the cover letter. When a target keyword is unsupported, leave it as a reported gap.
- Placement, in order of preference:
  1. Professional summary: fold one or two supported target keywords into the positioning or proof
     sentence, keeping the 3-sentence, no-pileup, under-cap structure from S1. This directly addresses
     the "weak job-language / 0 keyword hits" FAIL driver.
  2. Top two or three experience bullets: for a keyword the audit says is "buried in Skills only",
     surface it into an early bullet where truthful (rephrase or reorder an existing bullet rather
     than adding a new one), so it is visible in the top third.
  3. Skills line: last resort only; the audit specifically penalizes keywords that live only in Skills.
- Anti-stuffing: cap additions (for example, at most two woven keywords in the summary and one per top
  bullet), and run the result through the existing prose validation so the text stays natural. Do not
  keyword-stuff.
- Verification: after weaving, re-run the job-language audit; the summary should clear the weak
  job-language threshold and the buried/missing gaps for supported terms should close. Regression:
  Adobe Sr PM (surface "program management", "process", "customer") and Blue Yonder Program Manager
  (surface "technical", "customer", "teams delivery" where supported) move from FAIL to PASS/BRIDGE,
  with no `[unsupported-do-not-insert]` term inserted.

## Update: branch verification (regenerated Blue Yonder / Adobe / Advyzon docs)

Read the regenerated priority documents from the `codex-systemwide-docfixes` branch:
- S2 works: Blue Yonder Program Manager, Adobe Sr PM, and Advyzon now GENERATE cover letters (as
  DRAFT) instead of getting none. The "no cover letters" problem is fixed.
- S5 works: the qualifications "why interested" no longer mislabels the employer ("Delta is a
  consulting firm" is gone; now "Adobe appears to need steady work around..."), the dangling "A
  concrete proof point is ... and." is fixed, and the mid-list split fragment is fixed.
- S3 works: Blue Yonder Program Manager and Adobe Sr PM resumes now PASS.
- S4 is partway: the two canned sentences are gone, replaced with JD-keyword openers, and the new
  `COVER_UNREPAIRED_VALIDATION` lint correctly catches the remaining defect and marks the cover DRAFT.
  But the GENERATION still ships defects that must be fixed, not just detected:
  - "partnering with the and plant controllers" persists. Root cause: the cover's proof-sentence
    compression drops a word from the source bullet ("plant controllers, accounting managers, and the
    CFO" becomes "the and plant controllers"). Fix the compression.
  - The "My background lines up directly with the {lane tokens} this {role} role calls for" sentence
    still concatenates internal lane descriptors into unnatural prose. Replace with a natural sentence.
  - Body is still two proof sentences crammed into one paragraph, not 2-3 real paragraphs.
  - Mismatched proof (Adobe GSO gets the finance-close / plant-controllers line).
  Do not submit these covers yet; S4 generation is still in progress.
Minor S5 polish (optional, later): "steady work around X" and "improve system change" read slightly
awkward.

## S6 (content/positioning) Lead the resume and pitch with the dual-sided ERP reframe

From the recruiter-call analysis (`interview_prep/Recruiter call analysis and repositioning.md`):
Christian's strongest, most differentiated asset is having run ERP implementations from both the
vendor side (Aptean) and the client/owner side (East West), plus finance-plus-IT and cross-border
supply chain. The system currently generates a generic "enterprise systems consultant" positioning
that buries this.
- The professional summary and resume headline should LEAD with the dual-sided ERP implementation
  identity and name a target title ("ERP Implementation Consultant"), not generic language; make the
  dual vendor + client fact a headline in the summary.
- The generated TMAY / positioning statement should default to the dual-sided ERP story for ERP and
  implementation targets, then branch to breadth.
- Reframe the Aderant role in the source resume as enterprise application support with SQL Server,
  Active Directory, and integration diagnostics (not support/desktop language).
- Reconcile the Aptean client count (resume says 80+; use that documented number consistently; do not
  inflate to the recruiter's loose "~100").
Coordination: these are source-content and summary/positioning changes. Because Codex is actively
editing source resumes and generators now, Claude has NOT made the source edits, to avoid conflicts;
this is specced for Codex to fold into the current source-content and S3/summary work.

## Codex verification integration + answers to Codex's review questions

Codex ran a full 20-run rebuild-and-verify pass and found real remaining bugs. Integrating them here
so the next Codex pass has one complete plan.

### Confirmed: the S1 crash was reopened by S3 (critical interaction, highest priority)
USAA reproduced the crash ("Professional Summary must use exactly 3 recruiter-friendly sentences;
found 4", fragment "AI-assisted workflow questions. Data-trust issues..."). Root cause was NOT the
summary builder but S3 keyword weaving: it appended "with emphasis on dashboards reporting and
strategy", pushing the first sentence over length, and the generic clause-density repair then split it
into a 4th sentence. So S3 re-opened S1. Codex's fix, `summary_weave_candidate_is_safe()` (reject a
weave that is not exactly 3 sentences or fails summary prose validation, with a safer close-sentence
fallback), is the RIGHT architecture, not a USAA patch. Answers to Codex's questions:
- Yes, it must also check word count. The invariant: a woven candidate must pass the SAME sendability
  checks the final summary must pass, every summary FAIL rule (SENTENCE_TOO_LONG, TOO_LONG,
  PREPOSITION_PILEUP) plus the exactly-3-sentence rule, and must not change the sentence count. Cleanest
  test: `repair_text(candidate, "summary")` converges without changing the sentence count AND the
  candidate passes every summary rule; else fall back.
- General principle to encode: any mutation of the summary (weave, repair, smoothing) must re-validate
  the full summary contract before acceptance. This is the standing invariant that closes the whole
  S1/S3 class; mirror the F11 convergence guard, now as "any summary mutation stays sendable."

### Confirmed: some "canned" content is stale SOURCE, not a generator bug (global_notes.txt)
Verified: `source/global_notes.txt` opens with "What motivates me is using technology to help people
and organizations work better..." and the qualifications builder faithfully preserved it. Codex's
suppression (ban that exact sentence, skip it from global_notes) is a good SAFETY guard; keep it. But
the root fix is to rewrite the note, which is also where S6 lands:
- Rewrite the global_notes motivation to a specific, truthful, but LANE-BROAD statement (not
  ERP-only; Christian applies across program/product/process/consulting). The umbrella is a
  capability, not a domain: turning ambiguous cross-functional work into structured, adopted delivery.
  CONFIRMED by Christian (2026-07-21). Set this as the new first line of `source/global_notes.txt`,
  replacing the generic "What motivates me is using technology..." line. Use exactly this text.
  Broadened to hit all lanes (program/product/process/
  support/consulting/implementation/CS/analytics/change): "What drives me is stepping into ambiguous,
  cross-functional problems, the ones without a clear owner, and turning them into structured work
  that people actually use and that holds up after I hand it off. I do my best work where business,
  operations, and technology have to line up, whatever the title, and I care most about closing the
  gap between a plan and something that actually works in practice." ("whatever the title" keeps it
  lane-agnostic; the summary/positioning specializes per lane.)
- Positioning note for the generator: the default identity should be this broad capability, then the
  summary/positioning specializes per lane (ERP dual-sided for implementation roles, program delivery
  for PM, process improvement for CI, etc.). Broad umbrella, sharp per-lane proof, not ERP-only.
- Keep the suppression as a guard even after the rewrite. Have F11's source-lint flag generic
  motivation phrasing in global_notes so it cannot silently return.

### S4 cover generation: plant-controllers fixed, two defects remain
Codex moved the "the and plant controllers" -> "the CFO and plant controllers" repair into the common
`repair_cover_paragraph()` (correct; proof paragraphs bypassed the later smoothing). Remaining S4 work
from the branch DRAFT covers I read: the "My background lines up directly with the {lane tokens} this
{role} role calls for" sentence still concatenates internal lane descriptors into unnatural prose
(replace with a natural sentence); the body is still two proof sentences crammed into one paragraph
(produce 2-3 real body paragraphs, each with a distinct, relevant proof; stop pairing mismatched proofs
like Adobe GSO getting the finance-close line).

### Operational (must-do before the next rebuild)
- Restore the active `jobs/` files first. The interrupted rebuild left `jobs/job_description.txt` on
  Delta Marketing Tech Sr PO; the pre-run backup is at the temp path Codex noted. Restore Christian's
  original active state before anything else (the swap-check hazard from the start of this engagement).
- Commit the uncommitted verification patches (build_resume weave-safety, build_cover_letter repair,
  question_prep motivation suppression, the three new smoke regressions) as a focused commit.
- Re-run `python scripts/smoke_test.py`, `python tasks.py validate`, `python tasks.py source-lint`.
- Complete the 20-run rebuild with per-target archive folders (the Blue Yonder / Delta broad-name
  filename-collision risk is real; do not rely on `/output` alone). The `06_Delta_Marketing` rebuilt
  folder is currently empty and needs re-running.

## The complete plan spans three domains (per Christian's request)

1. Resume workflows (Codex code), updated master sequence:
   a. S1 + S3 weave-safety invariant (biggest correctness item; generalize `summary_weave_candidate_is_safe`).
   b. S4 cover generation finish (lane-token sentence + real body paragraphs; plant-controllers already repaired).
   c. S5 done; keep the global-notes motivation suppression.
   d. S6 positioning reframe: rewrite the global_notes motivation (Christian-confirmed), lead the
      summary and headline with the dual-sided ERP identity and target title, reframe Aderant as
      enterprise application support, keep the Aptean client count at the documented 80+.
   e. F6, F7, F11 (extend F11's source-lint to flag stale generic phrasing in global_notes).
   f. Content sweep + operational (restore active files, commit patches, full rebuild with per-target folders).
2. Interview and mindset prep (content, already produced in `interview_prep/`): the recruiter-call
   reframe, the answer bank's "Part 0: Your positioning" (dual-sided pitch, target title, the three
   reframes), and the fit triage. System-side piece: the generated TMAY / positioning statement should
   default to the dual-sided ERP story (part of S6).
3. Daily practice (content, done in `interview_prep/`): the daily-practice positioning anchor (the
   20-second pitch, the disclaimer-kill, the metric reflex, and the one-title drills). No Codex code
   needed; this is rehearsal material.

## S7 (HIGH, root cause of the false failures) Expand the lane taxonomy: add program/delivery, product, and process-improvement lanes

Diagnosis, confirmed in code: the system has 5 targeting lanes, `change_enablement`,
`presales_solution`, `customer_success`, `implementation_delivery`, `analytics_operations`
(`scripts/config/job_profiles.py:75`). Christian is heavily targeting Program/Project Management,
Product Ownership, and Continuous Improvement roles, which have NO dedicated lane. Worse, "project
management" is a signal for `implementation_delivery`, so a Program Manager or Product Owner JD routes
to the implementation lane and gets implementation-flavored positioning and keywords (go-live,
configuration, data migration) that do not match the actual JD. The job-language / keyword-placement
audit then marks a genuinely good-fit role FAIL. This is exactly why Blue Yonder Program Manager
(35/40 req) and Adobe Sr PM (95/115 alignment) FAILed with 0-1 summary keyword hits: mis-routing, not
misfit. That is the false-failure mechanism.

Add three lanes (5 -> 8), each with signals, problem/audience/outcomes, a positioning template, and a
proof-anchor map so the right story leads:
1. `program_delivery` (Program / Project / Delivery Management). Signals: program manager, technical
   program manager, program management, delivery manager, delivery lead, engagement manager, roadmap,
   dependencies, milestones, governance, PMO, cross-functional program, stakeholder management, agile,
   waterfall, risk register. Proof anchors to lead: the five-month EFT/ACH replacement, the warehouse +
   Amazon Robotics launch, five-site coordination without authority, PMP-in-progress.
2. `product_ownership` (Product Owner / Product Management). Signals: product owner, product manager,
   product management, product analyst, backlog, user stories, roadmap, prioritization, discovery,
   sprint, feature, stakeholder requirements. Proof anchors: de facto product owner of the ERP
   platform, requirements to backlog to adoption, Agile partnership, VP and director investment
   decisions.
3. `process_improvement` (Continuous Improvement / Business Process). Signals: continuous improvement,
   process improvement, business process, lean, six sigma, kaizen, workflow optimization,
   standardization, operational excellence, efficiency, process analyst. Proof anchors: the 78% / 22%
   automation, workflow redesign, standardization across five sites.

Detection nuance (important): title-based signals must take priority over generic body keywords. A
"Program Manager" or "Product Owner" title should route to the new lane even when "project management"
or "requirements" (implementation_delivery signals) also appear in the JD body. Weight the title and
most-specific signal above generic body keywords, or the new lanes will keep losing to
implementation_delivery.

Impact: this is the single highest-leverage fix for the false failures across Christian's priority
searches, and it operationalizes broaden-but-specialize, each new lane is a specialization for a role
type he is actively targeting. Sequence it alongside S3 (the lane determines which keywords S3 weaves)
and S6 (the broad umbrella identity specializes per lane). Regression: Blue Yonder Program Manager and
Adobe Sr PM route to `program_delivery`, surface program-management keywords, and move off the
keyword-placement FAIL; a Continuous Improvement JD routes to `process_improvement` and leads with the
78/22 story.

### Other candidate lanes, verified (add one more; the rest are already covered or should be skipped)
The system has two axes: functional lanes (what you do) and domain contexts (manufacturing, saas,
healthcare, financial_services, consulting, plus a supply-chain specialty). Checked each of Christian's
suggestions against both:
- Application support / general IT: ADD a 4th functional lane, `technical_support_admin` (application
  support, technical support engineer, systems administrator, IT analyst). Genuine gap, no current
  functional lane; real evidence (Aderant product-support engineer with SQL Server / AD / integration
  diagnostics, ITIL 4, ServiceNow admin, East West IT). Signals: technical support, application
  support, help desk, tier-2, tier-3, systems administrator, incident, troubleshooting, ITIL,
  ServiceNow, Active Directory, user provisioning. Proof anchors: Aderant enterprise app support, ERP
  and access administration at East West. Fold "general IT" into this lane; do not lead with tier-1
  help desk.
- Supply chain: already covered as a DOMAIN (the manufacturing context carries supply-chain signals,
  cover openings, an interview lens, and a supply-chain-optimization specialty). A supply-chain-analyst
  ROLE is functionally `analytics_operations` with the manufacturing/supply-chain domain overlay, so no
  new functional lane is needed; optionally add "supply chain / logistics / procurement / demand
  planning" to the `analytics_operations` signals so those roles route cleanly.
- Management / general consulting: mostly covered by the existing `consulting` domain context plus
  `presales_solution` and the new `program_delivery` lane. A dedicated advisory/strategy lane is
  optional and lower priority; only add if pure strategy/advisory roles (e.g., Guidehouse OCM,
  Chartis) become a focus.
- Life sciences: SKIP. It is a domain (the healthcare context exists), but Christian has no
  life-sciences experience, so those roles should honestly fail rather than be force-fit. Adding
  anything here would be inventing a specialty; do not.
Net lane recommendation: add 4 functional lanes (program_delivery, product_ownership,
process_improvement, technical_support_admin), 5 -> 9, and optionally extend `analytics_operations`
signals with supply-chain terms. Do not add life-sciences or a separate general-IT lane.

## Queued next: federal workflow analysis (start after the standard workflow lands)

Registered per Christian's request; the deep dive runs after S1-S7 are complete. The federal workflow
is a separate system: `build_federal_resume.py`, `build_federal_cover_letter.py`,
`federal_supporting_docs.py`, `build_federal_interview_cheat_sheet.py`,
`build_federal_detailed_interview_guide.py`, `run_federal_resume_workflow.py`.

Why "safely" matters: federal resumes are governed by hard USAJOBS requirements that standard resumes
are not, and improving tailoring must never strip them: hours per week, exact employment dates, salary,
supervisor/contact and may-we-contact, GS-level alignment, citizenship, announcement number, and
KSA / specialized-experience narratives. Any content or tailoring change has to preserve these.

Preliminary scope (to verify during the deep dive):
- Do the standard-workflow bugs have federal analogs? Check the federal summary/profile for the same
  crash and fragment issues (S1), the federal cover letter for the canned/lane-token and thin-body
  issues (S4), and the federal supporting docs for the stale global-notes motivation (S5).
- Federal tailoring: does the federal builder map the announcement's specialized-experience statements
  and KSAs to Christian's evidence, and surface the right keywords per announcement, or does it reuse
  generic language (the federal analog of S3)?
- Reframe and lanes: reconcile the dual-sided / broad-capability positioning (S6) and the new lanes
  (S7) with the federal narrative style (which is longer and accomplishment-plus-context, not the
  3-sentence summary).
- Approach: run the federal dry-runs (there are `scratch/federal_dry_run_*` snapshots), read the
  generated federal resume, cover, and supporting-doc text, and produce a federal-specific packet with
  the same discipline (severity-ranked, Word-only, no invented content, preserve all mandatory federal
  fields), for Codex to implement.

## Bottom line
Your builds are failing and coverless for two fixable systemic reasons (S1 crash, S2 cover-skip), and
your good-fit roles are being marked FAIL for a third (S3 keyword placement), not because they are bad
fits. Fix S1, S2, S3 and the majority of these, including most of Blue Yonder and Adobe Sr PM, go all
the way through with cover letters. Delta stays your weakest priority; lead with its Sr Operations
Analyst.
