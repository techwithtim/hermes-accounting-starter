"""Local-only command line entry point."""
import argparse
import json
from pathlib import Path

from .ledger import Ledger


def main(argv=None):
    parser = argparse.ArgumentParser(prog='accounting-starter', description='Ledger Starter: local-first bookkeeping.')
    parser.add_argument('--data-dir', type=Path, default=Path.home() / '.local/share/hermes-accounting-starter')
    parser.add_argument('--demo', action='store_true', help='Use isolated demo.sqlite3, never the live ledger.')
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('demo', help='Seed fictional data (requires global --demo).')
    commands.add_parser('init', help='Create an empty ledger; preserve existing records.')
    commands.add_parser('mcp', help='Run the accounting MCP server over stdio.')
    commands.add_parser('status', help='Print a JSON summary.')
    serve = commands.add_parser('serve', help='Read-only dashboard on 127.0.0.1 only.', epilog='Remote access: ssh -N -L 8765:127.0.0.1:8765 user@your-server')
    serve.add_argument('--port', type=int, default=8765)
    render = commands.add_parser('render', help='Print one dashboard view (used by the Hermes dashboard tab).')
    render.add_argument('view', nargs='?', default='')
    render.add_argument('--embed', action='store_true', help='Print JSON {html, css} for embedding')
    render.add_argument('--filter', default='', help='Status filter for a view, e.g. overdue for invoices')
    args = parser.parse_args(argv)
    if args.command == 'serve' and not 1 <= args.port <= 65535:
        parser.error('--port must be between 1 and 65535')
    if args.command == 'demo' and not args.demo:
        parser.error('demo requires --demo before the command; live data is never seeded')
    path = args.data_dir.expanduser() / ('demo.sqlite3' if args.demo else 'ledger.sqlite3')
    if path.is_symlink() or (path.exists() and path.stat().st_nlink > 1):
        parser.error('ledger files must not be symbolic or hard links; demo/live isolation is required')
    ledger = Ledger(path).initialize()
    if args.command == 'demo':
        ledger.seed_demo()
        print(f'Fictional DEMO ready: {path}')
    elif args.command == 'init':
        print(f'Ledger ready: {path}')
    elif args.command == 'mcp':
        import os
        from .mcp_server import create_server
        os.environ['ACCOUNTING_DATA_DIR'] = str(args.data_dir.expanduser().resolve())
        create_server(ledger).run(transport='stdio')
    elif args.command == 'serve':
        import uvicorn
        from .web import create_app
        uvicorn.run(create_app(path, demo=args.demo), host='127.0.0.1', port=args.port, access_log=False)
    elif args.command == 'render':
        from .render import FILTERS, VIEWS, embed_css, render_page
        if args.view and args.view not in VIEWS:
            parser.error('unknown view; choose one of: ' + ', '.join(VIEWS))
        if args.filter and args.filter not in FILTERS.get(args.view, {}):
            parser.error('unknown filter for this view')
        html = render_page(ledger, args.view, demo=args.demo, embed=args.embed, status_filter=args.filter)
        print(json.dumps({'html': html, 'css': embed_css()}) if args.embed else html)
    elif args.command == 'status':
        print(json.dumps(ledger.summary(), indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
