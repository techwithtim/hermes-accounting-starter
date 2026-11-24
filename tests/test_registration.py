import importlib.util
import subprocess
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]

def load():
    spec = importlib.util.spec_from_file_location('register', ROOT/'scripts/register_mcp.py')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

def test_register_refuses_existing_other_server(tmp_path, monkeypatch):
    m = load()
    (tmp_path/'config.yaml').write_text('mcp_servers:\n  accounting-starter:\n    command: private-app\n')
    monkeypatch.setattr(m.subprocess, 'run', lambda *a, **k: pytest.fail('must not overwrite'))
    with pytest.raises(RuntimeError, match='different'):
        m.register(tmp_path, '/app/bin/accounting-starter', '/private/data')

def test_cancelled_registration_cannot_report_success(tmp_path, monkeypatch):
    m = load()
    monkeypatch.setattr(m.subprocess, 'run', lambda *a, **k: subprocess.CompletedProcess(a[0], 0))
    with pytest.raises(RuntimeError, match='not saved'):
        m.register(tmp_path, '/app/bin/accounting-starter', '/private/data')
