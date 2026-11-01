# Current status and evidence

**Last checked: 1 November 2026.** The latest live release is deployed and completed an end-to-end run with confirmed email delivery. This page is a dated snapshot.

## Live system and public code

The live system runs in n8n at 07:00 Asia/Jerusalem. It separates collection, description retrieval, assessment and delivery. The release checked here uses rules revision `r2r5-2026-11-01`.

The code under `src/` and `workflow/` remains the **September reference implementation**. This documentation update does not turn it into an export of the live system. Its setup, 07:30 default schedule and earlier scoring rubric are described in [reference setup](reference-setup.md). Newer application handling, source holds, classification rules and the $2 per-run guard belong to the live system.

## Verified run: 1 November 2026

Codex inspected the stored n8n execution results and Gmail send result after Claude deployed the release. The full verification run started at 11:59 Israel time and finished at 12:10. It used the daily runner; it was a release verification, not the morning's scheduled run.

| Observation | Result |
|---|---|
| Active sources checked | 427 |
| Sources read completely | 423 |
| Failed or incomplete sources | 4 |
| Open postings in the scanner | 4,672; 4,061 after removing duplicate copies |
| Selected for eligibility checks | 78 |
| Excluded before model assessment | 58 |
| Assessed by Claude | 20; zero final assessment failures |
| Model cost | $0.2403, within the $2 per-run limit |
| Email contents | 6 detailed job cards, 1 brief role listing, 2 existing application entries |
| Delivery | Gmail confirmed sent |
| Overall status | `partial_sent` |

The partial status reflects source failures and incomplete collection. Cybereason and Copperhelm failed; Daisy and CHEQ returned incomplete data. Those failures did not cause their postings to be marked closed. One open posting also remained unassessed because its description was unavailable after three attempts.

The cost is for this run's model use. It excludes n8n and other subscriptions. Delivery proves that the workflow sent the email, not that all six cards were good matches or led to applications.

## Coverage added in this release

- 29 source rows added. 28 passed collection and description checks and were released to the digest. CHEQ remains held.
- 106 existing held sources released after validation.
- 134 sources released in total: 106 existing plus 28 new.
- 435 source rows in the registry, of which 427 are active distinct sources.
- Active classifications: 135 cyber, 39 AI, 32 selected growth, 124 other and 97 unset.

These are source counts, not a count of unique employers or matching vacancies. “Active” means configured for monitoring. It does not guarantee a complete fetch on every run. The source inventory and the run's health results answer different questions.

## Behavior and checks

The release prioritizes operations, then SDR/BDR at cyber, AI and selected growth companies, then analytical and other roles. The order applies across fit bands and to the rendered email. An early-career fit label requires a fit score of at least 60. That score is an internal ranking, not a probability of getting hired.

SDR/BDR roles at companies outside the selected groups are excluded with a stated reason. If the company's classification is missing, the role goes to review. Saved, undelivered assessments receive the current rules when the digest is built, without another model call.

Codex reran the final node code against **13 assessment cases and 7 digest scenarios**. The checks covered score boundaries, company identity, missing classifications, saved assessments, ordering and card limits. The HTML card order matched the selected list in all seven digest scenarios. Codex also compared the source-table snapshots: only classification and release state changed in the original 406 rows.

Two missing application records were added after the release run. Codex confirmed the successful append in n8n. Claude read the table back and checked the live matching logic without sending another email: the records matched by job ID or full company and role name. A different role title remains a possible match rather than being assumed identical.

## Remaining limits

- Five sources are held out of recommendations: Copperhelm, Opmed.ai, Opti, Daisy and CHEQ.
- 97 active sources have no company classification yet. Their SDR/BDR roles go to review.
- Company discovery and source maintenance still require work. This is not complete coverage of the Israeli tech market.
- Broader discovery, contact enrichment and a weekly summary are outside this release.
- The updated live implementation has not been published as a sanitized, reproducible export in this repo.

The previous [12 October checkpoint](https://github.com/RoyManor1/ats-job-scanner/blob/413beec92d37ae0ba818c10f2cec7c3877cf7325/docs/current-status.md) remains in Git history. Its pending-release statements describe that earlier date.

The figures above come from operational records and local verification packages. Private application details, account exports and credentials are not published here. This is an aggregate report of those checks, not a publicly reproducible production audit.
