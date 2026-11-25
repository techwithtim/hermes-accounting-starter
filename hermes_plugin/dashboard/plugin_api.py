"""Hermes dashboard routes for the Accounting tab.

Mounted by Hermes at /api/plugins/accounting-starter/ behind the dashboard's own
login. Each request runs the installed package's read-only `render` command with
fixed arguments; nothing from the request reaches the command line except a
view name checked against a fixed list.
"""
import asyncio
import json
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter()
HERE = Path(__file__).resolve().parent
VIEWS = {'', 'reports', 'invoices', 'expenses', 'payments', 'clients', 'reviews', 'documents', 'audit'}
FILTERS = {'invoices': {'open', 'overdue', 'paid'}}


def _settings():
    """Paths written by scripts/install.py next to this file."""
    return json.loads((HERE / 'settings.json').read_text(encoding='utf-8'))


@router.get('/page')
async def page(view: str = '', demo: bool = False, filter: str = ''):
    if view not in VIEWS or (filter and filter not in FILTERS.get(view, ())):
        raise HTTPException(404, 'Unknown view')
    settings = _settings()
    command = [settings['executable'], '--data-dir', settings['data_dir']]
    if demo:
        command.append('--demo')
    command += ['render', '--embed'] + ([view] if view else []) + (['--filter', filter] if filter else [])
    # A clean environment: Hermes's own PYTHONPATH would make the package load
    # Hermes's libraries instead of its own.
    env = {'PATH': '/usr/local/bin:/usr/bin:/bin', 'HOME': os.environ.get('HOME', ''),
           'LANG': 'C.UTF-8', 'PYTHONNOUSERSITE': '1'}
    process = await asyncio.create_subprocess_exec(
        *command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL, env=env)
    try:
        out, _ = await asyncio.wait_for(process.communicate(), timeout=30)
    except asyncio.TimeoutError:
        process.kill()
        raise HTTPException(504, 'The ledger took too long to answer')
    if process.returncode != 0:
        raise HTTPException(502, 'Could not read the ledger; ask your agent to check the Accounting Starter install')
    return json.loads(out)
