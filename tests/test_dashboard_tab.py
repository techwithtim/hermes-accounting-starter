"""The Hermes dashboard tab: embed rendering, the plugin route and the installer copy."""
import asyncio
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_embed_render_has_only_in_page_links_and_scoped_css(tmp_path, capsys):
    from accounting_starter.cli import main
    assert main(['--data-dir', str(tmp_path), '--demo', 'demo']) == 0
    capsys.readouterr()
    assert main(['--data-dir', str(tmp_path), '--demo', 'render', '--embed', 'invoices']) == 0
    page = json.loads(capsys.readouterr().out)
    assert page['html'].startswith('<div class="ls-app">') and '<html' not in page['html']
    assert 'href="/' not in page['html'] and 'data-view="reviews"' in page['html']
    assert 'Demo data' in page['html'] and 'ssh -N' not in page['html']
    assert ':host{' in page['css'] and ':root{' not in page['css'] and 'body{' not in page['css']


def test_render_escapes_ledger_text(tmp_path, capsys):
    from accounting_starter.cli import main
    from accounting_starter.ledger import Ledger
    ledger = Ledger(tmp_path/'ledger.sqlite3').initialize()
    ledger.create_client('<img src=x onerror=alert(1)>', source_id='test:xss')
    assert main(['--data-dir', str(tmp_path), 'render', '--embed', 'clients']) == 0
    html = json.loads(capsys.readouterr().out)['html']
    assert '<img' not in html and '&lt;img' in html


def test_render_rejects_unknown_view(tmp_path):
    from accounting_starter.cli import main
    with pytest.raises(SystemExit):
        main(['--data-dir', str(tmp_path), 'render', '--embed', '../etc'])


def test_plugin_route_validates_view_and_uses_clean_environment(tmp_path, monkeypatch):
    api = load(ROOT/'hermes_plugin/dashboard/plugin_api.py', 'accounting_plugin_api')
    (tmp_path/'settings.json').write_text(json.dumps({'executable': '/app/bin/accounting-starter', 'data_dir': '/data'}))
    monkeypatch.setattr(api, 'HERE', tmp_path)
    monkeypatch.setenv('PYTHONPATH', '/hermes/site-packages')
    seen = {}

    class Done:
        returncode = 0
        async def communicate(self):
            return json.dumps({'html': '<div></div>', 'css': ''}).encode(), b''

    async def fake_exec(*command, **kwargs):
        seen['command'], seen['env'] = command, kwargs['env']
        return Done()

    monkeypatch.setattr(api.asyncio, 'create_subprocess_exec', fake_exec)
    assert asyncio.run(api.page(view='invoices', demo=True)) == {'html': '<div></div>', 'css': ''}
    assert seen['command'] == ('/app/bin/accounting-starter', '--data-dir', '/data', '--demo',
                               'render', '--embed', 'invoices')
    assert 'PYTHONPATH' not in seen['env']
    with pytest.raises(api.HTTPException):
        asyncio.run(api.page(view='; rm -rf /'))


def test_installer_copies_plugin_and_refuses_foreign_directory(tmp_path):
    installer = load(ROOT/'scripts/install.py', 'installer_tab')
    home = tmp_path/'hermes'
    installer.install_dashboard_tab(home, Path('/app/exe'), Path('/data'))
    plugin = home/'plugins/accounting-starter'
    assert (plugin/'plugin.yaml').exists() and (plugin/'dashboard/dist/index.js').exists()
    assert json.loads((plugin/'dashboard/settings.json').read_text()) == {'executable': '/app/exe', 'data_dir': '/data'}
    installer.install_dashboard_tab(home, Path('/app/exe'), Path('/data'))  # rerun is fine
    other = tmp_path/'other'
    (other/'plugins/accounting-starter').mkdir(parents=True)
    with pytest.raises(SystemExit):
        installer.install_dashboard_tab(other, Path('/app/exe'), Path('/data'))


def test_reports_keep_currencies_apart_and_add_up(tmp_path):
    from accounting_starter.ledger import Ledger
    from accounting_starter import reports
    from accounting_starter.render import render_page
    ledger = Ledger(tmp_path/'demo.sqlite3').initialize()
    ledger.seed_demo()
    data = reports.build(ledger)
    usd, others = data['primary'], data['others']
    assert usd['currency'] == 'USD' and others == []
    in_window = [i for i in ledger.list_records('invoices')
                 if i['currency'] == 'USD' and i['issued_date'][:7] in data['months']]
    assert usd['revenue'] == sum(i['amount_minor'] for i in in_window)
    assert usd['net'] == usd['revenue'] - usd['expenses']
    assert usd['rows'][-1]['cumulative'] == usd['net']
    assert usd['outstanding'] == sum(i['balance_minor'] for i in ledger.list_records('invoices') if i['currency'] == 'USD')
    assert usd['growth'] > 0 and usd['overdue_count'] >= 1
    html = render_page(ledger, 'reports', embed=True)
    assert '<svg' in html and 'Month by month' in html and '€' not in html
    overview = render_page(ledger, '', embed=True)
    assert 'You kept' in overview and 'Who owes you' in overview and 'DEMO' not in overview


def test_every_view_renders_for_empty_and_demo_ledgers(tmp_path):
    from accounting_starter.ledger import Ledger
    from accounting_starter.render import VIEWS, render_page
    empty = Ledger(tmp_path/'ledger.sqlite3').initialize()
    demo = Ledger(tmp_path/'demo.sqlite3').initialize()
    demo.seed_demo()
    for ledger in (empty, demo):
        for view in ['', *VIEWS]:
            for embed in (False, True):
                assert '<main id="main">' in render_page(ledger, view, embed=embed)


def test_invoice_filters_and_new_markers(tmp_path):
    from datetime import date
    from fastapi.testclient import TestClient
    from accounting_starter.ledger import Ledger
    from accounting_starter.render import render_page
    from accounting_starter.web import create_app
    path = tmp_path/'demo.sqlite3'
    ledger = Ledger(path).initialize()
    ledger.seed_demo()
    overdue = render_page(ledger, 'invoices', status_filter='overdue')
    assert 'Overdue' in overdue and '>Paid<' not in overdue.split('</thead>')[1]
    client = ledger.list_records('clients')[0]['id']
    ledger.create_invoice(client, 200000, 'USD', description='Website refresh', source='chat',
                          evidence='Requested in chat by the owner', invoice_number='INV-9001',
                          issued_date=date.today().isoformat())
    page = render_page(ledger, 'invoices', embed=True)
    assert 'INV-9001' in page and 'pill-new' in page and 'data-filter="overdue"' in page
    assert 'pill-new' in render_page(ledger, '', embed=True)
    web = TestClient(create_app(path, demo=True))
    assert web.get('/invoices?filter=paid').status_code == 200
    assert web.get('/invoices?filter=bogus').status_code == 404
    assert web.get('/expenses?filter=paid').status_code == 404


def test_plugin_route_rejects_unknown_filter():
    api = load(ROOT/'hermes_plugin/dashboard/plugin_api.py', 'accounting_plugin_api_filter')
    with pytest.raises(api.HTTPException):
        asyncio.run(api.page(view='invoices', filter='../../x'))
    with pytest.raises(api.HTTPException):
        asyncio.run(api.page(view='expenses', filter='paid'))


def test_overview_sentence_reads_well_with_a_single_invoice(tmp_path):
    from datetime import date
    from accounting_starter.ledger import Ledger
    from accounting_starter.render import render_page
    ledger = Ledger(tmp_path/'ledger.sqlite3').initialize()
    client = ledger.create_client('Acme Studio', source='chat')['id']
    ledger.create_invoice(client, 200000, 'USD', issued_date=date.today().isoformat())
    html = render_page(ledger, '', embed=True)
    assert 'That is a 100% profit margin so far.' in html and 'A a' not in html
