# Running on a VPS

The supported first target is Linux with Python 3.11+, uv and an already
configured Hermes agent. Composio handles the Gmail OAuth connection.
Hostinger-specific images may differ; this package does not assume a
particular port proxy or bypass their authentication.

## Run locally

```sh
uv run accounting-starter --demo demo
uv run accounting-starter --demo serve --port 8765
# For the empty live ledger instead:
uv run accounting-starter serve --port 8766
```

Global options go before the command. An optional `--data-dir /private/path`
selects runtime storage. Never choose a path under the public checkout.

The dashboard binds only to loopback. On your laptop:

```sh
ssh -L 8765:127.0.0.1:8765 your-user@your-server
```

Open http://127.0.0.1:8765 in your laptop browser. This is deliberately not a
public financial website. A hosted authenticated proxy is a separate setup.

## Keep the dashboard running
On a Linux host with user systemd available, adapt
`deploy/accounting-starter.service.example` to the actual absolute checkout
and runtime paths, save it as
`~/.config/systemd/user/accounting-starter.service`, then:

```sh
systemctl --user daemon-reload
systemctl --user enable --now accounting-starter
systemctl --user status accounting-starter
```

Verify the health endpoint with `curl -f http://127.0.0.1:8765/health`.
User services stop when you log out unless lingering is on:
`loginctl enable-linger "$USER"` (may need sudo; a host administrator decision). Containers without systemd should use their normal
supervisor. Do not claim the service is installed just because this example
exists. The installer itself does not change host services.

## Backups
Stop writes before copying the SQLite ledger, or use SQLite's online backup
API for a consistent live snapshot. Back up the private runtime directory,
not just GitHub code. Protect backups like the original email/financial data.
Never commit backups or credential files. Test a restore to an isolated data
directory before depending on the backup.
