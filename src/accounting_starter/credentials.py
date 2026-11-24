"""Private local API key storage. Never located under the public checkout."""
import json
import os
from pathlib import Path
import stat


def default_path():
    return Path.home()/'.config/hermes-accounting-starter/credentials.json'


def _path(path):
    path = Path(path).expanduser()
    if path.is_symlink():
        raise ValueError('Credential file must not be a symlink')
    path = path.resolve()
    source_root = Path(__file__).resolve().parents[2]
    if path.is_relative_to(source_root) or any((p/'.git').exists() or (p/'pyproject.toml').exists() for p in path.parents):
        raise ValueError('Credentials must be outside source repositories')
    return path


def save_key(path, key):
    path = _path(path)
    if not isinstance(key, str) or not key.strip():
        raise ValueError('API key must not be empty')
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.parent.stat().st_mode & 0o077:
        raise ValueError('Credential directory permissions must be 0700')
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as out:
        json.dump({'composio_api_key': key.strip()}, out)


def load_key(path):
    path = _path(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd) as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077 or info.st_uid != os.getuid() or info.st_nlink != 1:
            raise ValueError('Unsafe credential file permissions or ownership')
        key = json.load(stream).get('composio_api_key', '')
    if not isinstance(key, str) or not key.strip():
        raise ValueError('API key must not be empty')
    return key.strip()
