# Codex Spec: Finish Fix 3 (inline example+result) + Phase 5 Career Operating Plan

Continuation of `CODEX_SPEC_interview_career_system.md` (master). Phase 4 (daily prep) is
approved. Two prose fixes landed; the third (every non-gap BLUF answer weaves example+result
inline) only half-landed. This pass finishes fix 3, then builds Phase 5 (career operating plan).
Build, verify, stop for review before Phase 6.

Guardrails unchanged: truthful only; weakness text speaks only interview_safe + improvement,
never honest_name; honest_name never appears in generated text; no fabricated credentials;
gap-pivots admit -> bridge -> smart question only; full smoke/validate must PASS on a long window
(15+ min) or be reported as a blocker.

---

## Part A: finish fix 3 (inline example+result for every non-gap answer)
Verified in the fresh guide: implementation, data, adaptability, discovery, stakeholder
alignment, and strengths weave the example inline correctly. These still do NOT and must be
fixed: customer relationship building, process improvement, the "build productive relationships"
prompt, and the "when perspectives differ" prompt. Root causes and fixes:

1. Every signature story must have BOTH a `spoken_reference` and a `result`. Currently CEO
   escalation lacks a spoken_reference (only Windows-95, fast-ramp, EFT/ACH were seeded). Add:
   - CEO escalation spoken_reference: "for example, when a client's CEO felt the delivered
     product didn't match what was agreed, I took direct ownership, set a weekly cadence with
     him, fast-tracked the fixes with product and dev, and moved every agreement into writing";
     result: "the relationship recovered and the account held."
   - Confirm Windows-95, fast-ramp, EFT/ACH, and inventory automation each have a spoken_reference
     AND a result (inventory result: 78% less manual work, 22% fewer discrepancies, ~32% lower
     scrap cost).
2. A non-gap competency must NEVER render without its inline example+result. Variety (distinct
   stories, the 2-per-story cap) is a PREFERENCE, not a hard rule that strands an answer. If
   honoring the cap would leave a strong competency (e.g. process improvement) without an inline
   example, reuse the best-fit story rather than render it bare. Priority order: (1) never strand
   a non-gap answer example-less; (2) then prefer distinct stories / cap 2 for variety.
3. Weave example+result inline in the behavioral high-stakes prompts too: "build productive
   relationships" uses CEO escalation; "when perspectives differ" uses a second distinct story
   (EFT/ACH current-state mapping or Windows-95). These currently use an assembly path that omits
   the example; route them through the same BLUF assembly.
4. Exemptions stay: genuine gap-pivots (e.g. AI adoption if a gap) are admit -> bridge -> ask, no
   result; the pure why-this-role motivation answer needs no result.
5. Tighten the test to assert on RENDERED PROSE, not object fields: each non-gap "BLUF ANSWER:"
   paragraph must contain an example clause (its spoken_reference) AND a result sentence. Re-render
   the sample detailed guide.

---

## Part B: Phase 5 - career operating plan (master Module 5)
Add `build_career_plan()` and `scripts/build_career_operating_plan.py` producing one Word doc,
read on a cadence rather than run linearly:
- Target roles: near-term realistic (Solutions Consultant / discovery-implementation) vs stretch
  north-star (Business Architect & AI Evangelist). Pull from `self_inventory.target_roles`.
- Gap-to-track mapping: each development area (weakness) and each stretch-role gap links to a
  specific track in the existing `Study/` learning path (e.g. formal-methodology gap -> Lean Six
  Sigma / PMP; AI-engineering gap -> AI-900 + AI track; architecture gap -> TOGAF; analytics ->
  PL-300; delivery communication -> the daily prep loop). Studying is gap-driven, not a checklist.
  Reference the Study/ docs, do not duplicate them.
- Two explicit modes: "get a job now" (delivery reps + applications + the one or two gaps that
  block current-tier roles) and "excel in the job" (continue the learning path, log new wins into
  the self-inventory, quarterly self-inventory refresh, stay interview-ready).
- Review checkpoints: monthly quick (update wins, adjust focus) and quarterly deep (re-rank target
  roles, refresh strengths/weaknesses). State them as a simple recurring rhythm.
- Add `tasks.py` command `career-plan`. Word-only into `output/`. Reads self-inventory; no
  fabricated credentials; no honest_name.

### Phase 5 tests
- Career plan links every development area and every stretch-role gap to a real Study/ track name.
- Both modes ("get a job now", "excel in the job") render.
- Near-term and stretch roles both appear.
- Safety: no honest_name, no unsupported credential phrase.

---

## Gates
`python scripts/smoke_test.py` and `python tasks.py validate` (long window, must pass, not time
out), `python tasks.py source-lint`, `python tasks.py commands`.

## Stop point
Deliver: the re-rendered detailed guide (all four previously example-less answers now weave
example+result inline) and a sample career operating plan. Stop for Christian's review before
Phase 6, the debrief feedback loop, which is the last phase and closes the system by letting each
interview debrief update the self-inventory and re-weight the next daily plan.

## Guardrails
- One focused commit per part (finish fix 3, then Phase 5) if commits are requested. Reuse
  existing generators/extraction. Word-only outputs to `output/`. Do not stage generated outputs,
  scratch logs, active jobs/ files, or spec docs.
