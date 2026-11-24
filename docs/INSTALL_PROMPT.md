# Copy-paste installation prompt

Replace `<PUBLIC_REPOSITORY_URL>` with this repository's published HTTPS URL.
Use this in an already configured Hermes agent with terminal access:

```text
Install the bookkeeping system from <PUBLIC_REPOSITORY_URL> in a new,
dedicated local directory. Read README.md, AGENTS.md and docs/SECURITY.md
first. Do not read, copy, migrate or alter any existing accounting system,
private rules, memories, credentials or other Hermes profiles.

Check Python 3.11+, uv, git and Hermes availability. Install missing software
using its official installer only with my approval when needed. Clone this
repository, inspect scripts/install.py, run its --dry-run, then install with
python3 scripts/install.py targeting my active HERMES_HOME. Use a runtime
data directory outside the repository. Do not overwrite existing MCP entries
or customized skills. Install the locked dependencies, including Composio.

Initialize an empty live ledger and a separate fictional demo. Test the MCP
connection in a new session, launch the localhost-only dashboard, and give
me its local URL (or the SSH tunnel steps if this is a VPS). Keep the app
running using the documented service setup when supported.

Follow docs/COMPOSIO.md. Guide me through creating my own Composio account,
API credential and read-only Gmail auth configuration, then generate my
connection link. Ask me to enter secrets in a private terminal prompt, NOT
in this conversation. Wait for my OAuth consent. Verify connection and one
real fetch before saying email is connected. Never use someone else's keys.

Load the accounting-starter skill, run one review-first scan, and show me the
results. Then create the opt-in hourly scan and daily review jobs described
in docs/AUTOMATION.md after confirming the email account, scope and schedule
with me. Do not claim a scheduled job exists until its ID has been verified.
Clearly report anything blocked, including permissions or OAuth. Do not send
emails, initiate payments, expose this dashboard publicly, or ingest demo
records into my real books.
```

A prompt cannot perform signup, OAuth consent or provide free model/API usage.
The existing Hermes must already have its own working model access. The
package installs Composio's SDK; the recipient supplies their own account.
