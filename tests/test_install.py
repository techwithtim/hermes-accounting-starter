import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_install_dry_run_is_non_mutating(tmp_path):
    result = subprocess.run([sys.executable, str(ROOT/'scripts/install.py'), '--dry-run', '--hermes-home', str(tmp_path/'hermes'), '--data-dir', str(tmp_path/'data')], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert not (tmp_path/'hermes').exists()
    assert not (tmp_path/'data').exists()
    assert 'uv sync --frozen' in result.stdout
    assert 'hermes mcp add accounting-starter' in result.stdout
    assert 'composio' in result.stdout.lower()


def test_skill_install_records_paths_and_preserves_customization(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location('installer', ROOT/'scripts/install.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    home, data = tmp_path/'home', tmp_path/'data'
    monkeypatch.setattr(sys, 'argv', ['install.py', '--hermes-home', str(home), '--data-dir', str(data)])
    monkeypatch.setattr(mod.shutil, 'which', lambda x: '/usr/bin/'+x)
    monkeypatch.setattr(mod.subprocess, 'run', lambda *a, **k: None)
    mod.main()
    target = home/'skills/accounting-starter/SKILL.md'
    assert str(ROOT) in target.read_text()
    assert str(data) in target.read_text()
    mod.main()  # repeat must work without losing the generated paths
    target.write_text('my custom policy')
    import pytest
    with pytest.raises(SystemExit):
        mod.main()
    assert target.read_text() == 'my custom policy'
