# Claude Review: Validation, Federal Granularity, and Spec Hygiene (Final)

Review pass only. No source files were modified.

---

## Verdict

Approved as written. One correction to a number I gave you, with the accurate figure below so the `ORPHAN_TEST_ALLOWLIST` can be seeded correctly rather than discovered during implementation.

---

## Correction: 18 orphan tests, not 86

My earlier "86-function gap" was the arithmetic difference between `def test_*` count and a regex match on `lambda ... test_x(` registry entries. That regex was wrong: zero-argument tests are registered as bare references, `("AGENTS word budget", test_agents_word_budget)`, not as lambda calls. Most of the gap was my detection method, not real.

Re-derived by counting whole-word occurrences of each test name across the whole module and keeping those that appear exactly once (their own definition):

```
total test definitions:  467
true orphans:             18
```

The full list, ready to seed the allowlist:

```
test_supply_chain_summary_stays_in_lane_context
test_retention_analytics_summary_meets_minimum_word_count
test_title_phrase_candidates_do_not_cross_comma_title_segments
test_clorox_style_job_title_and_specialties
test_multiline_job_title_extraction_with_bom
test_supply_chain_analytics_summary_promotes_supported_delivery_terms
test_proof_first_opening_avoids_list_density_with_comma_heavy_core_problem
test_cover_letter_prose_check_text_strips_header_before_quality_eval
test_standard_cover_trim_enforces_body_sentence_cap_even_within_word_budget
test_xml_page_estimate_shrinks_with_compact_separator_font
test_targeted_competency_guardrail_rejects_titles_and_bare_nouns
test_retained_competencies_preserve_jd_required_source_skill
test_recent_interview_question_classification_and_factual_scripts
test_recent_interview_question_prep_renders_spoken_answers
test_business_context_question_section_separates_answer_from_coaching
test_story_natural_reference_avoids_meta_announcement_language
test_contains_search_term_handles_simple_plural_forms
test_run_resume_workflow_parse_args_accepts_resume_only
```

Two implications for the plan:

**18 is small enough to fix rather than allowlist.** The plan frames the allowlist as visibility during the refactor, not a cleanup project, which was the right call at 86. At 18 you may prefer to simply register them and skip the allowlist entirely. Your call — but check them before registering, since a test that has never executed may not pass.

**One of them is directly relevant to this remediation.** `test_contains_search_term_handles_simple_plural_forms` is a test for the exact plural-tolerant predicate the alignment work depends on. It is defined and never runs. Register that one regardless of what you decide about the other seventeen, and confirm it passes — it is currently the only written check on behavior this plan treats as settled.

**Detection method for the meta-check.** Use whole-word occurrence counting across the module rather than matching registry syntax. Registry entries come in at least two forms — bare references for zero-argument tests and lambdas for tests taking a module fixture — and any pattern that only recognizes one of them will report false orphans, exactly as mine did.

---

## Nothing else outstanding

Every prior finding is resolved, scoped out, or recorded in Assumptions, including the `apply_selection_visibility()` dedup, the constant-offset `resume_candidate_quality()` behavior, the federal-only `build_coverage_report()` consumers, both coverage-report call sites, runtime-derived counts, and the packet-builder context set.

The acceptance gate — one completed `python tasks.py validate` with a recorded pass count and wall-clock duration — remains the single artifact this remediation has never produced. Everything else has been spot-checked; that run is what converts spot checks into a verified system.
