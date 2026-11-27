# Gmail through Composio

## Default: Composio MCP server (sign in, no API key)

`scripts/install.py` registers Composio's hosted MCP server in Hermes:

```yaml
mcp_servers:
  composio:
    url: https://connect.composio.dev/mcp
    auth: oauth
    tools:
      include: [COMPOSIO_SEARCH_TOOLS, COMPOSIO_GET_TOOL_SCHEMAS,
                COMPOSIO_MANAGE_CONNECTIONS, COMPOSIO_WAIT_FOR_CONNECTIONS,
                COMPOSIO_MULTI_EXECUTE_TOOL]
```

It uses `hermes config set`, keeps an existing entry for the same URL under
whatever name it has, and refuses to overwrite a different server named
`composio`. Then the person:

1. Signs Hermes in to their Composio account: **Authenticate** on the server under
   **MCP** in the Hermes dashboard, or `hermes mcp login composio` in an SSH terminal
   (open the printed link, approve, paste the address the browser ends up
   on back into the terminal). Hermes stores and refreshes the tokens.
   Then **Restart Gateway** (dashboard) so chat sessions load the Composio
   tools; signing in only reconnects the dashboard's own process.
   An agent's own terminal cannot do this step: it is non-interactive and
   Hermes stops with "Run `hermes mcp login composio` interactively".
2. Opens the Gmail link the agent gets from `mcp__composio__COMPOSIO_MANAGE_CONNECTIONS`
   (arguments `{"toolkits": [{"action": "add", "name": "gmail"}]}`)
   and approves Google consent.

The `accounting-starter` skill allows only `GMAIL_FETCH_EMAILS`,
`GMAIL_FETCH_MESSAGE_BY_MESSAGE_ID`, `GMAIL_GET_ATTACHMENT` and
`GMAIL_LIST_LABELS`. Google's grant is broader (Composio's shared Google app
asks for full mailbox access) and `COMPOSIO_MULTI_EXECUTE_TOOL` can run any
connected tool, so read-only here is an agent rule, not a technical block.

Verified so far: Hermes v0.23 registers the server, performs dynamic client
registration with Composio and prints the sign-in link. A completed sign-in
and live Gmail read through this path have not been tested yet.
