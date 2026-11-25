# Setup instructions for the Hermes agent

You are a Hermes agent setting up this bookkeeping package for the person
you are chatting with. Follow these steps in order. Where a step says
**ask the person**, stop and wait for their reply before going on. Keep
your messages to them short and plain, and give them commands they can
copy exactly.

## Ground rules (apply to every step)

- Work only in `~/apps/hermes-accounting-starter` (the checkout) and
  `~/.local/share/hermes-accounting-starter` (the data). Do not read, copy,
  move or change any other accounting system, memory, credentials, MCP
  entries, skills or Hermes profiles.
- Never ask for, accept or repeat a password, API key, sign-in code or
  sign-in redirect address in chat. If the person pastes one, tell them to
  revoke it (or sign in again) and not to share it.
- Never send email, pay anything, expose the dashboard publicly, or put
  demo records into the real books.
- If a step fails, say what failed and what you tried. Do not guess around it.

## 1. Check the machine

Confirm `python3 --version` is 3.11 or newer, and that `git` and `hermes`
work. If `uv` is missing, install it and load it into this shell:

```sh
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.local/bin/env
```

## 2. Install

If the checkout does not exist yet, clone it:

```sh
git clone https://github.com/techwithtim/hermes-accounting-starter ~/apps/hermes-accounting-starter
```

Then, from the checkout, read `AGENTS.md` and `docs/SECURITY.md`, and run:

```sh
cd ~/apps/hermes-accounting-starter
python3 scripts/install.py --dry-run
python3 scripts/install.py
uv run accounting-starter --demo demo
hermes mcp test accounting-starter
```

`hermes mcp test` should report 10 tools. The installer refuses to
overwrite an existing `accounting-starter` MCP entry or a customized skill;
if that happens, stop and tell the person.

## 3. Start the dashboards

From the checkout, run each in the background (or offer the systemd service in
`docs/DEPLOYMENT.md` so they survive a reboot):

```sh
uv run accounting-starter serve --port 8766
uv run accounting-starter --demo serve --port 8765
```

Check that `curl -s http://127.0.0.1:8766/health` contains `"live"` and
`curl -s http://127.0.0.1:8765/health` contains `"demo"`. If a port is
taken, pick a free one and say which.

The dashboards only listen on this machine. If it is a server, give the
person this command to run on their laptop, filled in with the real user
and host, then tell them to open http://localhost:8765 (demo) and
http://localhost:8766 (their books):

```sh
ssh -N -L 8765:127.0.0.1:8765 -L 8766:127.0.0.1:8766 USER@HOST
```

## 4. Sign in to Composio (the person does this)

The installer already registered Composio's MCP server as `composio`
(check with `hermes mcp list`). Signing in needs the person, because your
terminal cannot answer the sign-in prompt. **Ask the person** to:

1. Create a free account at https://dashboard.composio.dev if they do not
   have one.
2. Sign Hermes in to it, either way:
   - **Hermes dashboard:** open the MCP servers page, find `composio` and
     click **Authorize**, or
   - **SSH terminal on this machine:** run `hermes mcp login composio`, open
     the link it prints on their laptop, sign in and approve, then copy the
     full address the browser ends up on (the page will fail to load; that
     is expected) and paste it back into the terminal.

Wait until they say it is done, then run `hermes mcp test composio`. It
should connect and list 5 tools. If it says sign-in is still required, ask
them to try again. Never ask for a password, code or link from that step in
this chat.

## 5. Connect Gmail

Start a new Hermes session (or run `/reload-mcp`) so the Composio tools are
loaded. Then call `COMPOSIO_MANAGE_CONNECTIONS` for the `gmail` toolkit. If
Gmail is not connected yet it returns a link: give it to the person and
**ask them** to open it, sign in to Google and approve. Tell them: Google
will say the app can read, send and delete mail, because that is what
Composio's Google app asks for, but this setup only reads, as the
`accounting-starter` skill requires.

When they say they approved, check the connection is ACTIVE, then read one
small real sample: `GMAIL_FETCH_EMAILS` through `COMPOSIO_MULTI_EXECUTE_TOOL`
with `query` `newer_than:1d` and `max_results` 5. Email is connected only
when that returns messages (or an empty inbox) without an error.

Write the Gmail connected account ID to
`~/.local/share/hermes-accounting-starter/connection.md` (mode 600). If the
person has more than one Gmail account in Composio, ask which one to use.

## 6. First scan (review only)

Load the `accounting-starter` skill (start a new session if it or the
`accounting-starter` tools are missing) and scan the last
seven days of mail. Show the person what you found. **Do not book anything
yet.** Ask them to approve or correct it.

## 7. Recurring scans (only after approval)

Once the person approves the first scan, create the hourly capture and
daily review jobs exactly as described in `docs/AUTOMATION.md`, with the
real checkout path, data directory and Gmail account ID filled in.
Confirm `hermes cron status` shows a running scheduler (if not, follow the
fix in that file) and show the person the job IDs.

## 8. Wrap up

Tell the person, in a short list: the dashboard addresses and tunnel
command, that Gmail is connected, the job IDs, and anything that was
blocked or skipped.
