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
    assert mod.dashboard_url(tmp_path) is None
    (tmp_path/'config.yaml').write_text('dashboard:\n  public_url: "https://hermes.example.com/"\n')
    assert mod.dashboard_url(tmp_path) == 'https://hermes.example.com'
    monkeypatch.setenv('HERMES_DASHBOARD_PUBLIC_URL', 'http://203.0.113.7:9119')
    assert mod.dashboard_url(tmp_path) == 'http://203.0.113.7:9119'
