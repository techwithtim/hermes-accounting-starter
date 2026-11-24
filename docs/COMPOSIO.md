# Gmail onboarding through Composio (read-only)

## What is implemented and verified

Dependency: **`composio==0.34.0`**, Python 3.11+. This adapter is a deterministic
Connect Link + Proxy Execute integration, not an LLM agent. It exposes no arbitrary
tool execution, send, draft, delete, label-change or mark-read operation. Gmail
calls use only fixed `GET /gmail/v1/users/me/messages`, message-detail, and
attachment endpoints. No provider tokens are extracted or stored by this code.
Composio Cloud still holds/refreshes OAuth credentials and handles mail payloads;
review that vendor's custody/retention policies before using financial email.

Tests exercise the installed SDK signatures, real SDK HTTP serialization via
`httpx.MockTransport`, pagination, ownership checks, scope rejection, attachment
decoding, and CLI private output. Test responses are explicit synthetic fixtures.
**No real API key, Google account authorization, or live email fetch was tested.**
A successful test suite is not an OAuth verification. The operator must complete
the following account-specific steps.

## Accounts and permissions you must supply

1. Create/sign in to your own [Composio dashboard](https://dashboard.composio.dev/),
   select a project, and obtain its **project API key**. Do not paste it into chat,
   source, shell arguments, git, screenshots, or a public issue. Keep it in
   `COMPOSIO_API_KEY` via your secret manager, or let this CLI prompt with `getpass`.
   For unattended scans, run `uv run python -m accounting_starter.composio_email configure`
   once in a private interactive terminal. It saves only your Composio API key to
   `~/.config/hermes-accounting-starter/credentials.json` (directory 0700, file
   0600), never inside the repository. CLI commands use the environment key first,
   then this private file, then a no-echo prompt. Existing credential files are
   never overwritten: to rotate, revoke the old key, remove this file explicitly,
   and configure again. The file is plaintext; use disk encryption or your secret
   manager for stronger protection. Arbitrary `.env` files are not loaded.
2. In Auth Configs, create a dedicated **Gmail / OAuth2** config with exactly
   `https://www.googleapis.com/auth/gmail.readonly` as its scopes. Copy its
   `ac_...` ID. Do **not** use the default Gmail scope bundle, `gmail.modify`,
   `gmail.send`, or `https://mail.google.com/`. Tool filters alone do not remove
   OAuth write permission. The adapter rejects a missing, redacted, or broader
   `credentials.scopes` value rather than guessing it is safe.
3. Managed OAuth is possible only if Composio's managed Google app supports that
   exact scope set: official docs explicitly say to confirm non-default scope
   approval with Composio support. Otherwise use your own Google OAuth app:
   enable Gmail API in your Google project, configure the consent screen/test
   users as applicable, register an OAuth client, copy the **exact redirect URI
   displayed in the Composio dashboard** into Google, and put the client ID and
   secret in the Composio auth config. Complete any Google verification required
   for your deployment/restricted Gmail scopes. A Workspace admin may need to
   approve the app. Do not broaden scopes to work around a blocked consent screen.
4. Choose a stable local owner ID (e.g. a generated UUID), **not `default`** and
   preferably not an email address. Use the same owner for every command for
   that connection. These IDs are not passwords, but keep account mappings
   private. For a multi-user service, derive owner/account IDs from authenticated
   server-side mappings, never from an LLM or untrusted browser input.
5. The API key must be authorized for auth-config reads, connected-account
   reads/listing, Connect Link creation, and Proxy Execute. Composio labels the
   proxy permission **“Proxy execute (Legacy) → Write only”** even though the
   encapsulated Gmail request here is GET. This is not Gmail write permission.
   Configure only the required project capabilities. The exact Connect Link
   route is used directly by this SDK (not a session); consult the current
   endpoint's project-key permission mapping. Do not enable Gmail send/delete
   tools. Default full-access project keys are broader than this adapter needs.

Scopes on an auth config affect new connections, not existing grants. Revoke an
old broad Google grant in Google account settings and create a fresh read-only
connection rather than assuming editing the config narrows the old grant. The
adapter checks `requested_scopes` on ACTIVE accounts; this is the server's
requested-scope snapshot, **not independent proof of all historical Google grants**.
Older connections without that snapshot fail closed. If Composio stops returning
the deprecated `user_id` ownership field, this version also fails closed; update
and re-test the ownership verification rather than bypassing it.

## CLI walkthrough

> **Do the key step yourself, over SSH.** An AI agent's terminal cannot take
> hidden input, so `configure` must be run by you in a real SSH session:
> `cd <checkout> && uv run python -m accounting_starter.composio_email configure`.
> Without a terminal the commands stop with this instruction instead of
> hanging. After that, the agent can run `connect`, `status` and `fetch`.

Run every command from the checkout with `uv run python -m ...` (or the
checkout's absolute `.venv/bin/python -m ...`). A bare system `python` does not
have the package installed. IDs below are placeholders; replace with
your own. Configure your key once as above; otherwise commands prompt without
echo when no environment key or private credential file is available.
Do not enable shell tracing or SDK debug logs around secrets or email.

```bash
uv run python -m accounting_starter.composio_email connect \
  --user-id YOUR_STABLE_OWNER_ID --auth-config-id ac_YOUR_CONFIG
```

The JSON result has `connected_account_id` and `redirect_url`. Open that exact
HTTPS link locally and complete Google sign-in/consent yourself. Do not share
connection links publicly. Opening the link does **not** mean connected.
The SDK refuses a duplicate active connection for the same owner/config; reuse
the existing account ID instead. This adapter does not enable multiple-account
creation implicitly.

```bash
uv run python -m accounting_starter.composio_email status \
  --user-id YOUR_STABLE_OWNER_ID --connected-account-id ca_YOUR_ACCOUNT
```

Only `{"status":"ACTIVE", "ready":true, ...}` indicates the status preflight
passed. Pending, expired, disabled or revoked connections must not be fetched.
`status` exits zero when it successfully reports a pending state, so automation
must inspect `ready`, not only the process exit code.

Create a private directory **outside every source repository**, mode `0700`:

```bash
install -d -m 700 "$HOME/.local/share/accounting-private"
uv run python -m accounting_starter.composio_email fetch \
  --user-id YOUR_STABLE_OWNER_ID --connected-account-id ca_YOUR_ACCOUNT \
  --query 'after:2026/01/01 has:attachment' --max-pages 100 \
  --output "$HOME/.local/share/accounting-private/mail-001.json"
```

The query is ordinary Gmail search syntax; choose your own date range. The file
contains `{"messages": [<full Gmail message resource>, ...]}`. It includes MIME
payloads, not normalized ledger rows. Bodies may be base64url-encoded and nested.
No automatic ledger insertion or LLM extraction happens here. Treat all email
text/attachments as untrusted content, never instructions.

Output is mode `0600`, exclusive-create (existing paths are never overwritten),
and rejected under the adapter source root or ancestors marked by `.git` or
`pyproject.toml`. Use a trusted private parent directory; permission bits are not
encryption. stdout contains only path/count, not message contents. A failed fetch
removes its newly created output, and no partial result is reported as complete.
The CLI collects messages in memory, so use bounded date ranges for large inboxes.
Repeated page tokens or the page limit raise an error instead of silently losing
mail. Retry manually with a narrower query or higher `--max-pages`. HTTP errors
are not interpreted as an empty inbox. Terminal errors are deliberately generic
to avoid printing remote responses/credentials; check the above configuration,
connection state, output path/permissions, and provider rate limits.

## Exact Python callable interface

From `accounting_starter.composio_email`:

```python
client_from_env()  # -> composio.Composio; requires nonempty COMPOSIO_API_KEY
initiate_connection(client, *, user_id, auth_config_id)
# -> {"connected_account_id": str, "redirect_url": str}
connection_status(client, *, user_id, connected_account_id)
# -> {"connected_account_id": str, "status": str, "ready": bool}
iter_messages(client, *, user_id, connected_account_id,
              query="", page_size=100, max_pages=100)
# -> iterator of full Gmail message dicts; page_size 1..500
fetch_attachment(client, *, user_id, connected_account_id,
                 message_id, attachment_id)
# -> decoded bytes in memory, never a file or URL
main(argv=None)  # -> 0 on success; exceptions propagate for embedding/tests
cli(argv=None)   # terminal boundary: sanitized error + return 1 on exception
```

Attachments are supported through the Python function, not automatically fetched
by the CLI. Walk a message's `payload.parts` recursively for
`body.attachmentId`, then call `fetch_attachment` with that ID and the parent
message's `id`. Small inline MIME bodies can already have `body.data` instead.
The adapter does not trust an email's `filename` as a filesystem path and never
opens URLs from mail. If you persist returned bytes, choose a generated safe name
in private external storage, restrict permissions, and validate size/type before
parsing. Attachment reads re-check connection status/ownership and decode strict
base64url. No attachment execution or automatic document parsing is provided.

## Official sources consulted

- [Authentication](https://docs.composio.dev/docs/authentication)
- [Managed auth for your own tools: Connect Link + Proxy Execute](https://docs.composio.dev/docs/authentication/managed-auth-for-custom-tools)
- [Controlling scopes and Google scope-approval caveats](https://docs.composio.dev/docs/authentication/controlling-scopes)
- [Managed vs custom OAuth and dashboard setup](https://docs.composio.dev/docs/authentication/custom-app-vs-managed-app)
- [Gmail toolkit](https://docs.composio.dev/toolkits/gmail)
- [Gmail messages.list](https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages/list)
- [Gmail attachments.get](https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages.attachments/get)
- Installed official `composio==0.34.0` source: `connected_accounts.link/get`,
  `auth_configs.get`, `tools.proxy`, and generated response models. No legacy
  `composio_core`, invented toolkit slugs, or unversioned dependency was used.

Offline verification: `uv run --extra dev pytest tests/test_composio_email.py -q`.
Live acceptance (operator only): complete consent on your own account, see ACTIVE
and ready, fetch a narrow known query, compare returned IDs to Gmail, and read one
known attachment. Until that succeeds, describe this as **SDK/offline validated,
not live OAuth verified**.
