"""Register through Hermes CLI and verify persistence; never edit its YAML."""
import os
from pathlib import Path
import subprocess
import sys
import yaml


def register(home, executable, data):
    home = Path(home)
    def existing():
        file = home/'config.yaml'
        config = yaml.safe_load(file.read_text()) if file.exists() else {}
        return (config or {}).get('mcp_servers', {}).get('accounting-starter')
    wanted = {'command': executable, 'args': ['--data-dir', data, 'mcp']}
    old = existing()
    if old is not None:
        if old.get('command') != wanted['command'] or old.get('args') != wanted['args']:
            raise RuntimeError('A different accounting-starter MCP server already exists; refusing overwrite')
        print('Matching MCP registration already exists; preserved unchanged.')
        return
    env = dict(os.environ, HERMES_HOME=str(home))
    # This package owns this new, previously absent server. Approve discovered
    # tools only; never answer yes to an overwrite prompt on an existing entry.
    subprocess.run(['hermes', 'mcp', 'add', 'accounting-starter', '--command', executable,
                    '--args', '--data-dir', data, 'mcp'], input='y\n', text=True,
                   env=env, check=True)
    saved = existing()
    if not saved or saved.get('command') != executable or saved.get('args') != wanted['args']:
        raise RuntimeError('MCP registration was not saved; installation is incomplete')
    print('MCP registration verified in the selected Hermes home.')

if __name__ == '__main__':
    register(*sys.argv[1:])
