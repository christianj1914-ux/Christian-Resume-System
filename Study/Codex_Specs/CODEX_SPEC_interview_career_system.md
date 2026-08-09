# Codex Spec: Interview & Career Operating System

## Why this exists
Christian's core blocker is not capability, it is self-knowledge and delivery: he has lost track
of his own strengths and weaknesses, so he improvises under pressure, rambles, buries his best
evidence, and undersells. The fix is a durable system built on a single "know yourself"
foundation that feeds everything: interview answers, per-JD scorecards, daily practice, and a
long-term career plan. It must work career-long in two modes, "get a job now" and "excel in the
job," and it must not require a linear path. Build it as reusable generators on top of the
existing interview-prep code and the evidence ledger. Do NOT mass-produce per-job documents;
generate for planning and test runs only.

Supersedes [the archived interview scorecard specification](docs/specs/archive/CODEX_SPEC_interview_scorecard.md) (folds it in as Module 2). See
`interview_prep/Interview Repair Kit and Dematic Mock.md` and
`interview_prep/Scorecard - Adobe Business Architect and AI Evangelist.md` for target output
quality. Truthfulness is absolute: the self-inventory is Christian's real data; weaknesses are
honest; no fabricated credentials or experience.

Reuse, do not rebuild: `scripts/question_prep.py` (story bank, question categorization, answer
builders), `scripts/build_interview_cheat_sheet.py`, `scripts/build_detailed_interview_guide.py`,
`scripts/build_interview_companions.py`, `scripts/post_interview_debrief.py`,
`scripts/interview_context.py`, the evidence ledger (`source/evidence_terms.py`), the confirmed
motivation line, and the JD competency/keyword extraction in `scripts/resume_analysis.py` and the
federal competency parser.

Build in phases; Module 1 is the foundation everything else reads from.

---

## Module 1 (FOUNDATION): the Self-Inventory ("know yourself")

Create `source/self_inventory.json`, Christian's living self-model. Every other module reads from
it. Seed it with the draft below (Christian confirms/edits; this is his certified self-picture).

Structure:
- `strengths`: exactly 3, each { name, one_line, interview_safe (say-out-loud, confident but not
  arrogant, evidence-anchored), evidence_stories[], how_it_shows_up, keywords[] }.
- `weaknesses`: exactly 3, each { honest_name (for self-development only, never spoken),
  interview_safe (real but non-disqualifying, always paired with active improvement),
  improvement_action (links to a daily drill, a learning track, or a story to build), status }.
- `signature_stories`: the 5 anchor stories (reuse/extend the story bank, tagged with the
  competencies each proves): Windows-95 discovery, CEO escalation, East West fast ramp, EFT/ACH
  cross-functional, inventory automation / DMAIC.
- `motivation`: the confirmed motivation line already in source.
- `values`, `target_roles`, `non_negotiables`: short lists.

SEED (draft from observed evidence; Christian to confirm):

Strengths (name | interview_safe say-out-loud version):
1. Dual-sided implementation translator.
   interview_safe: "My biggest strength is translating between business and technical teams. I've
   implemented enterprise systems from both the vendor side and as the internal owner, so I can
   sit with a customer, understand what they actually need, turn it into something engineering
   can build, and make sure what's delivered still matches what was agreed."
   Evidence: Aptean 80+ clients + East West ownership; Windows-95 discovery; CEO escalation.
   Keywords: discovery, requirements, FRD/SOW, gap analysis, implementation judgment.
2. Fast ramp on unfamiliar systems.
   interview_safe: "I ramp quickly on unfamiliar systems. I've been handed platforms I'd never
   used and gotten up to speed fast enough to train other teams on them, because I map new tools
   to fundamentals I already know. I'm comfortable in ambiguity and I get productive fast."
   Evidence: East West thrown-into-fire; now hands-on with Claude/Codex. Keywords: adaptability,
   learning velocity, self-direction.
3. Cross-functional alignment without authority.
   interview_safe: "I'm strong at aligning cross-functional groups without formal authority,
   getting business, IT, finance, and vendors onto one plan everyone commits to. I did exactly
   that on a five-month payment-integration project spanning four different organizations."
   Evidence: EFT/ACH across four parties; 60+ executive workshops; CEO escalation. Keywords:
   stakeholder alignment, influence, delivery.

Weaknesses (honest_name is for development only and never spoken; interview_safe is what he says,
always real + non-disqualifying + paired with active improvement). 2 are presentation (fast,
free); 1 is skills (the learning path):
1. honest_name: rambles, buries the point, not BLUF.
   interview_safe: "I tend to go deep into detail when I care about the work, so I've been
   deliberately practicing leading with the headline first and keeping answers tight, especially
   with non-technical and executive audiences. It's made me a noticeably clearer communicator."
   Improvement: daily BLUF + story drills. Status: active.
2. honest_name: loses track of strengths, hedges ("just," "almost," "not really"), undersells.
   interview_safe: "Historically I've undersold my own contributions, I'd credit the team and
   downplay my part. I've been working on owning my impact accurately by keeping a running record
   of outcomes, which has made me a better advocate for my work and my team's."
   Improvement: this self-inventory + disclaimer-kill drill. Status: active.
3. honest_name: no formal Lean Six Sigma belt, thinner on deep AI-engineering (RAG/vector/
   protocols), TOGAF, cloud/coding foundations.
   interview_safe: "In a couple of areas my experience is hands-on rather than formally
   certified, for example I've led process-improvement work but haven't sat for a Six Sigma belt.
   I'm closing that deliberately, I'm actively pursuing certifications so the credentials match
   the experience." Improvement: the IT learning path (Study/ folder). Status: in progress.

Note for the answer builder: the "3 weaknesses" answer speaks ONLY the interview_safe versions,
each immediately followed by the active improvement. Never speak honest_name. For strengths, the
interview_safe line is the spoken answer; keep it to 2-3 sentences, lead with the strength, and
attach one concrete piece of evidence.

Generators from Module 1:
- `build_self_inventory_onepager()`: a print-ready "who I am" sheet (3 strengths with proof, 3
  weaknesses with active improvement, motivation, 5 stories) for pre-interview grounding and
  quarterly self-review.
- Answer builders for the two literal questions: "What are your 3 greatest strengths?" and "What
  are 3 weaknesses / areas you're working on?" in BLUF, drawing strengths with evidence and
  weaknesses with the interview_framing + the active improvement (never a naked flaw).

---

## Module 2: per-JD interview scorecard (folds in the prior spec)
- `jd_competency_scorecard(job_description)`: 4-8 scored competencies from the existing
  keyword/competency extraction + a curated `COMPETENCY_TAXONOMY`.
- `COMPETENCY_FRAMEWORKS`: competency -> frameworks/keywords to say out loud (process improvement
  -> DMAIC/5 Whys/Lean Six Sigma; delivery -> Agile/Scrum/risk register; discovery -> FRD/SOW/gap
  analysis; data -> KPI/Power BI/ETL; alignment -> RACI/executive readout; AI -> RAG/prompt
  engineering/adoption metrics).
- Map each competency to a self-inventory strength/story; flag gaps and emit an honest gap-pivot
  (admit -> bridge to a ramp story -> smart question). Never claim an absent credential.
- Render the one-page scorecard into the cheat sheet (competency | words to say | your story or
  pivot).

## Module 3: interview guides (enhance existing)
- Generate BLUF model answers (Answer -> Example -> Result -> Relevance) for the standard high-
  stakes prompts plus the JD's scorecard questions, all anchored to the self-inventory stories.
- Always include: why this role, walk-me-through-your-last-role (lead with the skill category),
  build relationships, alignment under conflict, 3 strengths, 3 weaknesses, biggest gap, 30/60/90,
  questions to ask.
- Enforce BLUF shape in tests (first sentence is the answer; a result appears; a relevance
  sentence ties to the JD).

## Module 4: daily prep system (sustainable, non-linear, two modes)
- `build_daily_prep_plan(mode)` with `mode` in {job_search, on_the_job}. Reuse the existing daily
  practice guide; add a rotating rep set so it never gets stale:
  - self-inventory rehearsal (say the 3 strengths + 3 weaknesses aloud, BLUF),
  - a delivery drill (BLUF rep, hedge/disclaimer kill-count),
  - a story rep (one of the 5 anchors, scored on lead-with-point + a number),
  - a scorecard rep (build a scorecard from a live JD in 5 minutes),
  - a weakness rep (one concrete action on an active weakness).
- Job-search mode weights delivery + scorecards + applications. On-the-job mode weights the
  learning path + logging new wins into the self-inventory + staying interview-ready.
- Maintain a simple progress log (`scratch/prep_log.csv` or similar): date, mode, reps done,
  hedge count, self-rated clarity. Advisory only; the point is a visible streak, not a gate.

## Module 5: career operating system (long-term throughline)
- `build_career_plan()`: one document that ties it together and is reviewed on a cadence, not run
  linearly:
  - Target roles (near-term realistic vs stretch, e.g. Solutions Consultant now, Business
    Architect/AI Evangelist as the north star).
  - Each weakness and each stretch-role gap mapped to a specific learning-path track in the
    Study/ folder (TOGAF, AI-900, Power BI/PL-300, Security+, AWS, PMP), so studying is gap-
    driven, not a checklist.
  - Two modes made explicit: "get a job now" (delivery + applications + targeted study of the one
    or two gaps that block current-tier roles) and "excel in the job" (continue the learning
    path, log wins, quarterly self-inventory refresh, stay interview-ready).
  - Review checkpoints (monthly quick, quarterly deep): update the self-inventory with new wins,
    re-rank target roles, adjust study focus.
- Reference the existing `Study/` learning path and schedule; do not duplicate them, link the
  weaknesses/gaps to their tracks.

## Module 6: feedback loop (the system learns)
- Extend `post_interview_debrief.py` so a debrief updates the self-inventory: which strengths
  landed, which weakness surfaced, any new story worth adding, and it re-weights the next daily
  plan toward whatever failed. This is what turns each interview, win or loss, into a system
  improvement instead of just a bruise.

---

## Test / verification (planning + one test run, not mass production)
- Unit: self-inventory loads; strengths=3, weaknesses=3; each weakness has an interview_framing
  and an improvement_action; strengths/weaknesses answer builders produce BLUF answers; no
  weakness answer emits a naked flaw with no improvement; no fabricated credential appears.
- Scorecard: returns 4-8 competencies for a sample JD; each maps to a story or an honest pivot.
- Daily plan: both modes generate a rotating rep set and write the progress log.
- Career plan: every weakness and stretch-gap links to a real Study/ track.
- Debrief: a sample debrief updates the self-inventory and re-weights the next plan.
- Gates: `python scripts\smoke_test.py`, `python tasks.py validate`, `python tasks.py source-lint`.
- Test run ONE role end-to-end (e.g., a Solutions Consultant JD): self-inventory one-pager +
  scorecard + guide + a daily plan + career plan. Christian reads it; confirm truthful, BLUF, and
  that nothing claims credentials or experience he lacks. Do not generate a batch of per-job docs.

## Guardrails
- Truthful only; the self-inventory is Christian's certified data; weaknesses honest with active
  improvement; gap-pivots for real gaps; stories from the evidence ledger.
- Reuse existing generators and extraction; phased build (Module 1 first, then 2+3, then 4, then
  5+6); one focused commit per module.
- Do not stage generated outputs, scratch logs, active jobs/ files, or spec docs.
