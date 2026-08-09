# ATS Heading Review

Date: 2026-06-25

## Question

Does using `Core Competencies` instead of `Skills` create a meaningful ATS auto-rejection risk for Christian's commercial resume workflow?

## External Evidence

- No credible source was found showing that a compliant resume is auto-rejected solely because the skills section uses the label `Core Competencies` instead of `Skills`.
- Daxtra, a resume parsing vendor, explains that parsers extract structured data such as skills, work experience, and qualifications from free-form resumes, and that parsing quality depends on context, extraction rules, and parser accuracy across real data samples rather than one exact heading label.
  Source: https://info.daxtra.com/blog/2016/10/18/what-is-cvresume-parsing
- Business Insider quoted a recruiter in May 2024 saying many candidates overestimate ATS autonomy and that recruiters often reduce the pile with keyword filters and other variables.
  Source: https://www.businessinsider.com/why-your-resume-gets-rejected-job-search-bots-people-ats-2024-5

## Local Audit

- The commercial source resumes and recent generated commercial resumes expose the section heading as normal paragraph text inside `word/document.xml`; the heading is not being emitted as an image-only artifact.
- The commercial pipeline previously hard-coded the literal heading `Core Competencies` across section detection, formatting, ATS plain-text validation, comparison tooling, and smoke tests.
- The federal workflow already uses `Technical Skills`, so this review applies only to commercial resumes.

## Decision

- Keep the internal competency model and function naming intact where useful.
- Render the visible commercial resume heading as `Skills` going forward because it is the most standard ATS-facing label and matches the ATS-first preference.
- Preserve backward compatibility by allowing commercial validators, extractors, and audits to recognize both `Skills` and legacy `Core Competencies`.

## Practical Takeaway

The bigger ATS risks in this repo were formatting, plain-text extraction, and keyword placement, not the phrase `Core Competencies` by itself. The heading was still standardized to `Skills` as a conservative commercial-output choice.
