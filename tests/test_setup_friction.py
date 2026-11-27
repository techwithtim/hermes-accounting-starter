"""Regressions for problems found when an agent ran the install prompt on a fresh VPS."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_installer():
    spec = importlib.util.spec_from_file_location('installer_friction', ROOT/'scripts/install.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_installer_finds_uv_before_path_is_updated(tmp_path, monkeypatch):
    mod = load_installer()
    uv = tmp_path/'.local/bin/uv'
    uv.parent.mkdir(parents=True)
    uv.write_text('#!/bin/sh\n')
    uv.chmod(0o755)
    monkeypatch.setattr(mod.Path, 'home', lambda: tmp_path)
    monkeypatch.setattr(mod.shutil, 'which', lambda name: None)
    assert mod.find_uv() == str(uv)


def test_installer_prints_rescan_link_when_dashboard_address_is_known(tmp_path, monkeypatch):
    mod = load_installer()
    monkeypatch.delenv('HERMES_DASHBOARD_PUBLIC_URL', raising=False)
    assert mod.configured_dashboard_url(tmp_path) is None
    (tmp_path/'config.yaml').write_text('dashboard:\n  public_url: "https://hermes.example.com/"\n')
    assert mod.configured_dashboard_url(tmp_path) == 'https://hermes.example.com'
    monkeypatch.setenv('HERMES_DASHBOARD_PUBLIC_URL', 'http://203.0.113.7:9119')
    assert mod.configured_dashboard_url(tmp_path) == 'http://203.0.113.7:9119'


def test_setup_names_the_exact_composio_call_and_gateway_restart():
    # Fresh-VPS run (Hermes v0.23.4): a bare "COMPOSIO_MANAGE_CONNECTIONS" made the agent pick
    # another tool and wrongly report "not signed in"; Authenticate only reconnects the dashboard.
    setup = (ROOT/'SETUP.md').read_text()
    skill = (ROOT/'skills/accounting-starter/SKILL.md').read_text()
    call = 'mcp__composio__COMPOSIO_MANAGE_CONNECTIONS'
    args = '{"toolkits": [{"action": "add", "name": "gmail"}]}'
    assert call in setup and args in setup
    assert call in skill and args in skill
    assert 'Restart Gateway' in setup and 'Restart Gateway' in skill
    # Dashboard labels as Hermes shows them.
    assert '**MCP**' in setup and '**Authenticate**' in setup
    assert 'Authorize' not in setup and 'MCP servers' not in setup


def test_rescan_link_found_from_listening_dashboard():
    mod = load_installer()
    home = Path('/nonexistent-home')
    hermes = {9119: 'login'}
    probe = lambda port: hermes.get(port)
    # Dashboard on all interfaces: the server's own IP and the real port.
    link, state = mod.find_dashboard(home, {('0.0.0.0', 22), ('0.0.0.0', 9119)}, probe, lambda: '203.0.113.7')
    assert link == 'http://203.0.113.7:9119/api/dashboard/plugins/rescan' and state == 'login'
    # A non-default port is found too, and a specific bind address wins over the guessed IP.
    link, _ = mod.find_dashboard(home, {('198.51.100.4', 8443)}, {8443: 'login'}.get, lambda: '10.0.0.2')
    assert link == 'http://198.51.100.4:8443/api/dashboard/plugins/rescan'
    # Loopback-only dashboard sits behind a proxy we cannot see: no guessed link.
    assert mod.find_dashboard(home, {('127.0.0.1', 9119)}, probe, lambda: '203.0.113.7')[0] is None
    # No dashboard found at all.
    assert mod.find_dashboard(home, {('0.0.0.0', 22)}, probe, lambda: '203.0.113.7') == (None, 'unknown')


def test_configured_public_url_wins(monkeypatch):
    mod = load_installer()
    monkeypatch.setenv('HERMES_DASHBOARD_PUBLIC_URL', 'https://hermes.example.com/')
    link, _ = mod.find_dashboard(Path('/nonexistent-home'), set(), lambda p: None, lambda: None)
    assert link == 'https://hermes.example.com/api/dashboard/plugins/rescan'


def test_setup_always_passes_the_rescan_link_on():
    setup = (ROOT/'SETUP.md').read_text()
    assert 'Rescan link: <url>' in setup and 'Always\n  include the URL' in setup
