# Commercial Resume Queue

Put one commercial job posting in each ordinary `.txt` file in this folder.

- Example job: `ringcentral_tsm.txt`
- Optional application-question sidecar: `ringcentral_tsm.questions.txt`
- Do not combine multiple postings in one file.
- Queue files stay in place and are never moved or deleted automatically.

Run the full workflow for every queued posting:

`python tasks.py resume-queue`

Run resumes only:

`python tasks.py resume-queue --resume-only`

Rebuild entries that would otherwise be skipped:

`python tasks.py resume-queue --rerun`

Jobs run sequentially. A failed or timed-out job does not stop later jobs. State, logs, and manifests are written under `scratch/commercial_queue/`.
