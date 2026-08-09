# Codex Spec: Federal Grade-Match, Shared True Evidence, and Competency Coverage

## Context
Christian is applying to Department of Education IT Project Manager, GS-2210-14 (needs
GS-13-equivalent specialized experience in 2 of 3 duties). Review found true, GS-relevant
accomplishments stranded only in `Federal_Standard_Essays.json`, not in the structured
federal source, so the two-page resume cannot surface them. Christian confirmed the specifics
and attribution (below). This pass captures that true material into the structured sources
(federal AND commercial), corrects one metric, adds the required competency coverage, and
makes the grade match explicit. The two-page federal cap stays. Federal content is certified
under penalty, so apply the confirmed wording exactly; do not invent or embellish.

Phase the work and checkpoint. Do not run a blind full rebuild.

---

## Confirmed attribution (from Christian, use exactly)
- Cybersecurity mentoring = VOLUNTEER only: "Cybersecurity Track Lead" during a Grow With
  Google program under the Mentor Me Collective. MUST NOT appear in any paid work-experience
  bullet. Add ONLY as a clearly labeled volunteer entry, and keep it in the essays where it
  already lives.
- Zero-trust / incident-response = real paid work: East West (access governance and global-IT
  support for Aptean Intuitive) and the Aderant Interim Systems Administrator role (DR, backup,
  restore, recovery testing).
- Metrics = East West modernization: ~25% less unplanned downtime; decisions affecting
  $20M+ in daily inventory; ~32% lower INVENTORY SCRAP cost (not general "operational cost")
  from the inventory automation and tracking he built.

---

## Phase 1: capture true evidence + corrections (low risk, do first)

### 1a. Federal source (`source/Christian_Estrada_Federal_Source.json`)
- Enhance the East West security/governance bullet to make the true framing explicit, e.g.:
  "Applied zero-trust-aligned least-privilege access, role-based access controls, and dynamic
  permission frameworks for sensitive financial and inventory transactions, and supported
  incident-response readiness and access validation for the global IT team supporting Aptean
  Intuitive."
- Add an East West modernization-outcomes bullet, e.g.:
  "Led enterprise systems modernization that improved reliability and reduced unplanned
  downtime by roughly 25%, supporting reporting and decisions affecting $20M+ in daily
  inventory, and cut inventory scrap cost by about 32% through the inventory automation and
  tracking I designed." (Do NOT duplicate the existing 78% manual-processing / 22% discrepancy
  bullet; these are distinct outcomes.)
- Frame the Aderant Interim Systems Administrator entry as incident-response readiness:
  "Performed disaster-recovery planning, backup and restore, and recovery testing supporting
  incident-response readiness during an organizational transition." (Matches existing confirmed
  evidence; just make the incident-response framing explicit.)
- Add a labeled VOLUNTEER entry (not in paid work): "Cybersecurity Track Lead (Volunteer) -
  Grow With Google, Mentor Me Collective" with a one-line description of leading/mentoring the
  cybersecurity track. Place it in a Volunteer/Community section, clearly separated from paid
  Work Experience.

### 1b. Essay correction (`source/Christian_Estrada_Federal_Standard_Essays.json`)
- Everywhere it says "lowered operational costs by 30 percent" (or similar), change to
  "reduced inventory scrap cost by about 32 percent." Keep the scope precise (inventory scrap,
  not general operational cost). Leave the cybersecurity-mentoring example as the volunteer
  example it already is.

### 1c. Federal summary wording (`scripts/build_federal_resume.py` summary builder)
- Change the summary opener "Federal enterprise technology leader" to "Enterprise technology
  leader." Christian has no federal service; the word "Federal" there implies experience he
  does not have.

### 1d. Commercial source (BRIEF, per Christian's request)
The commercial resumes build from three docx in `source/`: `Estrada_Resume_Implementation.docx`,
`Estrada_Resume_PreSales_CSM.docx`, `Christian_Estrada_KPMG_Final_Tightened_EdFix.docx`
(see build_resume.py lines 307-317). Add the SAME true East West material to the East West
section of these source resumes, consistently:
- the modernization-outcomes bullet (roughly 25% less downtime; $20M+ daily inventory; ~32%
  lower inventory scrap cost), and
- the zero-trust / incident-response security framing on the governance bullet.
- Add the labeled volunteer line ("Cybersecurity Track Lead (Volunteer), Grow With Google -
  Mentor Me Collective") to the commercial master(s) as a volunteer entry.
Keep it brief and truthful; do not duplicate the existing 78%/22% metric. The commercial
selection/ledger will surface these where relevant.

### Phase 1 checkpoint
- Federal resume still resolves to exactly two pages with all mandatory fields (hours,
  salary, supervisor, dates) present; build passes.
- The security/modernization material and volunteer entry appear; essay reads 32% inventory
  scrap; summary no longer says "Federal ... leader."
- One commercial rebuild (a program/implementation lane target) shows the new metrics/security
  are available and the 20-run does not regress (spot-check 2-3 roles, not a blind 20).
- STOP and hand the federal resume + essay text to Christian for a final certification read
  before Phase 2.

---

## Phase 2: grade match + competency coverage (federal generator logic)

### 2a. Cover all nine basic competencies
The posting requires demonstrating EACH of nine competencies; the qualifications statement
currently addresses only four (Attention to Detail, Customer Service, Oral Communication,
Problem Solving). Add truthful, supported coverage for the missing five: Decision Making,
Information Management, Interpersonal Skills, Teamwork, Technical Competence. Draw each from
real experience already in the source (e.g., Decision Making from VP/director technology
tradeoff decisions; Information Management from SQL/BI reporting and data governance; Teamwork
from cross-functional coordination without direct authority; Technical Competence from SQL,
ETL, access controls, ERP modernization; Interpersonal Skills from executive workshops/QBRs
and stakeholder alignment). Stay within the 3-page qualifications budget.

### 2b. Explicit GS-13 equivalence
Make the grade match explicit rather than implied. State that the most recent role is
equivalent to at least the GS-13 level and demonstrates 2 of the 3 specialized-experience
duties, in the specialized-experience response and/or the resume grade-equivalence line. Keep
the existing grade-equivalence validation intact.

### 2c. Two-page selection prioritization
When trimming to fit two pages, prioritize bullets that match the announcement's
specialized-experience duties and KSAs, so the newly captured Duty-2 material (security,
modernization, incident response) actually surfaces. This directly answers the existing
warnings that supported experience is "not clearly visible in the selected 2-page resume."
Do not weaken the two-page cap or the mandatory-field blockers; trim optional content, never
a mandatory header.

### Phase 2 checkpoint
- Qualifications statement explicitly and truthfully addresses all nine competencies within
  3 pages.
- Resume/response explicitly states GS-13 equivalence and the 2-of-3 duties.
- The two-page resume surfaces at least one clear Duty-1, one Duty-3, and now Duty-2
  (security/modernization) bullet; mandatory fields still present; still exactly two pages.

---

## Phase 3 (queued, lower priority): Executive Order citation safety
The EO essay hardcodes specific Executive Orders (13985, 14028) that may be rescinded or
superseded across administrations. Do not auto-assert specific EO numbers. Either reference
the posting's stated priorities and agency mission generically, or emit a build warning that
the cited EOs must be verified as currently in effect for the target administration before
submission. Christian supplies the verified EOs per cycle.

---

## Phase 2 execution discipline (learned the hard way on the commercial side)
Phase 1 is certified and approved by Christian; Phase 2 may proceed. The two-page duty
prioritization is the delicate part; apply these rules so it does not turn into a loop:
- No subjective-quality build-abort assertions. The build must never fail because a duty is
  "not visible enough." Machine gates are objective only: resume PASS, exactly two pages,
  mandatory-field blockers, quals within 3 pages, all nine competency labels present.
- Fit by rating priority, then accept drops. If Duty 1, 2, and 3 evidence cannot all fit in
  two pages alongside the mandatory headers, keep the highest rating-value bullets
  (specialized-experience duties first) and let the least-critical optional content drop.
  Do NOT thrash trying to fit everything; report which duties surfaced.
- Circuit breaker: if the objective checkpoint fails after 2 build attempts, STOP and report
  the specific failure for a human decision. Do not keep tuning autonomously.
- Fast inner loop: iterate on focused federal tests; run the full smoke/validate/source-lint
  suite once before the commit, not after every tweak.
- Nine competencies must be truthful and specific, drawn from real source experience, not the
  generic fallback template. If a competency has no honest support, note it rather than
  padding.

## Guardrails
- Truthfulness first: apply only Christian-confirmed content; volunteer work stays labeled
  volunteer and never enters paid bullets; the 32% figure is inventory scrap, scoped exactly.
- Federal content is certified: after Phase 1, Christian reads and confirms the wording before
  Phase 2.
- Keep the two-page federal cap, the mandatory-field blockers, and all existing validations.
- Commercial change is additive and brief; do not regress the 20-run.
- One focused commit per phase. Do not stage generated outputs, active jobs/ files, or spec
  docs.
