# Release verification

## Executed checks
- Full automated suite: 49 tests passed on Linux ARM64 / Python 3.11.
- Real Hermes native CLI installation into an isolated temporary HERMES_HOME:
  server configuration saved and read back; 10 tools discovered and connected.
- MCP stdio initialization and real SQLite ledger tool execution covered.
- Empty live ledger remained empty after separate fictional demo seeding.
- Dashboard visited using Chromium: navigation succeeded without page errors;
  mobile overview had no horizontal overflow. Health endpoint returned
  `{"status":"ok"}`. The bundled screenshot is the actual fictional demo.
- Currency display checked for two-, zero- and three-decimal currencies.
- Python wheel and source distribution built successfully.
- Secret scanner reviewed: only a literal synthetic test credential and an
  ignored pytest cache signature flagged in the initial scan; no real key found.
- Tracked source checked for private identity, production paths and database files.

## Not verified / not promised
- Live Composio project authorization, Google consent and real email/attachment
  retrieval: requires a recipient-owned account. Connector tests use explicit
  synthetic HTTP fixtures with the real installed SDK serialization.
- Hostinger-specific deployment image, public authenticated proxy, Windows,
  unattended scheduled job completion, accountant/tax compliance.
- Public GitHub publication is separate from building this release.

Passing tests are not a substitute for a real account's consent/first scan.
