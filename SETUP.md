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
- Never ask for, accept or repeat an API key in chat. If the person pastes
  one, tell them to revoke it in Composio and make a new one.
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

## 4. Composio API key (the person does this)

**Ask the person** to:

1. Sign up at https://dashboard.composio.dev and copy their project API key.
2. Open an SSH terminal on this machine (not this chat) and run:

   ```sh
   cd ~/apps/hermes-accounting-starter && uv run python -m accounting_starter.composio_email configure
   ```

   and paste the key at the hidden prompt.

Wait until they say it is done. Your own terminal cannot type into that
prompt; if you run a Composio command before the key is saved it stops with
the same instruction.

## 5. Connect Gmail

Generate an owner ID with `python3 -c 'import uuid; print(uuid.uuid4())'`,
then, from the checkout, make the connection link:

```sh
uv run python -m accounting_starter.composio_email connect --user-id OWNER_ID
```

Write the owner ID and the returned `connected_account_id` to
`~/.local/share/hermes-accounting-starter/connection.md` (mode 600). Give
the person the `redirect_url` and **ask them** to open it, sign in to
Google and approve. Tell them: Google will say the app can read, send and
delete mail, because that is what Composio's shared Google app asks for,
but this package only ever reads.

When they say they approved, run this (from here on, put the real IDs from
`connection.md` in place of OWNER_ID and CA_ID):

```sh
uv run python -m accounting_starter.composio_email status --user-id OWNER_ID --connected-account-id CA_ID
```

Email is connected only when it shows `"ready": true`. Then fetch one small
real sample to prove it works (keep the file private, outside the checkout):

```sh
install -d -m 700 ~/.local/share/hermes-accounting-starter/mail
uv run python -m accounting_starter.composio_email fetch --user-id OWNER_ID --connected-account-id CA_ID \
  --query 'newer_than:1d has:attachment' --max-pages 10 \
  --output ~/.local/share/hermes-accounting-starter/mail/check-$(date +%s).json
```

## 6. First scan (review only)

Start a new Hermes session or reload MCP so the `accounting-starter` tools
and skill are loaded. Load the `accounting-starter` skill and scan the last
seven days of mail. Show the person what you found. **Do not book anything
yet.** Ask them to approve or correct it.

## 7. Recurring scans (only after approval)

Once the person approves the first scan, create the hourly capture and
daily review jobs exactly as described in `docs/AUTOMATION.md`, with the
real checkout path, data directory and connected account ID filled in.
Confirm `hermes cron status` shows a running scheduler (if not, follow the
fix in that file) and show the person the job IDs.

## 8. Wrap up

Tell the person, in a short list: the dashboard addresses and tunnel
command, that Gmail is connected, the job IDs, and anything that was
blocked or skipped.
