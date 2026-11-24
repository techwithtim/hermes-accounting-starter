# Copy-paste installation prompt

Paste this into an already configured Hermes agent with terminal access
(for example the Hermes web chat on your VPS):

```text
Install the bookkeeping system from
https://github.com/techwithtim/hermes-accounting-starter
into ~/apps/hermes-accounting-starter. Read README.md, AGENTS.md and
docs/SECURITY.md first. Do not read, copy, migrate or alter any existing
accounting system, private rules, memories, credentials or other Hermes
profiles.

Check Python 3.11+, uv, git and Hermes. If uv is missing, install it with
Astral's official installer (curl -LsSf https://astral.sh/uv/install.sh | sh)
and then run: source ~/.local/bin/env. Clone the repository, inspect
scripts/install.py, run python3 scripts/install.py --dry-run, then run
python3 scripts/install.py for my active HERMES_HOME. Keep the default data
directory (~/.local/share/hermes-accounting-starter), never inside the repo.
Do not overwrite existing MCP entries or customized skills.

From the checkout, create the separate fictional demo with
uv run accounting-starter --demo demo. Check the MCP server with
hermes mcp test accounting-starter. Start the live dashboard on port 8766 and
the demo on port 8765 (uv run accounting-starter serve --port 8766 and
uv run accounting-starter --demo serve --port 8765) and confirm that
curl http://127.0.0.1:8766/health says "live" and 8765 says "demo". If either
port is taken, pick a free one and tell me. This is a VPS, so give me the
exact SSH tunnel command for my laptop. Offer to keep the dashboard running
with the systemd user service in docs/DEPLOYMENT.md.

Then connect my email following docs/COMPOSIO.md. Walk me through creating my
own Composio account and API key. I will save the API key myself over SSH with
the configure command, never in this chat. Then run connect without an auth
config ID (Composio's one-click Gmail login), give me the link, wait for me to
approve Google consent, and check status and one small real fetch before
saying email is connected. Tell me that Google will show a full mailbox access
screen but this package only reads mail.
Use a random UUID as my owner ID and save it, with my connected account ID,
in ~/.local/share/hermes-accounting-starter/connection.md.

Load the accounting-starter skill, run one review-first scan of the last
seven days, and show me what you found. Do not book anything yet. After I
approve, create the hourly scan and daily review jobs from docs/AUTOMATION.md,
confirm hermes cron status shows a running scheduler, and show me the job IDs.
Clearly report anything blocked. Never send emails, make payments, expose the
dashboard publicly, or put demo records into my real books.
```

What the person still does by hand (no prompt can do these for them):
1. Sign up for Composio and create an API key.
2. Run the `configure` command over SSH to save that key privately.
3. Click the connection link and approve Google consent.
4. Approve the first scan before recurring jobs are created.

Want Google itself to enforce read-only? That is an optional stricter setup
with your own Google OAuth app; see [COMPOSIO.md](COMPOSIO.md).

The Hermes agent must already have working model access. Composio and model
usage are billed by those providers.
