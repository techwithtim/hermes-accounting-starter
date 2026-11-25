import importlib.util
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]


def load():
    spec = importlib.util.spec_from_file_location('register_composio', ROOT/'scripts/register_composio.py')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def fake_hermes_config_set(home):
    """Stand-in for `hermes config set`, writing the same YAML shape Hermes v0.23 writes."""
    def run(cmd, **kwargs):
        assert cmd[:3] == ['hermes', 'config', 'set'] and kwargs['env']['HERMES_HOME'] == str(home)
        file = home/'config.yaml'
        config = yaml.safe_load(file.read_text()) if file.exists() else {}
        node = config
        *parents, last = cmd[3].split('.')
        for part in parents:
            node = node.setdefault(part, {})
        node[last] = yaml.safe_load(cmd[4])
        file.write_text(yaml.safe_dump(config))
        return subprocess.CompletedProcess(cmd, 0)
    return run


def test_registers_signin_server_with_tool_allowlist(tmp_path, monkeypatch):
    m = load()
    monkeypatch.setattr(m.subprocess, 'run', fake_hermes_config_set(tmp_path))
    assert m.register(tmp_path) == 'composio'
    saved = yaml.safe_load((tmp_path/'config.yaml').read_text())['mcp_servers']['composio']
    assert saved == {'url': 'https://connect.composio.dev/mcp', 'auth': 'oauth', 'tools': {'include': m.TOOLS}}
    assert not any('BASH' in t or 'WORKBENCH' in t or 'PROXY' in t for t in m.TOOLS)
    assert 'api_key' not in (tmp_path/'config.yaml').read_text().lower()


def test_existing_composio_server_is_reused_under_its_own_name(tmp_path, monkeypatch):
    m = load()
    (tmp_path/'config.yaml').write_text('mcp_servers:\n  my-composio:\n    url: https://connect.composio.dev/mcp/\n    auth: oauth\n')
    monkeypatch.setattr(m.subprocess, 'run', lambda *a, **k: pytest.fail('must not touch an existing entry'))
    assert m.register(tmp_path) == 'my-composio'


def test_refuses_other_server_named_composio(tmp_path, monkeypatch):
    m = load()
    (tmp_path/'config.yaml').write_text('mcp_servers:\n  composio:\n    url: https://example.com/mcp\n')
    monkeypatch.setattr(m.subprocess, 'run', lambda *a, **k: pytest.fail('must not overwrite'))
    with pytest.raises(RuntimeError, match='different URL'):
        m.register(tmp_path)


def test_unsaved_registration_cannot_report_success(tmp_path, monkeypatch):
    m = load()
    monkeypatch.setattr(m.subprocess, 'run', lambda *a, **k: subprocess.CompletedProcess(a[0], 0))
    with pytest.raises(RuntimeError, match='not saved'):
        m.register(tmp_path)
