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
        if target.exists() and target.read_text() != skill_text and '## Local installation' not in target.read_text():
            # Not a copy this installer wrote: keep it next to the new one instead of losing it.
            backup = target.with_name('SKILL.md.custom-backup')
            backup.write_text(target.read_text())
            print(f'Your edited skill was saved as {backup}')
        target.write_text(skill_text)
    print('\nINSTALLED. Ledger, demo data, MCP servers, skill and dashboard tab are ready.')
    if args.skip_hermes:
        print('Start dashboard: '+shlex.join([str(exe), '--data-dir', str(data), 'serve']))
        return
    link, state = find_dashboard(home)
    if state == 'rescanned':
        print('Accounting tab: already loaded (this dashboard has no login).')
    elif link:
        print(f'Rescan link: {link}')
    print('Next: follow step 2 of SETUP.md (send the hand-over message, then stop).')


RESCAN_PATH = '/api/dashboard/plugins/rescan'


def configured_dashboard_url(home):
    """The public address Hermes was told about (env or dashboard.public_url), else None."""
    url = os.environ.get('HERMES_DASHBOARD_PUBLIC_URL', '').strip()
    if not url:
        try:
            import yaml
            config = yaml.safe_load((home/'config.yaml').read_text()) or {}
            url = str((config.get('dashboard') or {}).get('public_url') or '').strip()
        except Exception:
            url = ''
    return url.rstrip('/') if url.startswith(('http://', 'https://')) else None


def listening_sockets():
    """(bind address, port) for every listening TCP socket, read from /proc (Linux only)."""
    found = set()
    for table, v6 in (('/proc/net/tcp', False), ('/proc/net/tcp6', True)):
        try:
            lines = Path(table).read_text().splitlines()[1:]
        except OSError:
            continue
        for line in lines:
            parts = line.split()
            if len(parts) < 4 or parts[3] != '0A':  # 0A = LISTEN
                continue
            addr_hex, port_hex = parts[1].split(':')
            raw = bytes.fromhex(addr_hex)
            if v6:
                words = [raw[i:i+4][::-1] for i in range(0, 16, 4)]
                import ipaddress
                addr = str(ipaddress.IPv6Address(b''.join(words)))
                if addr.startswith('::ffff:'):
                    addr = addr[7:]
            else:
                addr = '.'.join(str(b) for b in raw[::-1])
            found.add((addr, int(port_hex, 16)))
    return found


def probe_dashboard(port, timeout=1.5):
    """'login' if this local port is a Hermes dashboard that needs a login, 'rescanned' if it
    answered the rescan itself (no login on this dashboard), else None."""
    import urllib.error  # urllib.request is imported at the top
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{port}{RESCAN_PATH}', timeout=timeout) as r:
            body = json.loads(r.read(4096) or b'{}')
            return 'rescanned' if body.get('ok') is True and 'count' in body else None
    except urllib.error.HTTPError as e:
        try:
            body = json.loads(e.read(4096) or b'{}')
        except Exception:
            return None
        return 'login' if e.code == 401 and 'login_url' in body else None
    except Exception:
        return None


def primary_ip():
    """This server's main IPv4 address (no packet is sent), else None."""
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(('1.1.1.1', 80))
            return s.getsockname()[0]
    except OSError:
        return None


def find_dashboard(home, sockets=None, probe=probe_dashboard, ip=primary_ip):
    """Return (rescan_url or None, state) where state is 'login', 'rescanned' or 'unknown'.

    The rescan URL only works in the person's logged-in browser, so the installer prints it
    for the agent to pass on. A dashboard without a login gets rescanned right here."""
    sockets = listening_sockets() if sockets is None else sockets
    # Default port first, then any other listener; first one that answers like Hermes wins.
    ports = sorted({p for _, p in sockets}, key=lambda p: (p != 9119, p))
    port = state = None
    for candidate in ports:
        state = probe(candidate)
        if state:
            port = candidate
            break
    public = configured_dashboard_url(home)
    if public:
        return public + RESCAN_PATH, state or 'login'
    if not port:
        return None, 'unknown'
    binds = {a for a, p in sockets if p == port}
    if binds and binds <= {'127.0.0.1', '::1'}:
        # Loopback only: reached through a proxy or tunnel whose address we cannot know.
        return None, state
    specific = sorted(a for a in binds if a not in ('0.0.0.0', '::'))
    host = specific[0] if specific else ip()
    if not host:
        return None, state
    host = f'[{host}]' if ':' in host else host
    return f'http://{host}:{port}{RESCAN_PATH}', state


if __name__ == '__main__':
    main()
