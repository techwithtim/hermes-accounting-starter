# Setup instructions for the Hermes agent

You are setting up this bookkeeping package for the person you are chatting
with. Be quick: run the commands below as written. Do not read other files
in the repository unless a command fails. Keep messages to the person short.

**Rules:** touch only `~/apps/hermes-accounting-starter`,
`~/.local/share/hermes-accounting-starter` and what the installer registers.
Never ask for or accept a password, key, sign-in code or sign-in link in
chat. Never send email or pay anything. If a tool you need is missing, do
not work around it with `python -c`, `bash -c` or Hermes's own code: tell
the person what to do instead (usually step 3 below).

## 1. Install (one command)

```sh
git clone https://github.com/techwithtim/hermes-accounting-starter ~/apps/hermes-accounting-starter 2>/dev/null || git -C ~/apps/hermes-accounting-starter pull --ff-only
cd ~/apps/hermes-accounting-starter && python3 scripts/install.py
```

It installs everything (including the Accounting tab in the Hermes
dashboard and the Composio MCP server) and is safe to run again. If it
fails, show the person the last lines of the error and stop.

## 2. Hand over to the person

Send the person this, nearly word for word, then wait for them to reply:

> Installed. Two quick things for you:
> 1. In your Hermes dashboard (same address and login you already use),
>    open the **Accounting** tab to see your books. "Demo data" shows a
>    fictional example. If the tab is not in the menu yet, open your
>    dashboard address with `/api/dashboard/plugins/rescan` added to the
>    end once, then go back and refresh.
> 2. Connect Composio: open **MCP servers**, find **composio**, click
>    **Authorize** and sign in (create a free Composio account if you need
>    one). No API key needed.
>
> Then start a **New chat** and paste:
> `Continue the accounting setup from step 4 of ~/apps/hermes-accounting-starter/SETUP.md`

Stop here. The new chat is needed so Hermes loads the new tools.

## 3. If the Authorize button is missing or fails

Ask the person to open an SSH terminal on the server and run
`hermes mcp login composio`, open the printed link, sign in, then paste the
address their browser ends up on back into that terminal (the page itself
will not load; that is expected). Then continue with the New chat in step 2.

## 4. Connect Gmail (new chat starts here)

Load the `accounting-starter` skill. Call `COMPOSIO_MANAGE_CONNECTIONS` for
the `gmail` toolkit. If the Composio tools are missing, the sign-in did not
finish: go back to step 3. If Gmail is not connected yet, give the person
the link it returns and ask them to approve Google's screen. Tell them
Google will say the app can read, send and delete mail; this setup only
reads it.

When they say done, check the connection is ACTIVE and run
`GMAIL_FETCH_EMAILS` (through `COMPOSIO_MULTI_EXECUTE_TOOL`) with `query`
`newer_than:1d` and `max_results` 5 to prove it works. Save the Gmail
account ID to `~/.local/share/hermes-accounting-starter/connection.md`. If
they have more than one Gmail account in Composio, ask which one.

## 5. First scan (review only)

Scan the last seven days as the skill describes. Show what you found. Do
not book anything yet. Ask the person to approve or correct it.

## 6. Recurring scans (after approval)

Create the two jobs in `docs/AUTOMATION.md` with the real checkout path,
data directory and Gmail account ID, confirm `hermes cron status` shows a
running scheduler, and give the person the job IDs and a one-line summary.
