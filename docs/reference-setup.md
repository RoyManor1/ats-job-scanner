# Run the September reference implementation

This repository contains an earlier version of Job Scanner. It is useful for exploring the original integrations and workflow structure. It is **not the current October pilot export**; see [current status](current-status.md).

## Run the offline fixture check

Requires Git and Node.js. No credentials or paid calls are needed.

```bash
git clone https://github.com/RoyManor1/ats-job-scanner.git
cd ats-job-scanner
node src/test_harness.js
```

The harness reads `workflow/job-scanner.workflow.json`, executes selected workflow code paths against fixtures and mocked model responses, and finishes with `ALL CODE NODES PASS` on success. It also overwrites `docs/sample-digest.html` with its fixture output.

That HTML is an older test artifact: it contains stub responses reused across different job titles. Its scores and explanations are not real recommendations. The README's [illustrative card](digest-preview.svg) is a separate, fictional presentation example.

## Explore or configure the workflow

Python 3 is needed to regenerate the JSON. An n8n instance and your own Google Sheets, Gmail and Anthropic configuration are needed for live use.

```bash
cp scoring_prompt.example.md scoring_prompt.md
# Edit the personal TODO sections in scoring_prompt.md.
python3 src/build_workflow.py
# Configure your own identifiers in src/make_export.example.py.
python3 src/make_export.example.py
```

The generator writes `workflow/job-scanner.workflow.json`. The export example writes the ignored `workflow/job-scanner.local.json` with your configuration. Keep your identifiers and credentials out of commits.

Import the local JSON into n8n and review the configuration before activation: recipient, model availability in your account, credentials, schedule, scoring prompt and assessment limits. The earlier export's unlimited scoring default does **not** provide the October pilot's $2 daily guard. Its filters are specific to the original Israel-focused search.

The reference uses two Google Sheets tabs:

- **Companies:** `company, ats, slug, type, active, il_jobs_on_scan_day, notes`
- **Seen:** `job_id, first_seen, company, title, location, url, source, posted_at, score, tier, role_family, seniority_read, why_fit, gap, angle, disqualifier, status`

The October pilot uses a broader record structure. Do not substitute this two-tab setup for the live pilot's schema.

## Files

| File | Purpose |
|---|---|
| `src/build_workflow.py` | Assembles the reference workflow, including embedded JavaScript |
| `src/fetch_workday.js` | Workday retrieval logic included by the generator |
| `src/test_harness.js` | Offline fixture checks against the generated workflow |
| `src/make_export.example.py` | Local configuration example |
| `workflow/job-scanner.workflow.json` | Committed reference workflow |
| `scoring_prompt.example.md` | Earlier scoring prompt template |
| `docs/ats-feeds.md` | Historical integration notes |
| `docs/israeli-tech-ats-directory.tsv` | Historical employer-to-ATS research; not the current active-source list |

Endpoint behavior and available models can change. Passing the offline fixture check does not verify external services or authorize enabling an unchanged example in production.
