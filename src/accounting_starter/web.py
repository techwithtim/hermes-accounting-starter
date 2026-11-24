"""Read-only dashboard; the CLI always serves this on loopback."""
from pathlib import Path
from decimal import Decimal
from babel.numbers import get_currency_precision

def format_money(amount_minor, currency):
    precision = get_currency_precision(currency)
    value = Decimal(amount_minor).scaleb(-precision)
    return f"{currency} {value:,.{precision}f}"


from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader, select_autoescape

from .ledger import Ledger

VIEWS = {'invoices': 'Invoices', 'expenses': 'Expenses', 'payments': 'Payments',
         'clients': 'Clients', 'reviews': 'Review queue', 'documents': 'Documents', 'audit': 'Audit trail'}


def create_app(path: str | Path, *, demo: bool = False) -> FastAPI:
    ledger = Ledger(Path(path))
    ledger.initialize()
    root = Path(__file__).parent
    templates = Environment(loader=FileSystemLoader(root / 'templates'), autoescape=select_autoescape(['html']))
    templates.filters['money'] = format_money
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    app.mount('/static', StaticFiles(directory=root / 'static'), name='static')

    @app.middleware('http')
    async def local_security(request: Request, call_next):
        # Explicit hosts prevent DNS rebinding against an unauthenticated local service.
        host = request.headers.get('host', '').split(':', 1)[0].lower()
        if host not in {'127.0.0.1', 'localhost', 'testserver'}:
            return HTMLResponse('Invalid host', status_code=400)
        response = await call_next(request)
        response.headers['Cache-Control'] = 'no-store'
        response.headers['Content-Security-Policy'] = "default-src 'none'; style-src 'self'; img-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'"
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'no-referrer'
        return response

    @app.get('/health')
    def health():
        summary = ledger.summary()
        return {'status': 'ok', 'ledger': 'demo' if demo or summary['is_demo'] else 'live'}

    @app.get('/', response_class=HTMLResponse)
    @app.get('/{view}', response_class=HTMLResponse)
    def dashboard(request: Request, view: str = ''):
        if view and view not in VIEWS:
            raise HTTPException(404)
        rows = ledger.list_records(view) if view else []
        columns = list(dict.fromkeys(key for row in rows for key in row))
        summary = ledger.summary()
        return templates.get_template('dashboard.html').render(
            summary=summary, demo=demo or summary.get('is_demo', False), views=VIEWS,
            view=view, title=VIEWS.get(view, 'Financial overview'), rows=rows, columns=columns)

    return app
