#!/usr/bin/env python3
"""Install only this clean package into an explicitly selected Hermes home."""
import argparse
import os
from pathlib import Path
import shlex
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def find_uv():
    """Find uv even when its installer has not yet updated this shell's PATH."""
    found = shutil.which('uv')
    if found:
        return found
    for candidate in (Path.home()/'.local/bin/uv', Path.home()/'.cargo/bin/uv'):
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--skip-hermes', action='store_true', help='Install standalone without registering MCP or skills')
    parser.add_argument('--hermes-home', type=Path, default=Path(os.environ.get('HERMES_HOME', Path.home()/'.hermes')))
    parser.add_argument('--data-dir', type=Path, default=Path.home()/'.local/share/hermes-accounting-starter')
    args = parser.parse_args()
    home, data = args.hermes_home.expanduser().resolve(), args.data_dir.expanduser().resolve()
    if data == ROOT or ROOT in data.parents:
        parser.error('Runtime data must be outside the public repository')
    exe = ROOT/'.venv/bin/accounting-starter'
    uv = find_uv() or 'uv'
    commands = [[uv, 'sync', '--frozen'],[str(exe), '--data-dir', str(data), 'init']]
    if not args.skip_hermes:
        print('Register using hermes mcp add accounting-starter (with persistence verification).')
        commands.append([str(ROOT/'.venv/bin/python'), str(ROOT/'scripts/register_mcp.py'), str(home), str(exe), str(data)])
    print('Install includes Composio SDK. Account creation and email OAuth require your consent.')
    for command in commands:
        print(shlex.join(command))
    if args.dry_run:
        return
    if not find_uv():
        parser.error('uv is required; install it from https://docs.astral.sh/uv/getting-started/installation/ '
                     '(if you just installed it, run: source ~/.local/bin/env)')
    if not args.skip_hermes and not shutil.which('hermes'):
        parser.error('Install and configure Hermes first, or use --skip-hermes')
    target = home/'skills/accounting-starter/SKILL.md'
    source = ROOT/'skills/accounting-starter/SKILL.md'
    skill_text = source.read_text() + f'\n## Local installation\n\nCheckout: `{ROOT}`\nRuntime data: `{data}`\nPython: `{ROOT / ".venv/bin/python"}`\n'
    if not args.skip_hermes and target.exists() and target.read_text() != skill_text:
        parser.error('An existing customized accounting-starter skill exists; back it up and remove it before upgrading')
    os.umask(0o077)
    data.mkdir(parents=True, exist_ok=True, mode=0o700)
    env = dict(os.environ, HERMES_HOME=str(home))
    for command in commands:
        subprocess.run(command, cwd=ROOT, env=env, check=True)
    if not args.skip_hermes:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(skill_text)
    print('Installed. Continue with SETUP.md step 3 (dashboards), then connect Gmail in step 4.')
    print('Start dashboard: '+shlex.join([str(exe), '--data-dir', str(data), 'serve']))
    print('Reload MCP in a new Hermes session. Scheduled scans are opt-in; see docs/AUTOMATION.md.')

if __name__ == '__main__':
    main()
