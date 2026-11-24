"""Offline contract tests against the installed Composio SDK; no OAuth claims."""
import importlib
from types import SimpleNamespace as NS
from unittest.mock import create_autospec

import pytest
from composio import Composio


def adapter():
    try:
        return importlib.import_module('accounting_starter.composio_email')
    except ModuleNotFoundError:
        pytest.fail('Composio adapter has not been implemented')


def client():
    real = Composio(api_key='unit-test-not-a-real-key')
    return NS(connected_accounts=NS(link=create_autospec(real.connected_accounts.link),
                                   get=create_autospec(real.connected_accounts.get)),
              auth_configs=NS(get=create_autospec(real.auth_configs.get)),
              tools=NS(proxy=create_autospec(real.tools.proxy)))


def test_initiate_checks_readonly_config_before_returning_link():
    module = adapter()
    c = client()
    c.auth_configs.get.return_value = NS(toolkit=NS(slug='gmail'), auth_scheme='OAUTH2',
        status='ENABLED', credentials={'scopes': 'https://www.googleapis.com/auth/gmail.readonly'})
    c.connected_accounts.link.return_value = NS(id='ca_test', redirect_url='https://connect.composio.dev/link/test')
    assert module.initiate_connection(c, user_id='user-test', auth_config_id='ac_test') == {
        'connected_account_id': 'ca_test', 'redirect_url': 'https://connect.composio.dev/link/test'}
    c.connected_accounts.link.assert_called_once_with(user_id='user-test', auth_config_id='ac_test')
    c.connected_accounts.link.reset_mock()
    c.auth_configs.get.return_value.credentials['scopes'] = 'https://mail.google.com/'
    with pytest.raises(ValueError, match='read-only'):
        module.initiate_connection(c, user_id='user-test', auth_config_id='ac_test')
    c.connected_accounts.link.assert_not_called()


def active_client():
    c = client()
    c.connected_accounts.get.return_value = NS(id='ca_test', user_id='user-test',
        toolkit=NS(slug='gmail'), auth_config=NS(id='ac_test', is_disabled=False),
        is_disabled=False, status='ACTIVE', requested_scopes=[adapter().READONLY_SCOPE])
    return c


def test_status_is_sanitized_and_rejects_wrong_owner():
    m = adapter()
    c = active_client()
    assert m.connection_status(c, user_id='user-test', connected_account_id='ca_test') == {
        'connected_account_id': 'ca_test', 'status': 'ACTIVE', 'ready': True}
    with pytest.raises(ValueError, match='owner'):
        m.connection_status(c, user_id='other', connected_account_id='ca_test')
    c.connected_accounts.get.return_value.status = 'INITIATED'
    assert not m.connection_status(c, user_id='user-test', connected_account_id='ca_test')['ready']


def test_fetch_paginates_and_gets_full_messages():
    m = adapter()
    c = active_client()
    c.tools.proxy.side_effect = [
        NS(status=200, data={'messages': [{'id': 'a'}], 'nextPageToken': 'next'}),
        NS(status=200, data={'id': 'a', 'payload': {}}),
        NS(status=200, data={'messages': [{'id': 'b'}]}),
        NS(status=200, data={'id': 'b', 'payload': {}}),
    ]
    assert [x['id'] for x in m.iter_messages(c, user_id='user-test', connected_account_id='ca_test', query='has:attachment')] == ['a', 'b']
    calls = [call.kwargs for call in c.tools.proxy.call_args_list]
    assert all(x['method'] == 'GET' and x['user_id'] == 'user-test' and x['connected_account_id'] == 'ca_test' for x in calls)
    assert calls[0]['endpoint'] == '/gmail/v1/users/me/messages'
    assert {'name': 'pageToken', 'value': 'next', 'in': 'query'} in calls[2]['parameters']
    assert calls[1]['endpoint'] == '/gmail/v1/users/me/messages/a'


@pytest.mark.parametrize('failure', ['inactive', 'broad_scope', 'http', 'cycle', 'path', 'page_size'])
def test_fetch_fails_closed(failure):
    m = adapter()
    c = active_client()
    c.tools.proxy.return_value = NS(status=200, data={})
    kwargs = {}
    if failure == 'inactive':
        c.connected_accounts.get.return_value.status = 'EXPIRED'
    elif failure == 'broad_scope':
        c.connected_accounts.get.return_value.requested_scopes = ['https://mail.google.com/']
    elif failure == 'http':
        c.tools.proxy.return_value.status = 403
    elif failure == 'cycle':
        c.tools.proxy.return_value.data = {'nextPageToken': 'repeat'}
        kwargs['max_pages'] = 3
    elif failure == 'path':
        c.tools.proxy.return_value.data = {'messages': [{'id': '../../settings'}]}
    else:
        kwargs['page_size'] = 501
    with pytest.raises((ValueError, RuntimeError)):
        list(m.iter_messages(c, user_id='user-test', connected_account_id='ca_test', **kwargs))
    if failure in ('inactive', 'broad_scope', 'page_size'):
        c.tools.proxy.assert_not_called()
    if failure == 'path':
        assert c.tools.proxy.call_count == 1
    if failure == 'cycle':
        assert c.tools.proxy.call_count == 2


def test_fetch_attachment_decodes_bytes_without_writing_filename():
    m = adapter()
    c = active_client()
    c.tools.proxy.return_value = NS(status=200, data={'data': 'JVBERi0', 'size': 5})
    assert m.fetch_attachment(c, user_id='user-test', connected_account_id='ca_test', message_id='abc', attachment_id='att') == b'%PDF-'
    assert c.tools.proxy.call_args.kwargs['endpoint'] == '/gmail/v1/users/me/messages/abc/attachments/att'
    c.tools.proxy.return_value.data['data'] = '!!!'
    with pytest.raises(ValueError):
        m.fetch_attachment(c, user_id='user-test', connected_account_id='ca_test', message_id='abc', attachment_id='att')


def test_cli_connect_prompts_secret_and_prints_link(monkeypatch, capsys):
    m = adapter()
    c = client()
    c.auth_configs.get.return_value = NS(toolkit=NS(slug='gmail'), auth_scheme='OAUTH2',
        status='ENABLED', credentials={'scopes': m.READONLY_SCOPE})
    c.connected_accounts.link.return_value = NS(id='ca_test', redirect_url='https://connect.composio.dev/link/test')
    monkeypatch.delenv('COMPOSIO_API_KEY', raising=False)
    monkeypatch.setattr('getpass.getpass', lambda prompt: 'prompted-test-secret')
    monkeypatch.setattr('composio.Composio', lambda **kwargs: c if kwargs['api_key'] == 'prompted-test-secret' else None)
    assert m.main(['connect', '--user-id', 'user-test', '--auth-config-id', 'ac_test']) == 0
    out = capsys.readouterr().out
    assert 'https://connect.composio.dev/link/test' in out
    assert 'prompted-test-secret' not in out


def test_cli_status_and_fetch_private_json(monkeypatch, capsys, tmp_path):
    import json
    import stat
    m = adapter()
    c = active_client()
    monkeypatch.setenv('COMPOSIO_API_KEY', 'unit-test')
    monkeypatch.setattr('composio.Composio', lambda **kwargs: c)
    base = ['--user-id', 'user-test', '--connected-account-id', 'ca_test']
    assert m.main(['status', *base]) == 0
    assert json.loads(capsys.readouterr().out)['ready']
    c.tools.proxy.side_effect = [NS(status=200, data={'messages': [{'id': 'a'}]}),
                               NS(status=200, data={'id': 'a', 'payload': {}})]
    output = tmp_path / 'mail.json'
    assert m.main(['fetch', *base, '--output', str(output)]) == 0
    assert json.loads(output.read_text())['messages'][0]['id'] == 'a'
    assert stat.S_IMODE(output.stat().st_mode) == 0o600
    assert 'payload' not in capsys.readouterr().out
    with pytest.raises(FileExistsError):
        m.main(['fetch', *base, '--output', str(output)])


def test_cli_rejects_repo_output_before_network(monkeypatch):
    from pathlib import Path
    m = adapter()
    monkeypatch.setenv('COMPOSIO_API_KEY', 'unit-test')
    c = active_client()
    monkeypatch.setattr('composio.Composio', lambda **kwargs: c)
    output = Path(m.__file__).resolve().parents[2] / 'private-mail.json'
    with pytest.raises(ValueError, match='outside'):
        m.main(['fetch', '--user-id', 'user-test', '--connected-account-id', 'ca_test', '--output', str(output)])
    assert not output.exists()
    c.connected_accounts.get.assert_not_called()


def test_connect_rejects_unsafe_identity_and_url():
    m = adapter()
    c = client()
    with pytest.raises(ValueError, match='user'):
        m.initiate_connection(c, user_id='default', auth_config_id='ac_test')
    c.auth_configs.get.assert_not_called()
    c.auth_configs.get.return_value = NS(toolkit=NS(slug='gmail'), auth_scheme='OAUTH2',
        status='ENABLED', credentials={'scopes': m.READONLY_SCOPE})
    c.connected_accounts.link.return_value = NS(id='ca_test', redirect_url='http://unsafe.example/link')
    with pytest.raises(ValueError, match='HTTPS'):
        m.initiate_connection(c, user_id='user-test', auth_config_id='ac_test')


def test_installed_sdk_serializes_proxy_request_without_network():
    import httpx
    import json
    requests = []
    def handle(request):
        requests.append(request)
        if request.method == 'GET':
            return httpx.Response(200, json={'id': 'ca_test', 'user_id': 'user-test',
                'toolkit': {'slug': 'gmail'}, 'auth_config': {'is_disabled': False},
                'status': 'ACTIVE', 'is_disabled': False,
                'requested_scopes': [adapter().READONLY_SCOPE]})
        return httpx.Response(200, json={'status': 200, 'data': {'messages': []}})
    with httpx.Client(transport=httpx.MockTransport(handle)) as http:
        c = Composio(api_key='unit-test-not-a-real-key', http_client=http)
        assert list(adapter().iter_messages(c, user_id='user-test', connected_account_id='ca_test')) == []
    body = json.loads(requests[-1].content)
    assert body['method'] == 'GET'
    assert body['endpoint'] == '/gmail/v1/users/me/messages'
    assert body['user_id'] == 'user-test'
    assert body['connected_account_id'] == 'ca_test'


def test_cli_entry_suppresses_remote_error_secrets(monkeypatch, capsys):
    m = adapter()
    def broken(argv=None):
        raise RuntimeError('remote response contains SECRET')
    monkeypatch.setattr(m, 'main', broken)
    assert m.cli([]) == 1
    captured = capsys.readouterr()
    assert 'SECRET' not in captured.err + captured.out
    assert 'failed' in captured.err


def test_environment_client_requires_explicit_key(monkeypatch):
    module = adapter()
    monkeypatch.delenv('COMPOSIO_API_KEY', raising=False)
    with pytest.raises(ValueError, match='COMPOSIO_API_KEY'):
        module.client_from_env()
    monkeypatch.setenv('COMPOSIO_API_KEY', 'unit-test-not-a-real-key')
    assert isinstance(module.client_from_env(), Composio)
