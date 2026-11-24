import importlib
import json
import os
import pytest


def test_credentials_roundtrip_and_refuses_overwrite(tmp_path):
    assert importlib.util.find_spec('accounting_starter.credentials') is not None
    from accounting_starter.credentials import save_key, load_key
    path = tmp_path/'private'/'credentials.json'
    save_key(path, 'synthetic-test-value')
    assert load_key(path) == 'synthetic-test-value'
    assert path.stat().st_mode & 0o777 == 0o600
    assert path.parent.stat().st_mode & 0o777 == 0o700
    with pytest.raises(FileExistsError):
        save_key(path, 'another-test-value')
    path.chmod(0o644)
    with pytest.raises(ValueError, match='permissions'):
        load_key(path)


def test_credentials_reject_repo_and_symlink(tmp_path):
    from accounting_starter.credentials import save_key, load_key
    repo = tmp_path/'repo'; repo.mkdir(); (repo/'.git').mkdir()
    with pytest.raises(ValueError):
        save_key(repo/'credentials.json', 'synthetic-test-value')
    dest = tmp_path/'dest'; dest.write_text('{}'); link = tmp_path/'link'; link.symlink_to(dest)
    with pytest.raises(ValueError):
        load_key(link)


def test_cli_configure_and_later_noninteractive_status(tmp_path, monkeypatch, capsys):
    from accounting_starter import composio_email as m
    from accounting_starter import credentials
    from types import SimpleNamespace as NS
    path = tmp_path/'private'/'credentials.json'
    monkeypatch.setattr(credentials, 'default_path', lambda: path)
    monkeypatch.delenv('COMPOSIO_API_KEY', raising=False)
    monkeypatch.setattr('getpass.getpass', lambda prompt: 'synthetic-test-value')
    assert m.main(['configure']) == 0
    assert path.is_file()
    monkeypatch.setattr('getpass.getpass', lambda prompt: pytest.fail('must use saved credential'))
    monkeypatch.setattr('composio.Composio', lambda **kwargs: NS(key=kwargs['api_key']))
    monkeypatch.setattr(m, 'connection_status', lambda client, **kwargs: {'ready': client.key == 'synthetic-test-value'})
    assert m.main(['status', '--user-id', 'synthetic-owner', '--connected-account-id', 'ca_test']) == 0
    assert 'synthetic-test-value' not in capsys.readouterr().out
