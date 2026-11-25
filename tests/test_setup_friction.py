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
