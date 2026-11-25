# Copy-paste installation prompt

Paste this into the chat of a working Hermes agent (for example the Hermes
web chat on your VPS):

```text
Set up the bookkeeping system from https://github.com/techwithtim/hermes-accounting-starter for me. Clone it into ~/apps/hermes-accounting-starter, then open SETUP.md in that folder and follow it step by step. Stop and ask me whenever it says a step is mine, and never ask me to paste an API key into this chat.
```

Everything else (install, dashboards, Gmail connection, first scan and the
recurring jobs) is written out for the agent in [SETUP.md](../SETUP.md).

What you do yourself during setup:
1. Sign up for Composio and save your API key with one command over SSH.
2. Click the Gmail link and approve Google consent.
3. Approve the first scan before recurring jobs are created.

Want Google itself to enforce read-only? That is an optional stricter setup
with your own Google OAuth app; see [COMPOSIO.md](COMPOSIO.md).

The Hermes agent must already have working model access. Composio and model
usage are billed by those providers.
