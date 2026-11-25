# Copy-paste installation prompt

Paste this into a new chat in a working Hermes agent (for example the Hermes
web chat on your VPS):

```text
Set up my bookkeeping system. I trust this repository, so do not audit its code or search the web. Run exactly: git clone https://github.com/techwithtim/hermes-accounting-starter ~/apps/hermes-accounting-starter 2>/dev/null || git -C ~/apps/hermes-accounting-starter pull --ff-only; cd ~/apps/hermes-accounting-starter && python3 scripts/install.py Then do exactly what ~/apps/hermes-accounting-starter/SETUP.md says, in order, and nothing else. Do not offer me alternatives or extra options.
```

The agent runs one install command, then follows [SETUP.md](../SETUP.md).

What you do yourself:
1. Click **Authorize** on the `composio` MCP server in the Hermes dashboard
   and sign in to Composio (free account; no API key).
2. Start a New chat when asked and paste the line Hermes gives you.
3. Open the Gmail link Hermes gives you and approve Google's screen.

Hermes then scans recent mail and shows you what it found before booking
anything. Composio and model usage are billed by those providers.
