#!/usr/bin/env python3
"""One-command install into the active Hermes home.

Installs locked dependencies (fetching a pinned, checksum-verified uv if needed),
creates the live ledger and the fictional demo, registers the accounting and
Composio MCP servers, installs the skill and adds the Accounting tab to the
Hermes dashboard. Safe to run again. Ends with what to tell the person.
"""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import shlex
import shutil
import subprocess
import sys
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_NAME = 'accounting-starter'
UV_VERSION = '0.13.9'
UV_SHA256 = {
    'x86_64': 'a7fbaff2b9a271d85c1bdb540941090fd1ce011797b4abeb48e4dcd39c2471d5',
    'aarch64': '0797542018e541a9288855df555c8077eed06f7a47d206362030480e8ecc9f3d',
}


def find_uv():
    """Find uv even when its installer has not yet updated this shell's PATH."""
    found = shutil.which('uv')
    if found:
        return found
    for candidate in (Path.home()/'.local/bin/uv', Path.home()/'.cargo/bin/uv', ROOT/'.setup-tools/uv'):
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def download_uv():
    """Fetch the pinned uv release from GitHub into .setup-tools and verify its SHA-256."""
    machine = platform.machine().lower()
    arch = {'amd64': 'x86_64', 'arm64': 'aarch64'}.get(machine, machine)
    if sys.platform != 'linux' or arch not in UV_SHA256:
        raise SystemExit(f'uv is missing and no pinned build exists for {sys.platform}/{machine}; '
                         'install uv from https://docs.astral.sh/uv/ and rerun')
    name = f'uv-{arch}-unknown-linux-gnu'
    url = f'https://github.com/astral-sh/uv/releases/download/{UV_VERSION}/{name}.tar.gz'
    with urllib.request.urlopen(url, timeout=120) as response:
        blob = response.read()
    if hashlib.sha256(blob).hexdigest() != UV_SHA256[arch]:
        raise SystemExit('Downloaded uv failed its checksum; not using it')
    target = ROOT/'.setup-tools'
    target.mkdir(exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(blob)) as archive:
        member = archive.getmember(f'{name}/uv')
        (target/'uv').write_bytes(archive.extractfile(member).read())
    (target/'uv').chmod(0o755)
    return str(target/'uv')


def install_dashboard_tab(home, exe, data):
    """Copy the Hermes dashboard plugin and record where the package lives."""
    target = home/'plugins'/PLUGIN_NAME
    marker = target/'dashboard'/'manifest.json'
    if (target.exists() and not marker.exists()) or (
            marker.exists() and json.loads(marker.read_text()).get('name') != PLUGIN_NAME):
        raise SystemExit(f'{target} belongs to another plugin; refusing to overwrite')
    shutil.copytree(ROOT/'hermes_plugin', target, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns('__pycache__'))
    (target/'dashboard'/'settings.json').write_text(
        json.dumps({'executable': str(exe), 'data_dir': str(data)}, indent=2))


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
    py = str(ROOT/'.venv/bin/python')
    uv = find_uv()
    commands = [[uv or '<uv>', 'sync', '--frozen'],
                [str(exe), '--data-dir', str(data), 'init'],
                [str(exe), '--data-dir', str(data), '--demo', 'demo']]
    if not args.skip_hermes:
        if args.dry_run:
            print('Register using hermes mcp add accounting-starter (with persistence verification).')
        commands.append([py, str(ROOT/'scripts/register_mcp.py'), str(home), str(exe), str(data)])
        commands.append([py, str(ROOT/'scripts/register_composio.py'), str(home)])
        commands.append(['hermes', 'plugins', 'enable', PLUGIN_NAME])
    if args.dry_run:
        print('Registers the Composio MCP server (you sign in; no API key). Email access requires your consent.')
        if not uv:
            print(f'uv not found: would download uv {UV_VERSION} from GitHub and verify its SHA-256.')
        for command in commands:
            print(shlex.join(command))
        return
    if not args.skip_hermes and not shutil.which('hermes'):
        parser.error('Install and configure Hermes first, or use --skip-hermes')
    target = home/'skills/accounting-starter/SKILL.md'
    source = ROOT/'skills/accounting-starter/SKILL.md'
    skill_text = source.read_text() + f'\n## Local installation\n\nCheckout: `{ROOT}`\nRuntime data: `{data}`\nPython: `{ROOT / ".venv/bin/python"}`\n'
    if not args.skip_hermes and target.exists() and target.read_text() != skill_text:
        parser.error('An existing customized accounting-starter skill exists; back it up and remove it before upgrading')
    commands[0][0] = uv or download_uv()
    os.umask(0o077)
    data.mkdir(parents=True, exist_ok=True, mode=0o700)
    env = dict(os.environ, HERMES_HOME=str(home))
    for command in commands:
        if command[:3] == ['hermes', 'plugins', 'enable']:
            install_dashboard_tab(home, exe, data)
        # Quiet on success so the agent has little to read; full output on failure.
        result = subprocess.run(command, cwd=ROOT, env=env, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True)
        if result is not None and result.returncode != 0:
            print('FAILED: ' + shlex.join(command))
            print('\n'.join((result.stdout or '').splitlines()[-30:]))
            raise SystemExit(1)
    if not args.skip_hermes:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(skill_text)
    print('\nINSTALLED. Ledger, demo data, MCP servers, skill and dashboard tab are ready.')
    if args.skip_hermes:
        print('Start dashboard: '+shlex.join([str(exe), '--data-dir', str(data), 'serve']))
        return
    print('Next: follow step 2 of SETUP.md (send the hand-over message, then stop).')


if __name__ == '__main__':
    main()
