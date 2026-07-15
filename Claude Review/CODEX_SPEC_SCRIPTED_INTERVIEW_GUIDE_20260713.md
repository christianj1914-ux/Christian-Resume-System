# Codex Implementation Spec: Scripted Detailed Interview Guide (Authoritative)
## July 13, 2026 - Upgrade the detailed interview guide from "coaching about answers" to "rehearsable, verbatim, time-layered scripts with pushback branches"

## Summary

The detailed interview guide currently teaches Christian *how to think* about answers. It emits coaching grids ("what they are evaluating / bad-answer trap / best story angle"), single-block story answers, and a Tell Me About Yourself section made of one-line labeled fragments. In a live panel this produces exactly the failure captured in the latest debrief: stream-of-consciousness delivery, the point buried, the outcome missing until the interviewer prompts for it, and no plan for stretching or compressing an answer when the time cap changes.

This spec upgrades the guide so every core answer ships as a **verbatim, rehearsable script** with four things the current output lacks:

1. A **meat-first core** (20 to 30 seconds) that states the result and the role fit before any backstory.
2. A **time ladder** so the same answer can be delivered at 30 seconds, 60 to 90 seconds, 2 minutes, or 4 minutes, where each longer version is the shorter version plus labeled add-on modules (never a different, wandering answer).
3. An **alternate framing** of each hero story so it can answer more than one question type.
4. **Pushback branches**: scripted replies to the follow-up challenges an interviewer is likely to raise on that specific story.

Claude's role here is planner only. Codex applies the edits, runs the scripts, and validates the rendered Word documents locally, per the two-pass workflow in `CLAUDE.md`.

## Review Findings to Build In (Claude review, 2026-07-13)

These were surfaced reviewing the live code and Codex's consolidated plan. Build them in from the start rather than discovering them mid-implementation.

- **H2 (guardrail scoping).** `validate_delivery_principles` must run ONLY on the scripted spoken-answer strings (`meat_first`, `full`, `stretch_modules`, `alternate`, `pushback_branches` replies). It must NOT scan the reader-facing operating-system section, which intentionally quotes the banned hedges ("I guess," "let me know if you want me to dive deeper") as examples of what to avoid. If the validator scans the whole document it will fail the build on its own coaching copy. Pass it the answer strings explicitly; do not walk the finished document.
- **H3 (keyword construction).** `StoryAnswerParts(spoken=item.answer)` is constructed with the keyword `spoken=` at `scripts/build_detailed_interview_guide.py:1679`. Since `spoken` becomes a read-only property/alias for `full`, migrate this construction (and any like it) to `full=item.answer`.
- **M1 (complete the rollout).** Five sites read `answer.spoken`: lines 441 (inside `add_story_answer`), 568 (behavioral bank), 888 (company-fit bank), 1867 (story page), and 2240. Upgrading only `add_story_answer` leaves the layered boxes appearing in one place while the other four render flat. Enumerate all five and decide per site: route through the layered renderer or intentionally keep flat (document which and why).
- **M3 (limit cheat-sheet blast radius).** Keep Phase 1 edits to `scripts/build_interview_cheat_sheet.py` limited to the new shared helpers the guide consumes (`meat_first_answer`, `story_stretch_modules`, `story_pushback_branches`, alternate framing) plus the AI-answer swap. Do not re-script the cheat sheet's own rendering in this phase; that file is very large and a full rewrite is unnecessary for the guide to embody the principles.
- **Regression guard.** `scripts/smoke_test.py` asserts on `.spoken` content (lines 4302, 4348: no inline coaching labels, hook clause present). Ensure `full` preserves those properties so the alias keeps those tests green.

## Design North Star: the Bumbling-to-Boardroom Principles

Every scripted answer this generator produces must embody the delivery principles from the companion coaching document (`output/Christian Estrada - Public Speaking Transformation Plan.docx`). The guide and the speaking plan are one system: the plan teaches the habits, the guide supplies pre-built answers that already obey them. Codex should treat these six principles as acceptance criteria, not decoration. If a rendered answer violates one, it is a defect.

1. **Meat first.** The result or point lands in the first one or two sentences of every answer, at every length. The outcome is never reachable only at the end, and never requires an interviewer prompt to surface. (This is the direct fix for the debrief's "interviewers had to ask for the outcome.")
2. **Stretch by stacking, not wandering.** Longer answers are the short answer plus labeled modules that each end on a point. No version reaches its length by adding backstory or warm-up.
3. **Signpost.** Longer answers and multi-part answers open with a one-line frame ("Two parts: the problem, then what I changed" / "Result first, then how we got there").
4. **No hedging.** Scripted text never contains the debrief's flagged qualifiers: "I guess," "I think," "kind of," "let me know if you want me to dive deeper," "I could give a more specific example." The guide models declarative language so Christian rehearses declarative language.
5. **Declarative landing.** Every answer ends on a result or a point, never on a qualifier or an offer to keep talking. The closing sentence is a period, not a question.
6. **Composed pushback.** Each hero story ships with scripted, one-line-then-stop replies to its likely challenges, so a follow-up never triggers a spiral.

A `validate_delivery_principles(text)` check (reuse `validate_text` at line 453) should flag any scripted string that contains a banned hedge phrase or ends on an offer-to-continue, and fail the build. This makes principles 4 and 5 machine-enforced rather than aspirational.

## Confirmed Evidence Facts (do not exceed these)

All scripted content the generator produces must stay inside the confirmations already resolved with Christian. Codex must not let any new template introduce a claim beyond them.

- The two hero stories authorized with specifics (confirmed 2026-07-08):
  1. **Amazon Robotics warehouse certification (East West):** stood up a new warehouse facility in the ERP and passed Amazon's compliance and certification requirements before go-live; roughly six-month compliance and certification process; configured every product family, BOM, and component structure; coordinated with the CFO, plant controllers at every site, manufacturers, vendors, and Amazon's compliance team; achieved full Amazon Robotics certification and a live operational warehouse.
  2. **13-month modernization (Aptean vendor-side client):** discovered mid-engagement the customer's infrastructure was too outdated to run modern software; named it directly to leadership; required tens of thousands of dollars in hardware upgrades before implementation; engagement scoped at 4 to 7 months ran roughly 13 months; kept the customer confident, delivered a satisfied customer, and the extended timeline opened billable customization work.
- The four evidence confirmations from 2026-07-02 still cap ownership language (East West report portfolio, Aderant backup/recovery capped at "supported/performed," Azure DevOps/Git hands-on at Aptean only, Home Depot framed as contact center operations).
- The ODBC client-recovery story that appears in the debrief (inherited broken implementation, bad ODBC connection, misconfigured third-party integration, weekly cross-level meetings from CEO to data entry, resolved in roughly six weeks) is drawn from Christian's own account in the interview. It may be scripted at that level of detail, but Codex must not add metrics, dollar figures, or named systems that Christian did not state. If a template needs a number the source does not support, leave it qualitative.

Rule: if any new template string asserts evidence beyond the above, treat it as a blocker and require a fresh confirmation from Christian before shipping.

## Core Interfaces and Source Truth

Primary file: `scripts/build_detailed_interview_guide.py`.
Sentence and story helpers: `scripts/build_interview_cheat_sheet.py` (imported as `cheat`).

Anchors this spec depends on (verified against the current file on 2026-07-13):

- `class StoryAnswerParts` at line 92. Currently two fields: `spoken`, `coaching_note`.
- `add_story_answer(document, answer, *, prefix="")` at line 440. Renders a `StoryAnswerParts` today.
- `add_answer_box`, `add_tip_box`, `add_qa_card`, `add_subsection`, `add_body`, `add_bullet` (lines 331 to 402): the box and text primitives every new renderer reuses.
- `detailed_pitch` (925), `human_pivot_paragraph` (945): source prose for TMAY beats.
- `build_extended_tmay_sections` (994) and `add_extended_tmay_section` (1050): the fragment-list TMAY to be replaced by the time ladder.
- `story_sample_answer` (1605) and `behavioral_sample_answers` (1654): where per-story scripts are assembled; these gain the new fields.
- `add_pushback_section` (841): the global pushback list stays, but per-story branches are added inline at the story.
- `add_general_answer_operating_system` (2002): where the meat-first spine and stretch rules are documented for the reader.
- `build_document` (2081): section assembly and ordering.
- Helpers in `cheat`: `spoken_story_answer` (3292), `behavioral_answer_scripts` (3902), `join_answer_sentences`, `story_result_sentence` (216), `natural_voice_opening` (588), `pitch_career_arc_sentence` (552), `hero_stories` (2767).

## Implementation Changes

### Change 1 - Extend `StoryAnswerParts` into a layered script object

Replace the two-field dataclass with the structure below. Keep `spoken` as an alias/property returning `full` so nothing downstream breaks during migration.

```python
@dataclass
class StoryAnswerParts:
    full: str                                  # existing 60 to 90 second answer
    meat_first: str = ""                       # 20 to 30 second result-first core
    stretch_modules: list[tuple[str, str]] = field(default_factory=list)  # (label, add-on beat) to reach 2 to 3 minutes
    alternate: str = ""                        # same story reframed for a different question type
    pushback_branches: list[tuple[str, str]] = field(default_factory=list)  # (challenge, scripted reply)
    coaching_note: str = ""

    @property
    def spoken(self) -> str:                   # backward-compatible alias
        return self.full
```

Design rules for the content of each field:

- `meat_first` must state the outcome and the relevance in the first two sentences. Pattern: **[Result claim] + [one proof detail] + [one line tying it to this role].** No situation setup longer than a half sentence. This is the antidote to "interviewers had to prompt for the outcome."
- `full` stays the current 60 to 90 second STAR/CART answer but must **open with the `meat_first` claim**, then add situation, action, and a closing result restatement. The result is stated twice: once up front, once to close. It is never only at the end.
- `stretch_modules` are optional, self-contained add-on beats, each labeled (for example "Stakeholder depth," "What I noticed early," "Why it was hard," "Transfer to this role"). Christian inserts one or two of these only when he has time, and each ends on a point so a dropped module never leaves the answer unfinished. This is the mechanism for "stretch without going on a tangent": expansion is modular, not improvised.
- `alternate` reframes the same facts to answer a different prompt (for example the Amazon Robotics story answers both "tell me about a complex cross-functional project" and "tell me about a time you had to earn trust with stakeholders who outranked you").
- `pushback_branches` script the two or three most likely challenges to that story and a calm, specific reply to each.

### Change 2 - Build the story scripts in `story_sample_answer`

Extend `story_sample_answer` (1605) and the non-special-case return so it populates the new fields. The existing `cheat.spoken_story_answer` output becomes `full`. Add three helpers in `cheat` (mirroring the existing sentence-builder style so they compose with `join_answer_sentences`):

- `meat_first_answer(card, profile, company_name, role_title)` -> result-first two-sentence core. Compose from `story_result_sentence(card.result)` first, then one evidence detail, then `interview_role_bridge_sentence(...)`.
- `story_stretch_modules(card, profile)` -> ordered list of `(label, sentence_block)`. Draw labels from what the card already carries: `card.level3_trait` becomes "What I noticed early," `card.evidence` list becomes "Stakeholder depth" or "Scope," and `profile.core_problem` becomes "Transfer to this role."
- `story_pushback_branches(card, profile, role_title)` -> list of `(challenge, reply)`. Seed with generic-but-specific challenges keyed off the card's story types (see the worked bank in Change 6), overridable per active playbook (State Farm, Big Four, and any future lane playbook).

The State Farm and Big Four branches in `story_sample_answer` get the same treatment so their calibrated bridges and questions still render, now as part of the layered object rather than one flat `spoken` string.

### Change 3 - Render the layered script in `add_story_answer`

Rewrite `add_story_answer` (440) to render, in this fixed order, only the fields that are populated:

1. `add_answer_box(document, answer.meat_first, label="SAY THIS FIRST (20 to 30 sec):")`
2. `add_answer_box(document, answer.full, label="FULL ANSWER (60 to 90 sec):")`
3. If `stretch_modules`: `add_subsection(document, "Stretch to 2 to 3 minutes (add one or two, each ends on a point):")` then one `add_tip_box` per module labeled with its name.
4. If `alternate`: `add_answer_box(document, answer.alternate, label="ALTERNATE FRAMING (different question, same story):")`
5. If `pushback_branches`: `add_subsection(document, "If they push back:")` then one `add_qa_card(prompt=challenge, answer=reply)` per branch.
6. If `coaching_note`: keep the existing small-body render at the end.

Use the existing box primitives so styling stays consistent with the rest of the guide. No new visual system is required.

### Change 4 - Replace the TMAY fragment list with a time ladder

This is the highest-value change for the "tell me about yourself with a 4-minute cap" problem. Replace `build_extended_tmay_sections` (994) with a builder that returns a single ladder where each rung is the previous rung plus labeled modules, so Christian can hit any cap by adding or dropping modules rather than starting a different answer.

New function `build_tmay_ladder(profile, company_name, role_title, job_description, resume_text, notes_text) -> TmayLadder`, where `TmayLadder` carries:

- `anchor` (the 20 to 30 second core): one sentence naming what he does and the through-line, one sentence of headline proof, one sentence of why this role. This is the meat, and it is identical across every version so the point never moves.
- `sixty` modules: add `career_arc` (one sentence) and `why_this_role` bridge.
- `two_min` modules: add one hero **proof beat** (the strongest story compressed to three sentences: result, what made it hard, outcome) and the `why_i_care` human line.
- `four_min` modules: add a **second proof beat** (the other hero story, same three-sentence shape), one "range" line that names the breadth of environments he has worked across, and a forward-looking close that hands the conversation back.

Render with a new `add_tmay_ladder_section` that prints:

- A one-line rule at the top: "The first 20 seconds are identical in every version. Length is added by stacking labeled modules, never by delaying the point."
- `SAY THIS FIRST (about 30 sec)`: the anchor, as an answer box.
- `IF YOU HAVE 60 to 90 sec, ADD`: career arc + why-this-role, as tip boxes.
- `IF YOU HAVE 2 MIN, ADD`: proof beat 1 + why I care.
- `IF YOU HAVE 4 MIN, ADD`: proof beat 2 + range line + forward-looking close.
- A `COMPRESS RULE` tip box: "If the interviewer looks ready to move on, stop after the current module and end on the why-this-role line. Never open a module you cannot finish in the time left."

Each proof beat must be a self-contained three-sentence unit ending on the result, so dropping the last beat under time pressure still leaves a clean answer. Keep `detailed_pitch` and `human_pivot_paragraph` as the prose sources; this change is about structure and layering, not new claims.

### Change 5 - Document the delivery operating system for the reader

Extend `add_general_answer_operating_system` (2002) with two short, explicit subsections so the guide teaches the mechanics, not just the theory:

- **Meat-first spine (say this in this order every time):** (1) the answer or result in one sentence, (2) one proof detail, (3) one sentence on why it matters for this role, then stop or expand. Include the sentence: "If the interviewer still does not know your point by sentence two, restart shorter."
- **Stretch without tangent:** "To make an answer longer, add a labeled module from the story's stretch list, not more backstory. Each module is a mini-answer that ends on a point. When in doubt, add the 'transfer to this role' module and stop."

Also add a one-line **anti-hedge rule** wired to the debrief: "Delete these on the way out of your mouth: I guess, I think, kind of, let me know if you want me to dive deeper, I could give a more specific example. State the claim, then stop."

### Change 6 - Worked answer bank (reference content for the templates)

The strings below are the target output quality. Codex should use them as the shape the helpers must produce for the two confirmed hero stories and the ODBC recovery, and as fixture text for tests. They stay inside the confirmed facts above.

**TMAY anchor (identical in every version):**
> "I'm a systems and ERP implementation specialist, and the through-line of my career is taking messy, high-stakes rollouts and getting them to actually work for the people who live in them. Most recently I led an ERP warehouse certification that had to pass Amazon Robotics compliance before go-live, coordinating everyone from the CFO to plant controllers to Amazon's own compliance team. That's why this role interests me: piloting new solutions in a complex stakeholder environment is exactly the work I'm best at."

**TMAY proof beat 1 (Amazon Robotics, three sentences, result-first):**
> "The clearest example is a new warehouse we had to stand up in the ERP and certify against Amazon Robotics requirements before it could go live. What made it hard was that certification touched every product family, BOM, and component structure, and it meant aligning the CFO, plant controllers at every site, outside manufacturers, and Amazon's compliance team on the same standard. We passed certification and brought a live, operational warehouse online, which is the kind of end-to-end ownership I'd bring to your pilots."

**TMAY proof beat 2 (13-month modernization, three sentences, result-first):**
> "Another one: I inherited an implementation scoped for four to seven months and discovered partway in that the customer's infrastructure was too outdated to run the software at all. I named that directly to their leadership, which was not the comfortable message, and we invested in the hardware upgrades first before touching the implementation. The engagement ran about thirteen months, the customer stayed confident the whole way, and the extended scope actually opened new billable customization work."

**ODBC recovery, meat-first (20 to 30 sec):**
> "I once took over a client implementation that was already broken and the client was ready to walk. I reverse-engineered it down to a bad ODBC connection and a misconfigured third-party integration, ran weekly working sessions with everyone from their CEO to their data-entry staff, and had it stabilized in about six weeks. It's the ambiguity-to-plan pattern your team runs on."

**ODBC recovery, full (opens on the result, then situation and action, closes on result):**
> "The short version: I inherited a failing client implementation and had it stable in about six weeks. Here's what happened. The build predated me, the client was unhappy, and no one had root-caused it, so I started by reverse-engineering the whole setup rather than guessing. That surfaced two real problems, a bad ODBC connection and a third-party integration that had been configured incorrectly. Because the fix crossed IT, data, and leadership, I ran a weekly working session that deliberately spanned every level, from the CEO down to the data-entry team, so decisions and information moved in the same room. About six weeks in, the connection and integration were corrected and the relationship was stabilized. That reverse-engineer-then-align-everyone approach is how I turn an ambiguous, inherited mess into a plan people trust."

**ODBC recovery, stretch modules:**
- "What I noticed early: the loudest symptom was not the real problem, so I resisted the pressure to patch and insisted on tracing it to root cause first."
- "Stakeholder depth: putting the CEO and the data-entry staff in the same weekly session was deliberate, because the people closest to the data usually see the failure the executives cannot."
- "Transfer to this role: piloting emerging solutions for public agencies is the same shape, an ambiguous starting point, mixed stakeholders, and a need for one accountable path through it."

**ODBC recovery, pushback branches:**
- Challenge: "Six weeks sounds slow for a connection fix." Reply: "The connection itself was quick to correct once we found it. Most of the six weeks was earning back a client who had lost trust and making sure the third-party integration would not fail again, which mattered more than raw speed." (Note to Codex: keep this qualitative; Christian stated roughly six weeks total but did not break out how long the connection fix alone took, so do not assert a specific sub-duration.)
- Challenge: "Why did you need the CEO in a working meeting?" Reply: "I did not need them every week, but early on I needed the authority in the room to unblock decisions fast. I scaled their involvement down as soon as the path was clear."
- Challenge: "What would you have done differently?" Reply: "I would have asked for the original configuration documentation on day one instead of week two. I assumed it existed; it did not, and reverse-engineering earlier would have saved a few days."

**Sourcewell AI-usage answer (meat-first), included because the debrief flags it as required and it stays inside true practice:**
> "I use AI as a first-draft and analysis accelerator, never as the final word. Concretely, I use it to draft first-pass documentation, summarize long stakeholder inputs, and pressure-test my own analysis, then I review and correct every output before it goes anywhere. My rule is that AI speeds up the work but a human owns the result, which I understand is exactly how your team runs it."

If Christian has not confirmed a specific AI tool and workflow, keep this qualitative and flag it for confirmation rather than naming tools he did not claim.

### Change 7 - Guardrail validation

Add `validate_scripted_answer(parts: StoryAnswerParts, allowed_claims) -> None` called from `behavioral_sample_answers` after assembly. It should fail the build if a scripted field introduces a number, dollar figure, or named system not present in the story card's confirmed evidence. Reuse the existing `validate_text` machinery (453) rather than inventing a new validator. This keeps the richer scripts from drifting past the confirmed facts.

## Section Ordering in `build_document`

Insert the new TMAY ladder where the extended TMAY currently sits, and keep the layered story scripts inside the existing behavioral and story sections. Suggested order near the front of the guide:

1. Delivery operating system (meat-first spine, stretch rule, anti-hedge rule) - moved up so the reader internalizes the mechanics before the scripts.
2. Tell Me About Yourself: time ladder.
3. Hero story scripts (layered, with pushback branches).
4. Company-fit and behavioral banks (now layered).
5. Global pushback list, hidden-assessment grid, final-round strategy (unchanged).

## Test and Acceptance Plan

1. Unit: `build_tmay_ladder` returns an anchor identical across the 30, 60, 120, and 240 second renderings, and each longer rung is a strict superset of the shorter one.
2. Unit: every `StoryAnswerParts` for a hero story has non-empty `meat_first`, `full`, at least two `stretch_modules`, and at least two `pushback_branches`.
3. Unit: `meat_first` and `full` both contain the result sentence, and `full`'s first sentence matches the `meat_first` claim (result stated up front, not only at the end).
4. Guardrail: `validate_scripted_answer` raises on a fixture that injects an unconfirmed metric.
5. Render: build the guide for the Sourcewell posting in `jobs/job_description.txt`, open the Word document, and confirm the SAY THIS FIRST, FULL ANSWER, stretch, alternate, and IF THEY PUSH BACK boxes all render with the correct labels and no empty boxes.
6. Regression: existing guides (State Farm, Big Four playbooks) still build, and the `spoken` alias keeps any untouched caller working.

## Sequencing and Gates

1. Change 1 (dataclass + alias) first, behind the alias so nothing breaks.
2. Change 2 and 3 (assemble + render story scripts) together, gated by tests 2 and 3.
3. Change 4 (TMAY ladder) gated by test 1.
4. Change 5 (reader-facing operating system text).
5. Change 7 (guardrail) gated by test 4.
6. Full render (test 5) and regression (test 6) before merge.

## Assumptions

- The `cheat` sentence helpers can be extended without disturbing the cheat sheet output; the new helpers are additive.
- Playbook modules (State Farm, Big Four) remain the override path for calibrated bridges and questions.
- Worked strings in Change 6 are Sourcewell-flavored examples of target quality; the generator produces role-specific equivalents from the same structure, it does not hardcode Sourcewell.
- No claim in any new template exceeds the confirmed evidence facts; anything that would must be routed back to Christian for confirmation first.
