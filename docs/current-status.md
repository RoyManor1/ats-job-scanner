# Current status and evidence

**Last independent verification: 12 October 2026, before completion of the current release sprint.** This is a dated snapshot, not a live status page.

## Three different states

| Part | Status at this checkpoint |
|---|---|
| Public source in `src/` and `workflow/` | September reference implementation; unchanged by this documentation update |
| Working October pilot | Daily scheduled automation with separate collection, description retrieval, assessment and delivery records |
| Next release, v12 | Under revision after independent review; final deployment and runtime acceptance have not been independently verified |

The public workflow does not reproduce all the October behavior. In particular, do not assume it contains the newer application handling, source holds, run-health reporting or $2 budget guard. Its default schedule is 07:30; the working October pilot is scheduled for 07:00, both in Asia/Jerusalem.

## Verified run: 12 October 2026

Codex inspected the n8n execution records through the browser, including the stored scanner result and Gmail send result.

| Observation | Meaning and limit |
|---|---|
| 398 sources read completely, zero collection failures | Collection succeeded for the active source groups in this run. This is not a claim of 398 distinct companies or exhaustive coverage of every opening. |
| 86 jobs assessed; $0.6508 recorded model cost | One run's assessment cost. This excludes n8n and other service subscriptions and is not a daily average. |
| 15 cards shown; Gmail confirmed sent | Delivery succeeded. The 15 cards are not 15 independently verified good matches. |
| Grain — AI Builder was relevant to my search | My own feedback on one recommendation, not an application or hiring outcome. |
| Run status: `partial_sent` | The email was sent despite unresolved description retrieval gaps. |

There were **23 unique postings without usable descriptions**, retried once each. That produced 46 unsuccessful attempts out of 227 description-fetch attempts. Their sources, Opti and Daisy, were withheld from the digest. No alert was sent: the configured threshold was more than 25% of attempts, with a minimum of 20 attempts. The observed rate was 20.26%.

The source snapshot contained **122 held sources**. “Held” means collected but not yet eligible for recommendations. It is not additional verified recommendation coverage.

## What the review established

The later published selector repair, version `acda5006`, was downloaded from n8n and matched the supplied implementation. Existing regression suites passed when pointed at the relevant files. The morning run above occurred before that later publication; it does not establish a scheduled run of that version.

Independent tests then reproduced five issues in the v12 candidate:

1. Descriptions could be truncated before the eligibility checks read them.
2. A model's unsupported quote could validate its own “no experience required” claim.
3. Company-history wording could be mistaken for a candidate requirement.
4. Support-role filtering could reject work whose main responsibilities were not reactive support.
5. Early stops could produce inconsistent or negative health counters.

These are reproduced test cases, not confirmed evidence that a relevant live recommendation was lost. Their final repairs and the resulting release are still awaiting independent acceptance.

## What is still open

- Complete and review the filtering, evidence wording and health-counter repairs.
- Verify the final deployed version and an actual scheduled run.
- Release ready sources in stages within the assessment budget.
- Continue work on unsupported readers and distinguish fixable gaps from unavailable sources.
- Publish a sanitized implementation update after the current release has been reviewed.

The coverage audit also identified 31 companies needing reader implementation and seven with external blockers. Those are recorded gaps, not completed integrations. A planned first batch of 12 held sources is not counted here as released.

## Reproducing the public reference

On 12 October, the public repository's fixture harness was rerun in a separate local copy and completed with `ALL CODE NODES PASS`. It uses mocked inputs and responses and does not establish current endpoint availability, live model quality or October production behavior. See [reference setup](reference-setup.md).

Operational review evidence was checked against local review packages, supplied workflow exports and n8n records. Private account exports, application records, credentials and personal scoring context are not included here. The public status summary reports their relevant aggregate observations; it is not a publicly reproducible production audit.
