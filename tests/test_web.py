import importlib

from fastapi.testclient import TestClient


def test_dashboard_shows_empty_ledger_and_currency_summary(tmp_path):
    assert importlib.util.find_spec('accounting_starter.web') is not None, 'dashboard module missing'
    from accounting_starter.web import create_app
    client = TestClient(create_app(tmp_path / 'ledger.sqlite3'))
    response = client.get('/')
    assert response.status_code == 200
    assert 'Ledger' in response.text
    assert 'Nothing booked yet' in response.text
    assert 'Your books' in response.text


def test_accessible_record_views_escape_untrusted_text(tmp_path):
    from accounting_starter.ledger import Ledger
    from accounting_starter.web import create_app
    path = tmp_path / 'ledger.sqlite3'
    ledger = Ledger(path).initialize()
    ledger.create_client('<script>alert("x")</script>')
    client = TestClient(create_app(path))
    for kind in ('invoices', 'expenses', 'payments', 'clients', 'reviews', 'audit'):
        response = client.get('/' + kind)
        assert response.status_code == 200
        assert '<nav aria-label="Main navigation">' in response.text
        assert '<main id="main">' in response.text
    response = client.get('/clients')
    assert '<script>' not in response.text
    assert '&lt;script&gt;' in response.text
    assert '<caption>' in response.text
    assert 'scope="col"' in response.text
    assert client.get('/unknown').status_code == 404
    assert client.post('/clients').status_code == 405
    assert client.get('/static/style.css').status_code == 200
    assert 'ssh -N -L 8765:127.0.0.1:8765' in client.get('/').text


def test_dashboard_blocks_dns_rebinding_and_has_security_headers(tmp_path):
    from accounting_starter.web import create_app
    client = TestClient(create_app(tmp_path / 'ledger.sqlite3'))
    response = client.get('/')
    assert response.headers['cache-control'] == 'no-store'
    assert "default-src 'none'" in response.headers['content-security-policy']
    assert response.headers['x-content-type-options'] == 'nosniff'
    assert client.get('/', headers={'host': 'evil.example'}).status_code == 400


def test_health_and_document_metadata_views(tmp_path):
    from accounting_starter.web import create_app
    client = TestClient(create_app(tmp_path / 'ledger.sqlite3'))
    assert client.get('/health').status_code == 200
    assert client.get('/health').json()['status'] == 'ok'
    assert client.get('/health').json()['ledger'] in {'demo', 'live'}
    assert client.get('/documents').status_code == 200
