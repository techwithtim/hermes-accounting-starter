"""Read-only dashboard; the CLI always serves this on loopback."""
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from .ledger import Ledger
from .render import ROOT, VIEWS, embed_css, format_money, render_page, templates as _templates  # noqa: F401


def create_app(path: str | Path, *, demo: bool = False) -> FastAPI:
    ledger = Ledger(Path(path))
    ledger.initialize()
    root = ROOT
    templates = _templates()
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
    def dashboard(request: Request, view: str = '', filter: str = ''):
        try:
            return render_page(ledger, view, demo=demo, env=templates, status_filter=filter)
        except KeyError:
            raise HTTPException(404)

    return app
