import importlib
import json


def test_init_status_default_and_explicit_data_dir(tmp_path, monkeypatch, capsys):
    assert importlib.util.find_spec('accounting_starter.cli') is not None, 'CLI missing'
    from accounting_starter.cli import main
    monkeypatch.setenv('HOME', str(tmp_path))
    assert main(['init']) == 0
    path = tmp_path / '.local/share/hermes-accounting-starter/ledger.sqlite3'
    assert path.exists()
    capsys.readouterr()
    assert main(['status']) == 0
    assert json.loads(capsys.readouterr().out)['counts']['clients'] == 0
    assert main(['--data-dir', str(tmp_path / 'custom'), 'init']) == 0
    assert (tmp_path / 'custom/ledger.sqlite3').exists()


def test_demo_requires_explicit_flag_and_never_touches_live(tmp_path, capsys):
    import pytest
    from accounting_starter.cli import main
    from accounting_starter.ledger import Ledger
    from accounting_starter.web import create_app
    from fastapi.testclient import TestClient
    args = ['--data-dir', str(tmp_path)]
    main(args + ['init'])
    live = Ledger(tmp_path / 'ledger.sqlite3')
    live.create_client('Live client only')
    before = (tmp_path / 'ledger.sqlite3').read_bytes()
    with pytest.raises(SystemExit):
        main(args + ['demo'])
    assert not (tmp_path / 'demo.sqlite3').exists()
    assert main(args + ['--demo', 'demo']) == 0
    assert (tmp_path / 'ledger.sqlite3').read_bytes() == before
    demo = Ledger(tmp_path / 'demo.sqlite3')
    assert demo.summary()['is_demo']
    assert demo.summary()['counts']['invoices'] > 0
    assert live.summary()['counts']['invoices'] == 0
    response = TestClient(create_app(tmp_path / 'demo.sqlite3', demo=True)).get('/clients')
    assert 'Demo data' in response.text
    assert 'Live client only' not in response.text
    capsys.readouterr()
    main(args + ['--demo', 'status'])
    assert json.loads(capsys.readouterr().out)['is_demo']


def test_serve_binds_loopback_and_disables_access_logs(tmp_path, monkeypatch):
    import uvicorn
    import pytest
    from accounting_starter.cli import main
    calls = []
    monkeypatch.setattr(uvicorn, 'run', lambda app, **kwargs: calls.append(kwargs))
    assert main(['--data-dir', str(tmp_path), 'serve']) == 0
    assert calls == [{'host': '127.0.0.1', 'port': 8765, 'access_log': False}]
    with pytest.raises(SystemExit):
        main(['--data-dir', str(tmp_path), 'serve', '--host', '0.0.0.0'])
    with pytest.raises(SystemExit):
        main(['--data-dir', str(tmp_path), 'serve', '--port', '70000'])


def test_mcp_uses_selected_ledger_and_clean_stdio(tmp_path, monkeypatch, capsys):
    import os
    from mcp.server.fastmcp import FastMCP
    from accounting_starter.cli import main
    calls = []
    monkeypatch.setattr(FastMCP, 'run', lambda self, **kwargs: calls.append(kwargs))
    monkeypatch.setenv('ACCOUNTING_DATA_DIR', 'must-be-overridden')
    assert main(['--data-dir', str(tmp_path), '--demo', 'mcp']) == 0
    assert calls == [{'transport': 'stdio'}]
    assert os.environ['ACCOUNTING_DATA_DIR'] == str(tmp_path.resolve())
    assert (tmp_path / 'demo.sqlite3').exists()
    assert not (tmp_path / 'ledger.sqlite3').exists()
    assert capsys.readouterr().out == ''


def test_demo_refuses_symlink_to_live_ledger(tmp_path):
    import pytest
    from accounting_starter.cli import main
    main(['--data-dir', str(tmp_path), 'init'])
    live = tmp_path / 'ledger.sqlite3'
    (tmp_path / 'demo.sqlite3').symlink_to(live)
    before = live.read_bytes()
    with pytest.raises(SystemExit):
        main(['--data-dir', str(tmp_path), '--demo', 'demo'])
    assert live.read_bytes() == before
