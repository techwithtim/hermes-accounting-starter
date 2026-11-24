# Automatic scans with Hermes

The package supplies the connector, ledger tools and generic accounting skill.
Hermes does the interpretation; Composio does not classify receipts itself.
This requires a running Hermes scheduler with working model access. API/model
usage may incur charges. No email is read during installation.

## Enable after connecting
Ask Hermes to load `accounting-starter`, verify connector status and run the
first review-first scan. Confirm the account, lookback range, classification
policy and scan frequency. The installer prompt includes this handoff; you
do not need Discord or another chat integration.

Using Hermes's cronjob tool, first list existing jobs. Create or update two
jobs with names unique to this installation (never modify unrelated jobs):

- **Accounting Starter — hourly capture**: schedule `every 1h`.
- **Accounting Starter — daily review**: schedule `every 24h`.

Both use `skills: ["accounting-starter"]`. The job prompt must include the
actual checkout path, data directory, connected-account ID and the user's
approved policy. Keep delivery local unless the owner chooses a destination.
No secrets in job prompts: the connector reads its private credential file.

Hourly prompt template:

> Work only with the Accounting Starter installation at CHECKOUT and runtime
> directory DATA. Use its accounting-starter MCP tools, never another ledger.
> Fetch this owner's approved Gmail connection CONNECTION over the last seven
> days using the documented connector and a new private output file. Check
> pagination and retrieval success. Follow accounting-starter skill. Policy:
> REVIEW-FIRST unless the owner has explicitly authorized specific automatic
> classifications here. Deduplicate by original source IDs AND economic event.
> Queue uncertainty. Verify every write with read-back. Record actual coverage,
> success/failure and record IDs in DATA/scan-log.md. Do not report success if
> OAuth, a page or required attachment failed. Never send mail or make payments.

Daily prompt template:

> Review the Accounting Starter installation CHECKOUT, runtime DATA, connection
> CONNECTION. Read its recent scan log and ledger audit, invoices, expenses,
> payments and reviews. Check duplicate economic events, payment allocations,
> missing provenance and unresolved questions. Summarize separately by currency.
> Do not change uncertain entries or call email coverage bank reconciliation.
> Explicitly report failed/incomplete scans and items needing owner review.

Verify creation by listing the returned job IDs. Run the hourly job once and
inspect its completed result before declaring automation operational. A cron
job saved successfully is not proof that OAuth or extraction worked.

## Reliability
The overlapping seven-day window tolerates a short outage but is not a full
historical import. After a longer outage, explicitly backfill the missing date
range, using the same dedup rules. Only claim covered dates once every page
was fetched and reviewed. Repeating the same source cannot create another
record of the same kind, but different emails about one transaction still
require reasoning and review. Do not promise perfect autonomous accounting.

## Disable
List scheduler jobs and remove only the two IDs created for this installation.
Do not disable other accounting systems or unrelated schedules.
