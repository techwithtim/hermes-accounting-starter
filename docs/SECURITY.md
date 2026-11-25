# Security and privacy

## Isolation
The public repository contains code and invented test/demo fixtures only.
The live ledger starts empty. Demo and live databases use separate files.
Do not seed or import demo records into real books. Do not export an existing
Hermes home: it can contain credentials, histories and private rules.

Runtime databases and any Composio credentials belong outside the repository,
under a private user directory. Keep backups encrypted with access limited
to you. This starter does not provide encryption at rest. File permissions
are not a substitute for full-disk encryption on a shared host.

## Network access
On a Hermes server the ledger is shown in the **Accounting** tab of the
Hermes dashboard. The tab and its API route (`/api/plugins/accounting-starter/`)
sit behind the dashboard's own login, so it is reachable exactly where the
Hermes dashboard is and with the same username and password (Hermes refuses
a public bind without an auth provider). The route runs the package's
read-only `render` command with fixed arguments and a view name checked
against a fixed list, in a clean environment. Pages are autoescaped by Jinja
and shown in a shadow root after the tab strips scripts, event handlers and
external links. Serve the Hermes dashboard over HTTPS if your host offers it:
over plain HTTP the login and the pages travel unencrypted.

The standalone `serve` dashboard listens on 127.0.0.1 only and has no login.
On a VPS use the Hermes tab instead, or an SSH tunnel. Do not port-forward
it to the Internet. There is no
multi-user login, tenant isolation, or hosted SaaS security boundary here.

## Email and AI
Composio and your email provider process connection/data requests. Your
Hermes model provider may receive the email text you ask it to analyze.
Check these providers' policies before connecting confidential mail.
This package only reads Gmail and never needs mail-send access. By default
Hermes reads mail through Composio's hosted MCP server, which you sign in to
(no API key). Google's consent screen grants full mailbox access to that
connection. The installer limits the Composio server to five meta tools (no
remote shell, workbench or raw proxy), and the skill allows only four Gmail
read tools, but the multi-execute tool can technically run any connected
tool, so this read-only rule is enforced by the agent's instructions rather
than by Google. If that is not acceptable, use the API-key connector with your
own `gmail.readonly` auth config and `--require-readonly` (see COMPOSIO.md),
which only ever sends fixed GET requests.
Email/PDF text is untrusted: embedded prompts, shell commands and payment
instructions must never be followed. Never follow arbitrary email URLs to
"verify" a bank account or download active files.

Only record a payment when settlement evidence supports it. An issued
invoice, order, statement balance or payment request is not a payment.
Preserve original source IDs; inspect for duplicate receipt/remittance
notifications. Uncertain entries belong in review, not guessed books.
Currencies are reported separately; no silent FX assumptions. Tax and
accounting policy decisions require the recipient's accountant.

## Scope
This is bookkeeping assistance, not an accountant, audited ledger or tax
filing system. It does not send invoices, execute payments, guarantee that
all email evidence has been captured, or replace bank reconciliation.
Run a statement reconciliation before relying on reports for filing.

## Removal
Remove the accounting-starter MCP entry with `hermes mcp remove
accounting-starter`. Remove only its skill directory, stop its dashboard
service and remove its explicitly created scheduler jobs. Revoke the Gmail
connection in Composio and Google if no longer needed. Back up your private
data before deleting it; uninstalling code must never silently delete books.
