# Codex Implementation Spec: Interview Stage Selection + Interviewer Context (Authoritative)
## July 13, 2026 - Let Christian pick the interview stage before building a guide, or get one guide with all stages, plus an optional paste-in for who is interviewing him

## Summary

Today `python tasks.py guide` builds one detailed interview guide from `jobs/job_description.txt` with no notion of which interview stage it is for. A recruiter screen, a hiring-manager one-on-one, a peer panel, a panel presentation or case, and a final-round conversation need different emphasis, different answer lengths, and different question banks. Christian wants two things:

1. **Stage selection.** Tell the builder which stage the interview is (HR screen, hiring manager, panel, panel presentation or case, technical, final), and get a guide tuned to that stage. Selecting nothing, or selecting `all`, produces one comprehensive guide with a clearly separated section per stage, so he can prep every round from a single document.
2. **Interviewer context paste-in.** An optional file where he pastes who he is interviewing with (names, titles, tenure, what they emphasized, recruiter feedback, panel format), which the guide uses to add an interviewer-specific prep section and to sharpen anticipated questions.

Both must obey the existing guardrails: stay inside Christian's confirmed evidence and stories, and embody the Bumbling-to-Boardroom delivery principles (see `Claude Review/CODEX_SPEC_SCRIPTED_INTERVIEW_GUIDE_20260713.md`). Interviewer context is rehearsal context, never a source of new resume claims.

Claude planned this; Codex implements, runs, and validates locally, per the two-pass workflow.

## Review Findings to Build In (Claude review, 2026-07-13)

- **H1 (optional params + federal regression).** The new `stage` and `interviewer_context` parameters on `build_detailed_interview_guide_for_inputs(...)` MUST be optional (default `stage` resolves to `all`, `interviewer_context` defaults to an empty context). The federal guide calls this function directly at `scripts/build_federal_detailed_interview_guide.py:17`; required params would break it. Add a federal-guide build to the Phase 2 regression tests, not just State Farm and Big Four.
- **M2 (filename-suffix composition).** The output filename already injects `FAIL` / `POOR` / `BRIDGE` from the resume audit state in `build_detailed_interview_guide()` (around lines 2394 to 2402), and `build_detailed_interview_guide_for_inputs` derives a draft path via `question_prep.application_question_draft_path` and `question_prep.mark_docx_as_draft`. The stage suffix must compose with both, producing for example `Christian Estrada - <target> FAIL Detailed Interview Guide (HR Screen).docx`, and the draft-path derivation must still resolve correctly from the suffixed name. Pin the exact insertion point (append the stage suffix after the `Detailed Interview Guide` stem, before `.docx`) and confirm no tracker or filename-audit breakage.

## Core Interfaces and Source Truth

Anchors verified against the canonical repo (`C:\dev\Christian-Resume-System`) on 2026-07-13:

- Input constants in `scripts/build_detailed_interview_guide.py`: `JOB_DESCRIPTION` (line 54), `COMPANY_RESEARCH` (55), `INTERVIEW_NOTES` (56).
- `notes_context(company_research, interview_notes)` (485) and `add_recent_interview_question_prep_section(...)` (521): where pasted context is turned into guide content today.
- `build_document(company_name, role_title, job_description, resume_docx, output_docx)` (2081): assembles the sections.
- `build_detailed_interview_guide()` (2385) and `build_detailed_interview_guide_for_inputs(...)` (2414): entry points; the first computes the output filename and reads inputs.
- `main()` (end of file): no argument parsing today.
- `tasks.py`: the `"guide"` Task (line 219) runs `scripts/build_detailed_interview_guide.py` with no args; `run_task` (849) already forwards extra args via `command = (sys.executable, *task.args, *extra_args)` (857), so `python tasks.py guide --stage hr_screen` can pass through once the script parses it.
- `run_detailed_interview_guide.bat`: uses `choice` prompts and calls `:run_task interview` then `:run_task guide`.

## Change 1 - Add a stage taxonomy and a new `scripts/interview_stage.py`

Create `scripts/interview_stage.py` with a `StageProfile` dataclass and a `STAGE_PROFILES` registry. Stages:

| key | label | what it optimizes for |
|---|---|---|
| `hr_screen` | HR / Recruiter Screen | crisp background, why-company, why-leaving, comp range handling, availability and logistics, high-level fit, 2 to 3 smart questions |
| `hiring_manager` | Hiring Manager 1:1 | role fit, depth of the hero stories, how he thinks, first-90-days, gap pushback |
| `panel` | Peer / Team Panel | behavioral breadth, collaboration and cross-functional stories, culture fit, per-interviewer angles |
| `presentation` | Panel Presentation / Case | a structured solution walkthrough or case: discovery to recommendation framework, slide or whiteboard structure, Q&A defense |
| `technical` | Technical / Case Deep-Dive | role-specific technical and scenario anticipation, translating technical detail into business outcomes |
| `final` | Final / Executive | motivation, long-term fit, vision, executive presence, close and comp |
| `all` | All Stages (default) | one guide with a labeled section per stage above |

`StageProfile` fields (each stage sets these):

```python
@dataclass(frozen=True)
class StageProfile:
    key: str
    label: str
    banner: str                      # one-line "what this round is really testing"
    default_answer_seconds: tuple[int, int]   # e.g. (30, 60) for hr_screen, (60, 90) for hiring_manager
    sections: tuple[str, ...]        # ordered section keys to render for this stage
    salary_mode: str                 # "answer_when_asked" | "defer" | "negotiate"
    include_presentation_module: bool
    question_emphasis: tuple[str, ...]  # which question-bank categories to foreground
```

Add resolution helpers:

- `resolve_stage(cli_stage, interviewer_context, stage_file) -> StageProfile` with precedence: `--stage` flag > a `Stage:` line inside the interviewer-context paste > `jobs/interview_stage.txt` > default `all`. Unknown values fail with a clear message listing valid keys.
- `stage_filename_suffix(profile) -> str`: returns `""` for `all`, else ` (HR Screen)`, ` (Hiring Manager)`, etc., so stage-specific guides do not overwrite each other or the comprehensive one.

## Change 2 - Wire stage selection through the entry points

- `main()` in `build_detailed_interview_guide.py`: add `argparse` with `--stage` (choices = the stage keys) and `--interviewer-context PATH` (optional override of the default file location). Keep `python tasks.py guide` with no flags working: no `--stage` means resolve from file or default `all`.
- `build_detailed_interview_guide()` (2385): read the new optional inputs (see Change 3 and 4), resolve the stage, append `stage_filename_suffix(profile)` to `output_name` before the `.docx`, and pass `profile` and the parsed interviewer context into `build_detailed_interview_guide_for_inputs`.
- `build_detailed_interview_guide_for_inputs(...)` (2414): add `stage: StageProfile` and `interviewer_context: InterviewerContext` params and forward them to `build_document`.
- `build_document(...)` (2081): add the two params. Branch section assembly on `stage.sections`. For `all`, render the current full section set, but wrap each stage-specific block under a labeled stage header ("HR / Recruiter Screen", "Hiring Manager 1:1", and so on) so the comprehensive guide is navigable. For a single stage, render only that stage's sections plus the shared core (delivery operating system, hero stories, interviewer prep).
- `tasks.py`: confirm the generic dispatch forwards `sys.argv[2:]` to `run_task` for `guide` (it does via `extra_args`); no structural change needed beyond making sure `guide` is not in an "extra args rejected" branch. Update the `"guide"` Task description to mention `--stage` and the interviewer-context file.
- `run_detailed_interview_guide.bat`: before `:run_task guide`, add a `choice /c 12345 /n /m "Interview stage? 1=HR 2=Hiring Mgr 3=Panel 4=Presentation 5=All "` and map the selection to `--stage hr_screen|hiring_manager|panel|presentation|all`, then call `:run_task guide --stage <value>`. Default (no choice) is `all`.

## Change 3 - Stage-conditional content

Each stage's `sections` and settings drive real differences, not cosmetic headers:

- **hr_screen:** background ladder capped at the 60 to 90 second rung, "know the company" block, why-company / why-leaving / most-relevant-experience short answers, a salary block in `answer_when_asked` mode (give a range, hand it back), an availability-and-logistics block, and 2 to 3 recruiter questions. Suppress the deep behavioral bank and technical anticipation.
- **hiring_manager:** full hero-story scripts, first-90-days, role-fit and gap pushback, `defer` salary mode.
- **panel:** behavioral breadth across multiple story types, collaboration and cross-functional emphasis, plus the per-interviewer prep from Change 4 foregrounded.
- **presentation:** render the presentation/case module (Change 5) and a longer default answer length.
- **technical:** role-specific technical/scenario anticipation with the "every technical answer lands as a business outcome" rule made prominent.
- **final:** motivation and long-term-fit answers, executive-presence section, `negotiate` salary mode, concise high-conviction lengths.
- **all:** every block above, each under its stage header.

The delivery operating system, the meat-first spine, the hero-story scripts, and the interviewer-context prep render in every stage.

## Change 4 - Interviewer context paste-in

Add optional input `jobs/interviewer_context.txt` (constant `INTERVIEWER_CONTEXT` next to the others at lines 54 to 56). Christian pastes freeform, with light optional structure the parser recognizes:

```
Stage: panel
Format: 45-minute panel, then 15 minutes of my questions
Interviewers:
- Carrie Bowman, Director of Solution Development, 12 years, owns the team, cares about delivery and client trust
- Molly Taubery, Director of Innovation Pilots, 3.5 years, peer team, cares about fast ramp
Recruiter feedback: last round my answers ran long and buried the outcome
What they emphasized: pilot programs, ambiguous implementation, AI with human review
```

Add an `InterviewerContext` dataclass and `parse_interviewer_context(text) -> InterviewerContext` in `interview_stage.py`, extracting: an optional `Stage:` line (feeds `resolve_stage`), a `Format:` line, a list of interviewers (name, title, optional tenure, optional free-note), and any `Recruiter feedback:` / `What they emphasized:` lines. Parsing must be tolerant: a bare list of "Name, Title" lines works; the labeled fields are optional.

Render a new **Interviewer-Specific Prep** section (via a new `add_interviewer_prep_section`) that, for each named interviewer:

- restates their name and title,
- infers a likely focus from title keywords only (for example a title containing "Director of Solution Development" maps to "delivery, structured problem-solving, client trust"; "Innovation" maps to "speed, experimentation, comfort with ambiguity"; "Technical" or "Engineer" maps to "technical credibility translated to business value"). Keep these inferences generic and clearly framed as "likely cares about," never as asserted facts about the person.
- names which hero story to lead with for that interviewer, and
- suggests one tailored question to ask them.

Also fold `What they emphasized:` terms into the existing anticipated-question logic (reuse `notes_context` at 485 and `add_recent_interview_question_prep_section` at 521 so the emphasized language raises the matching questions), and surface `Recruiter feedback:` as a one-line "what to fix from last round" callout at the top of the guide.

Guardrail: the interviewer context is rehearsal context. It must never introduce a new claim about Christian's experience, and inferences about interviewers must stay at the "people in this kind of role usually care about" level. Do not fabricate biographical facts about a named person.

## Change 5 - Presentation / case module

For `presentation` (and included in `all`), render a `add_presentation_case_module` section with a reusable structure Christian can drop any prompt into:

- A discovery-to-recommendation spine: current-state, the constraint, options considered, the recommendation, the business case, the risks and mitigations, the ask.
- A slide or whiteboard skeleton (5 to 7 beats) matching that spine.
- Q&A defense: how to take a challenge, restate, answer in one line, and offer depth only if invited (the composed-pushback principle applied to a live audience).
- A time-boxing note tied to the stage's default length.

Content stays role-agnostic in structure and pulls the specifics (company, role, hero proof) from the existing profile, so it works for any posting, not just the current one.

## Guardrails Recap

- Every scripted answer still obeys the six Bumbling-to-Boardroom principles and the `validate_delivery_principles` check from the companion spec.
- No stage or interviewer input may introduce a claim beyond Christian's confirmed evidence and stories.
- Stage-specific filenames must not overwrite the comprehensive guide or each other.

## Test and Acceptance Plan

1. Unit: `resolve_stage` honors precedence (flag > context `Stage:` line > `interview_stage.txt` > default `all`) and rejects unknown keys with a helpful message.
2. Unit: `stage_filename_suffix` yields distinct suffixes so `guide --stage hr_screen` and `guide --stage panel` produce different filenames and neither overwrites the `all` guide.
3. Unit: `parse_interviewer_context` handles the full labeled sample, a bare "Name, Title" list, and an empty file without error.
4. Render: `python tasks.py guide --stage hr_screen` for the current `jobs/job_description.txt` produces an HR-focused guide (short ladder, salary-when-asked, logistics, recruiter questions) with no deep behavioral bank.
5. Render: `python tasks.py guide` (no flag) still produces the comprehensive `all` guide, now with per-stage headers.
6. Render: with `jobs/interviewer_context.txt` populated, the guide shows an Interviewer-Specific Prep section naming each interviewer, a likely-focus line, a lead story, and a tailored question, plus the recruiter-feedback callout at the top.
7. Regression: existing State Farm and Big Four playbook guides still build; the default path is unchanged for anyone not using the new inputs.

## Sequencing and Gates

1. `interview_stage.py` with `StageProfile`, `STAGE_PROFILES`, `resolve_stage`, `stage_filename_suffix`, `InterviewerContext`, `parse_interviewer_context` (gated by tests 1 to 3).
2. Entry-point wiring: argparse in `main`, reads and resolution in `build_detailed_interview_guide`, param passthrough to `_for_inputs` and `build_document`, filename suffix (gated by tests 2, 4, 5).
3. Stage-conditional section assembly in `build_document` (tests 4, 5).
4. Interviewer prep section and presentation module (tests 6).
5. `.bat` stage prompt and `tasks.py` description update.
6. Full render matrix and regression (tests 4 to 7).

## Assumptions

- File-based inputs (`jobs/interview_stage.txt`, `jobs/interviewer_context.txt`) match the existing `jobs/*.txt` convention and are the primary path; the `--stage` flag and the `.bat` prompt are conveniences layered on top.
- Default behavior with no new inputs is the comprehensive `all` guide, so nothing breaks for existing runs.
- Stage profiles are additive; new stages can be registered in `STAGE_PROFILES` without touching `build_document` beyond a new section key.
- Interviewer inference stays generic and non-biographical, consistent with the confirmed-facts guardrails.
