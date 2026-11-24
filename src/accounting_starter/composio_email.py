"""Read-only Gmail through Composio 0.34.0. Credentials stay in private local storage."""
import os
import re

READONLY_SCOPE = 'https://www.googleapis.com/auth/gmail.readonly'


def _readonly(scopes):
    if isinstance(scopes, str):
        scopes = re.split(r'[ ,]+', scopes.strip())
    if not isinstance(scopes, list) or set(scopes) != {READONLY_SCOPE}:
        raise ValueError('Explicit Gmail read-only scope required; missing or broader scopes rejected')


def initiate_connection(client, *, user_id, auth_config_id):
    """Return a hosted OAuth link, not proof of completed authorization."""
    if not user_id.strip() or user_id == 'default':
        raise ValueError('A stable, non-default user ID is required')
    config = client.auth_configs.get(auth_config_id)
    if config.toolkit.slug != 'gmail' or config.auth_scheme != 'OAUTH2' or config.status != 'ENABLED':
        raise ValueError('Enabled Gmail OAuth2 auth config required')
    _readonly((config.credentials or {}).get('scopes'))
    request = client.connected_accounts.link(user_id=user_id, auth_config_id=auth_config_id)
    from urllib.parse import urlsplit
    url = urlsplit(request.redirect_url or '')
    if url.scheme != 'https' or not url.hostname or url.username or url.password:
        raise ValueError('Composio did not return an HTTPS connection link')
    return {'connected_account_id': request.id, 'redirect_url': request.redirect_url}


def connection_status(client, *, user_id, connected_account_id):
    """Check ownership and scope snapshot; never return tokens or raw account state."""
    account = client.connected_accounts.get(connected_account_id)
    if account.user_id != user_id or account.id != connected_account_id:
        raise ValueError('Connected account owner mismatch')
    if account.toolkit.slug != 'gmail':
        raise ValueError('Gmail connected account required')
    ready = account.status == 'ACTIVE' and not account.is_disabled and not account.auth_config.is_disabled
    if ready:
        _readonly(account.requested_scopes)
    return {'connected_account_id': account.id, 'status': account.status, 'ready': ready}


def _identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_-]+', value):
        raise ValueError('Invalid Gmail identifier')
    return value


def _get(client, user_id, connected_account_id, endpoint, **params):
    response = client.tools.proxy(user_id=user_id, connected_account_id=connected_account_id,
        endpoint=endpoint, method='GET',
        parameters=[{'name': k, 'value': str(v), 'in': 'query'} for k, v in params.items()])
    if response.status != 200 or not isinstance(response.data, dict):
        raise RuntimeError('Gmail read failed or returned an invalid response')
    return response.data


def iter_messages(client, *, user_id, connected_account_id, query='', page_size=100, max_pages=100):
    """Yield full Gmail message dictionaries; exhaust pagination or raise (never truncate silently)."""
    if not connection_status(client, user_id=user_id, connected_account_id=connected_account_id)['ready']:
        raise ValueError('Gmail connection is not ACTIVE')
    if not 1 <= page_size <= 500 or max_pages < 1:
        raise ValueError('page_size must be 1..500 and max_pages positive')
    token = None
    seen = set()
    for _ in range(max_pages):
        params = {'q': query, 'maxResults': page_size}
        if token:
            params['pageToken'] = token
        page = _get(client, user_id, connected_account_id, '/gmail/v1/users/me/messages', **params)
        for message in page.get('messages', []):
            _identifier(message['id'])
            yield _get(client, user_id, connected_account_id,
                '/gmail/v1/users/me/messages/' + message['id'], format='full')
        token = page.get('nextPageToken')
        if not token:
            return
        if token in seen:
            raise RuntimeError('Repeated Gmail page token')
        seen.add(token)
    raise RuntimeError('Gmail pagination limit reached; narrow the query or increase max_pages')


def fetch_attachment(client, *, user_id, connected_account_id, message_id, attachment_id):
    """Return attachment bytes in memory; caller chooses private storage, never email filenames."""
    import base64
    if not connection_status(client, user_id=user_id, connected_account_id=connected_account_id)['ready']:
        raise ValueError('Gmail connection is not ACTIVE')
    endpoint = f'/gmail/v1/users/me/messages/{_identifier(message_id)}/attachments/{_identifier(attachment_id)}'
    data = _get(client, user_id, connected_account_id, endpoint)
    encoded = data['data']
    return base64.b64decode(encoded + '=' * (-len(encoded) % 4), altchars=b'-_', validate=True)


def client_from_env():
    """Construct the installed SDK using only an explicit COMPOSIO_API_KEY."""
    from composio import Composio
    key = os.environ.get('COMPOSIO_API_KEY', '').strip()
    if not key:
        raise ValueError('COMPOSIO_API_KEY is required')
    return Composio(api_key=key)


def main(argv=None):
    """CLI; API keys use environment/private file/no-echo prompt, never arguments."""
    import argparse
    import getpass
    import json
    from composio import Composio
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('configure', help='Save your API key privately for unattended scans')
    connect = commands.add_parser('connect')
    connect.add_argument('--user-id', required=True)
    connect.add_argument('--auth-config-id', required=True)
    status = commands.add_parser('status')
    fetch = commands.add_parser('fetch')
    for sub in (status, fetch):
        sub.add_argument('--user-id', required=True)
        sub.add_argument('--connected-account-id', required=True)
    fetch.add_argument('--query', default='')
    fetch.add_argument('--max-pages', type=int, default=100)
    fetch.add_argument('--output', required=True)
    args = parser.parse_args(argv)
    from .credentials import default_path, save_key, load_key
    private_path = default_path()
    if args.command == 'configure':
        save_key(private_path, getpass.getpass('Composio project API key (saved privately): '))
        print(json.dumps({'configured': True, 'credentials_file': str(private_path)}))
        return 0
    key = os.environ.get('COMPOSIO_API_KEY')
    if not key and private_path.exists():
        key = load_key(private_path)
    if not key:
        key = getpass.getpass('Composio project API key: ')
    if not key.strip():
        raise ValueError('COMPOSIO_API_KEY is required')
    client = Composio(api_key=key.strip())
    if args.command == 'connect':
        result = initiate_connection(client, user_id=args.user_id, auth_config_id=args.auth_config_id)
    elif args.command == 'status':
        result = connection_status(client, user_id=args.user_id, connected_account_id=args.connected_account_id)
    else:
        from pathlib import Path
        output = Path(args.output).expanduser().resolve()
        roots = [Path(__file__).resolve().parents[2]]
        roots.extend(p for p in output.parents if (p / '.git').exists() or (p / 'pyproject.toml').exists())
        if any(output.is_relative_to(root) for root in roots):
            raise ValueError('Private output must be outside source repositories')
        args.output = str(output)
        fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(fd, 'w') as stream:
                messages = list(iter_messages(client, user_id=args.user_id,
                    connected_account_id=args.connected_account_id, query=args.query, max_pages=args.max_pages))
                json.dump({'messages': messages}, stream)
        except Exception:
            os.unlink(args.output)
            raise
        result = {'output': args.output, 'count': len(messages)}
    print(json.dumps(result))
    return 0


def cli(argv=None):
    """Redact exceptions at the terminal boundary; never dump remote responses."""
    import sys
    try:
        return main(argv)
    except Exception:
        print('Composio operation failed. Check API permissions, read-only scopes, account status and private output path; see docs/COMPOSIO.md.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(cli())
