# Codex Spec: Sync and Expand the Generated Story Bank

> **STATUS: PARTIALLY SUPERSEDED.** Sections marked below were written before the eligibility architecture was measured and are now known to be wrong. The corrected approach: eligibility is gated on `question_prep.approved_source_resume_text()` (what Christian can defensibly claim), and the generated tailored resume is a **ranking** input only, never an exclusion gate. Measured eligibility for the current 18 cards: Procare generated resume 8/18, approved source 16/18, 18/18 after brittle-term repairs. Read the corrected sections in place; the card content, theme keys, story types, and lane lead-in material below remain valid.

Target files:

- `scripts/build_interview_cheat_sheet.py` (owns `StoryCard`, `expanded_story_bank()`, gating, theme keys, bridges)
- `scripts/build_detailed_interview_guide.py` (consumes `story_types`, story pages, selection table)
- `scripts/smoke_test.py` (regression coverage)
- `interview_prep/Christian Estrada - Project Delivery Interview Stories.md` (source of truth for content, already updated to 22 stories)

Do not rewrite either builder file. All changes below are additive or narrowly scoped edits.

---

## Background: what is actually out of sync

The markdown bank now holds 22 stories. `expanded_story_bank()` holds 18 `StoryCard` entries. The overlap is partial, not clean:

| Markdown story | Generator card | State |
| --- | --- | --- |
| 1 EFT/ACH | `EFT/ACH payment integration replacement` | in sync |
| 2 Warehouse + Amazon Robotics | `New warehouse and Amazon Robotics systems launch` | in sync |
| 3 Inventory automation | `High-volume inventory automation` | in sync |
| 4 $1M recovery | `$1M+ account stabilization` | in sync |
| 5 SMS channel | `Zero-to-one SMS support channel` | in sync |
| 6 Mexico sites | none | **missing** |
| 7 Parallel workstreams | none (partially inside the Robotics card) | **missing** |
| 8 Redirecting a churning account | none (distinct from the $1M card) | **missing** |
| 9 Data-migration setback | none (`Failure lesson and stronger validation` is a different event) | **missing** |
| 10 Acting on feedback | none | **missing** |
| 11 East West end-to-end | `East West ERP ownership` | **reframe needed** |
| 12 Aptean both-sides breadth | `Aptean rapid product learning` / `Aptean lifecycle delivery` | **reframe needed** |
| 13 through 22 | existing cards 5 through 17 | in sync (markdown was written from them) |

So the code needs five net-new cards and two reframes. Everything else is already represented.

---

## Blocker 1: silent evidence gating will drop the new stories

This is the highest-severity item and it must be handled before any card is added.

`supported_story_bank()` and `hero_stories()` both filter through:

```python
supported = [card for card in expanded_story_bank() if contains_all(resume_text, card.evidence_terms)]
```

`contains_all()` requires **every** term in `evidence_terms` to appear in the generated resume text. A card whose terms are absent is dropped with no warning, no log line, and no test failure. It simply never appears in any guide.

Verified against both source resumes (`source/Estrada_Resume_Implementation.docx`, `source/Estrada_Resume_PreSales_CSM.docx`). Note that gating actually runs against the **generated** resume text, which is a tailored subset of the source, so source presence is necessary but not sufficient. The "present" terms below were separately confirmed in three recent generated resumes in `output/`. One term that passes at source and fails in generated output is `stakeholder`, absent from the Advantive Technical Consultant resume. Treat that as the worked example of why source-level checking is not enough.

| Candidate term | Implementation | Pre-Sales / CSM |
| --- | --- | --- |
| `juarez` | absent | absent |
| `el paso` | absent | absent |
| `mexico` | absent | absent |
| `critical path` | absent | absent |
| `conflict` | absent | absent |
| `feedback` | absent | present |
| `training` | present | present |
| `adoption` | present | present |
| `migration` | present | present |
| `validation` | present | present |
| `cross-site` | present | present |
| `five sites` | present | present |
| `80+` | present | present |

The five new stories are exactly the ones whose natural evidence terms fail this test. If Codex writes `evidence_terms=("El Paso", "Juarez")` on the cross-cultural card, that story is dead on arrival in every generated guide, and nothing will report it.

### Fix 1a (SUPERSEDED, do not implement as written)

This section originally said to choose evidence terms that survive the generated resume. That treats a two-page layout constraint as a credibility test, which is backwards, and it is the root cause of the Procare defect below.

**Corrected:** gate eligibility on the approved source union. Use generated-resume presence only to boost ranking, so the guide leads with what the interviewer just read but never loses a story Christian can defend. The per-card `evidence_terms` values given later in this document are still correct as *safe, non-brittle* terms and should be used, but they are no longer load-bearing for exclusion.

**Why this matters, measured.** Audited against `output/Christian Estrada - Procare - Implementation Manager Resume.docx`, the interview that prompted this work: 10 of 18 cards were dropped, including four of the five headline stories (EFT/ACH, inventory 78/22, $1M recovery, SMS). Only Amazon Robotics survived from the headline five. The Procare prep guide was built from 8 stories, not 18. That is the real explanation for the stumble, not a gap in the bank.

Note also `build_interview_cheat_sheet.py:5742`, `if len(all_stories) < 6: fail(...)`. The system has been operating one or two cards above its own declared minimum for some time.

### Fix 1b (required): make the drop visible

Add a diagnostic so this failure mode cannot recur silently.

In `build_interview_cheat_sheet.py`, next to `supported_story_bank()`:

```python
def unsupported_story_cards(resume_text: str) -> list[tuple[str, tuple[str, ...]]]:
    """Cards excluded by evidence gating, with the terms that failed.

    Evidence gating is a silent filter: a card whose evidence_terms are absent
    from the generated resume never reaches any guide. This surfaces that so a
    story bank change cannot quietly disappear.
    """
    lowered = resume_text.lower()
    dropped: list[tuple[str, tuple[str, ...]]] = []
    for card in expanded_story_bank():
        missing = tuple(term for term in card.evidence_terms if term.lower() not in lowered)
        if missing:
            dropped.append((card.title, missing))
    return dropped
```

Call it in the cheat sheet build path and print a warn-only line (do not hard-fail; the gating is intentional, the silence is not). Match the existing warn-only pattern used by `utils.enforce_prose_quality()`.

---

## Blocker 2: new story types become dead metadata unless wired

`story_types` is a closed vocabulary consumed in at least nine places. The current set:

`Individual Achievement`, `Managing and Leading`, `Persuasion`, `Analysis and Decision`, `Challenge and Failure`, `Teamwork`, `Rapid Learning`, `Ambiguous Problem`, `Opposing Views`, `Customer Disagreement`, `Process Improvement`.

Note that `Process Improvement` is already dead metadata: it appears on the `East West Salesforce visibility` card but no consumer branches on it. Do not repeat that pattern.

The five new stories need three new types: `Cross-Cultural`, `Prioritization`, `Receiving Feedback`. Adding them to a card is not enough. Each requires consumers in **all** of these locations:

1. `build_interview_cheat_sheet.py` around line 892, `story_human_connection_line()` - add a branch per type.
2. `build_interview_cheat_sheet.py` around line 3515, the calibration-question chain - add a branch per type.
3. `build_interview_cheat_sheet.py` around line 3466, `six_story_type_lines()` - this tuple is hardcoded to six types and is the behavioral coverage table. Decide explicitly: either leave it at six and rename the function to reflect that it is a curated subset, or extend it. Recommended: leave the six, and add a separate `extended_story_type_lines()` covering the new three, so the existing one-page output does not grow unexpectedly.
4. `build_detailed_interview_guide.py` around line 1685, the `story_types` branch chain - add a branch per type.

Also add a module-level constant and assert against it so the vocabulary cannot drift again:

```python
KNOWN_STORY_TYPES = frozenset({
    "Individual Achievement", "Managing and Leading", "Persuasion",
    "Analysis and Decision", "Challenge and Failure", "Teamwork",
    "Rapid Learning", "Ambiguous Problem", "Opposing Views",
    "Customer Disagreement", "Process Improvement",
    "Cross-Cultural", "Prioritization", "Receiving Feedback",
})
```

---

## Blocker 3: `hero_stories()` returns only the top five

With 18 cards the selection pressure is already high. At 25 the new stories will almost never surface, because scoring is `signal_score(job_description, card.signals) + lane_bonus + quantified_story_boost(...)` and the new cards carry no boost entries.

Two changes:

1. Extend `lane_bonus_terms` so each lane can reach the new stories. Additions per lane are listed in the card table below under "lane signals."
2. Add a coverage guarantee. After the top-five sort in `hero_stories()`, ensure at least one `Challenge and Failure` card and one `Persuasion` or `Opposing Views` card are present. If neither is in the top five, swap the lowest-scoring card for the highest-scoring one of the missing type. Behavioral rounds always ask for both, and a top-five that is all delivery stories leaves a real hole.

---

## Blocker 4: `quantified_story_boost()` matches on title strings

```python
if title == "High-volume inventory automation":
```

Three hardcoded title comparisons. Any title edit silently zeroes the boost with no test failure. Before adding cards, add a `boost_key: str = ""` field to `StoryCard` and switch the comparisons to it. Keep the existing boost values identical so scoring does not shift; this is a refactor, not a behavior change. Verify by asserting the same card ordering for a fixed job description before and after.

---

## The five new cards

All content traces to the markdown bank. Do not paraphrase beyond what is written there, and do not add metrics that are not in the anchor facts.

### Card A: cross-site rollout to the Mexico teams

```
title="Cross-site rollout to the Mexico teams"
story_types=("Cross-Cultural", "Teamwork", "Managing and Leading")
boost_key="mexico_sites"
evidence_terms=("training", "adoption")
signals=("training", "adoption", "global", "stakeholder", "onboarding", "change", "enablement", "cross-site", "rollout")
```

Hook, noticing, action, result, and bridge come from markdown Story 6. Do not put "El Paso", "Juarez", or "Mexico" in `evidence_terms`; they are safe in `hook`, `evidence`, and `result` text, which is not gated.

### Card B: prioritizing parallel workstreams to a hard go-live

```
title="Parallel workstream prioritization"
story_types=("Prioritization", "Managing and Leading", "Ambiguous Problem")
boost_key="parallel_workstreams"
evidence_terms=("go-live", "training")
signals=("prioritization", "deadline", "delivery", "go-live", "sequencing", "critical path", "program", "workstream", "schedule")
```

From markdown Story 7. This overlaps the existing `New warehouse and Amazon Robotics systems launch` card, same event, different beat. Add both to `story_theme_key()` with distinct keys so `story_specific_bridge()` does not collapse them, and add a mutual-exclusion rule in selection: if both score into the top five, keep the higher scorer only and promote the next distinct card. Telling the same event twice in one interview is the exact failure this bank exists to prevent.

### Card C: redirecting a churning account without arguing

```
title="Redirecting a churning account"
story_types=("Customer Disagreement", "Persuasion", "Opposing Views")
boost_key="churn_redirect"
evidence_terms=("adoption",)
signals=("conflict", "disagree", "customer", "retention", "churn", "root cause", "adoption", "escalation", "account")
```

From markdown Story 8. Distinct from `$1M+ account stabilization`: that card is portfolio-level revenue protection, this is a single-account root-cause disagreement. Keep both, distinct theme keys.

### Card D: owning a data-migration setback

```
title="Data-migration setback and validation checkpoint"
story_types=("Challenge and Failure", "Analysis and Decision", "Rapid Learning")
boost_key="migration_setback"
evidence_terms=("migration", "validation")
signals=("failure", "mistake", "ownership", "data", "migration", "validation", "cutover", "checkpoint", "quality")
```

From markdown Story 9. Note the interaction with `story_for_type()`: that function hardcodes a preference chain for `Challenge and Failure`, currently `Customer loss and proactive success lesson` then `Failure lesson and stronger validation`. Extend the chain deliberately rather than leaving the new card unreachable. Recommended order, and the reasoning belongs in the comment:

1. `Data-migration setback and validation checkpoint` for implementation and delivery lanes, because the failure is inside the work the interviewer is hiring for.
2. `Customer loss and proactive success lesson` for customer success lanes, because it carries the proactive lesson and performed well in a real interview (Plataine, June 2026).
3. `Failure lesson and stronger validation` as the remaining fallback.

This means `story_for_type()` needs the lane passed in, or the preference needs to move to the caller. Passing the profile is cleaner; update the call sites at lines 2242, 2390 through 2394, 3476, and 4271 through 4273.

### Card E: acting on hard feedback about communication

```
title="Acting on hard communication feedback"
story_types=("Receiving Feedback", "Rapid Learning", "Individual Achievement")
boost_key="communication_feedback"
evidence_terms=("adoption",)
signals=("feedback", "coachability", "growth", "communication", "self-awareness", "weakness", "stakeholder", "executive")
```

From markdown Story 10. Do not use `feedback` as an evidence term: it is absent from the Implementation source resume, which is the default source. Do not use `stakeholder` either. It was checked against three recent generated resumes in `output/` and is absent from the Advantive Technical Consultant resume while present in the two Automation Direct resumes, so it is not a reliable gate. `adoption` survived in all three.

---

## The two reframes

### Reframe 1: East West end-to-end

The existing `East West ERP ownership` card frames the role as ownership and continuous improvement of a running platform. Markdown Story 11 frames it as an end-to-end implementation and migration, which is the stronger lead for implementation roles and is what Christian should open with.

Do not delete the existing card. Add a second card, `East West end-to-end ERP implementation`, with the Story 11 framing, and add a mutual-exclusion rule with the ownership card the same way as Card B. Rationale: the ownership framing is still the better fit for platform-ownership and administration postings, so both should stay reachable.

Add the layoff line as a new optional `StoryCard` field, `sensitive_note: str = ""`, carrying: `Position impacted by company reorganization.` Keep this consistent with the mandatory reorganization sentence in `.context/RULES_FOR_CLAUDE.md`. Render it in the detailed guide story page only, not in the cheat sheet.

### Reframe 2: Aptean both-sides breadth

The existing `Aptean rapid product learning` card covers the ramp. Markdown Story 12 covers something different and more valuable: the both-sides-of-the-table differentiator, which is Christian's opening hook. Add it as a distinct card:

```
title="Both-sides implementation breadth"
story_types=("Individual Achievement", "Rapid Learning", "Ambiguous Problem")
boost_key="both_sides_breadth"
evidence_terms=("80+", "migration")
signals=("breadth", "adaptability", "implementation", "vendor", "customer", "erp", "cloud", "on-premise", "regions", "differentiator")
```

This card should be reachable as an opener in every lane, so give it a lane bonus in all seven `lane_bonus_terms` entries.

---

## New feature: role-tailored lane lead-ins

Net-new. No equivalent exists in the code today.

Add to `build_interview_cheat_sheet.py`:

```python
@dataclass(frozen=True)
class LaneLeadIn:
    lane: str
    opener_boost_key: str
    proof_boost_key: str
    lead_in: str
    backup_boost_keys: tuple[str, ...]
    avoid_note: str = ""
```

Populate from the "Role-tailored lead-ins by lane" section of the markdown bank, which covers implementation and delivery, customer success and account management, program and project management, and solutions consulting and pre-sales. Map each to the existing `TARGETING_LANES` keys used in `lane_bonus_terms`: `implementation_delivery`, `customer_success`, `presales_solution`, plus `corporate_strategy`, `analytics_operations`, `change_enablement`, and `process_improvement`.

Note the mismatch: the markdown defines four lanes, the code has seven. Do not invent lead-ins for the three uncovered lanes. Fall back to the implementation lead-in for `change_enablement` and `process_improvement`, and to the pre-sales lead-in for `corporate_strategy`, and leave a comment saying these are fallbacks pending real content.

Render as a new section near the top of both the cheat sheet and the detailed guide, above the story pages. This is selection guidance, so it is only useful before the stories, not after.

Per `.context/RULES_FOR_CLAUDE.md`, adding a lane requires a matching `BRIDGE_EVIDENCE_AREAS` entry and a `questions_to_ask` lane case. No new lanes are added here, so that rule is satisfied, but confirm no lane key is introduced accidentally.

---

## Theme keys and bridges

`story_theme_key()` returns `"default"` for any unregistered title, which silently degrades the story to a generic bridge. Add entries for all seven new cards before adding the cards themselves, so no card ever ships unregistered:

| Card | theme key |
| --- | --- |
| Cross-site rollout to the Mexico teams | `cross_site_adoption` |
| Parallel workstream prioritization | `prioritization` |
| Redirecting a churning account | `churn_redirect` |
| Data-migration setback and validation checkpoint | `migration_setback` |
| Acting on hard communication feedback | `communication_feedback` |
| East West end-to-end ERP implementation | `east_west_end_to_end` |
| Both-sides implementation breadth | `both_sides_breadth` |

Add a matching entry in the `bridges` dict inside `story_specific_bridge()` and in the calibration-question chain. Then add a regression test asserting `story_theme_key(card) != "default"` for every card in `expanded_story_bank()`. That single test prevents the whole class of bug.

Note the ordering hazard in `story_theme_key()`: it matches on lowercase substrings in sequence, and `"migration"`, `"account"`, `"failure"`, and `"validation"` already appear in earlier branches. `Data-migration setback and validation checkpoint` will hit the existing `"failure" in lowered or "validation" in lowered` branch and return `"failure"` before reaching any new entry. Insert new checks **above** the existing generic ones, or switch to exact title matching via `boost_key`. Exact matching is preferable and is why `boost_key` is introduced in Blocker 4.

---

## Implementation order

Dependency-ordered. Do not reorder; several steps exist to make later steps safe.

1. Add `boost_key` and `sensitive_note` fields to `StoryCard` with empty defaults. Backfill `boost_key` on the three cards referenced in `quantified_story_boost()`.
2. Switch `quantified_story_boost()` from title comparison to `boost_key`. Verify identical card ordering for a fixed job description before and after.
3. Add `KNOWN_STORY_TYPES` and an assertion that every card's types are members.
4. Add `unsupported_story_cards()` and the warn-only diagnostic.
5. Convert `story_theme_key()` to `boost_key` matching, keeping existing return values byte-identical.
6. Add the three new story types and every consumer branch listed in Blocker 2.
7. Change `story_for_type()` to accept the profile and implement the lane-aware failure preference chain. Update all five call sites.
8. Add the seven new cards with theme keys and bridges registered in the same commit.
9. Add mutual-exclusion rules: Robotics vs parallel workstreams, East West ownership vs East West end-to-end.
10. Extend `lane_bonus_terms` and add the `hero_stories()` coverage guarantee.
11. Add `LaneLeadIn` and render the lead-in section in both builders.
12. Update `.context/SCRIPT_INDEX.md` with the new functions.

---

## Validation

Run in this order:

```
python scripts/smoke_test.py
python tasks.py validate
python tasks.py claude-packet --mode interview
```

Then a full build against a live posting and a visual check of the generated guides.

### Regression tests to add to `smoke_test.py`

1. **No unregistered theme keys.** For every card in `expanded_story_bank()`, assert `story_theme_key(card) != "default"`. This is the highest-value test in the set.
2. **No unknown story types.** For every card, assert `set(card.story_types) <= KNOWN_STORY_TYPES`.
3. **No dead story types.** For every member of `KNOWN_STORY_TYPES`, assert at least one card carries it. This catches the `Process Improvement` situation.
4. **Evidence gating reachability.** Assert every card passes against `approved_source_resume_text()` after the brittle-term repairs; target is 25/25. Do **not** assert every card passes against generated resumes, and do not use an allowlist: a card absent from a tailored resume stays eligible and simply loses its ranking boost. Separately assert that a source-supported card omitted from the tailored resume is still present in the pool, using the committed Procare fixture. Silent drops must be impossible in both directions.
5. **Unique boost keys.** Assert no two cards share a non-empty `boost_key`.
6. **Behavioral coverage.** For a representative job description per lane, assert `hero_stories()` returns at least one `Challenge and Failure` card and at least one `Persuasion` or `Opposing Views` card.
7. **Mutual exclusion.** Assert `hero_stories()` never returns both Robotics cards, and never both East West cards.
8. **Lane lead-in completeness.** Assert every key in `lane_bonus_terms` has a `LaneLeadIn`, and that every `opener_boost_key` and `proof_boost_key` resolves to a real card.
9. **Language rules.** Assert no new card text contains double dashes or first-person pronouns in fields that feed resume-adjacent surfaces. Story `evidence` fields intentionally use first person for spoken delivery, so scope this check to the fields that reach non-spoken output, and add a comment saying so.

### Manual checks

- Generate the detailed guide for an implementation posting and confirm the lane lead-in section appears above the story pages with the both-sides opener.
- Generate for a customer success posting and confirm the failure slot resolves to the customer loss story, not the migration setback.
- Confirm the layoff `sensitive_note` renders only in the detailed guide.
- Confirm total guide length has not blown past its previous page count; seven new cards will push it.

---

## Explicitly out of scope

- Do not touch resume or cover letter generation. No change here should affect `build_resume.py` output.
- Do not add new targeting lanes.
- Do not treat generated guides in `output/` as source material when checking behavior.
- Do not add metrics, clients, or outcomes beyond the anchor facts in the markdown bank.
