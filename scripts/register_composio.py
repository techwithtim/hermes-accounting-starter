"""Register Composio's hosted MCP server (sign-in, no API key) through the Hermes CLI.

Only adds the entry. Signing in is the person's step: `hermes mcp login composio`
in an SSH terminal, or Authenticate on the server under MCP in the Hermes dashboard
(then Restart Gateway so chats see the tools).
"""
import os
from pathlib import Path
import subprocess
import sys
import yaml

NAME = 'composio'
URL = 'https://connect.composio.dev/mcp'
# Search, connect Gmail, and run tools. Leaves out Composio's remote shell,
# workbench and raw proxy tools, which a bookkeeping agent never needs.
TOOLS = ['COMPOSIO_SEARCH_TOOLS', 'COMPOSIO_GET_TOOL_SCHEMAS', 'COMPOSIO_MANAGE_CONNECTIONS',
         'COMPOSIO_WAIT_FOR_CONNECTIONS', 'COMPOSIO_MULTI_EXECUTE_TOOL']


def _servers(home):
    file = Path(home)/'config.yaml'
    config = yaml.safe_load(file.read_text()) if file.exists() else {}
    return (config or {}).get('mcp_servers') or {}


def register(home):
    """Return the name of the Composio server Hermes should use."""
    servers = _servers(home)
    for name, cfg in servers.items():
        if isinstance(cfg, dict) and str(cfg.get('url', '')).rstrip('/') == URL:
            print(f'Composio MCP server already configured as {name!r}; preserved unchanged.')
            return name
    if NAME in servers:
        raise RuntimeError(f'An MCP server named {NAME!r} already exists with a different URL; refusing overwrite')
    env = dict(os.environ, HERMES_HOME=str(home))
    for key, value in (('url', URL), ('auth', 'oauth'), ('tools.include', yaml.safe_dump(TOOLS, default_flow_style=True).strip())):
        subprocess.run(['hermes', 'config', 'set', f'mcp_servers.{NAME}.{key}', value],
                       env=env, check=True, stdout=subprocess.DEVNULL)
    saved = _servers(home).get(NAME) or {}
    if saved.get('url') != URL or saved.get('auth') != 'oauth':
        raise RuntimeError('Composio MCP registration was not saved; installation is incomplete')
    print('Composio MCP server registered. Sign in with: hermes mcp login composio')
    return NAME


if __name__ == '__main__':
    register(*sys.argv[1:])
