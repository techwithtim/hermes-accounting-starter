"""Dashboard page rendering, kept free of the web server so `render` starts fast."""
from decimal import Decimal
from pathlib import Path

from babel.numbers import get_currency_precision
from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).parent

VIEWS = {'invoices': 'Invoices', 'expenses': 'Expenses', 'payments': 'Payments',
         'clients': 'Clients', 'reviews': 'Review queue', 'documents': 'Documents', 'audit': 'Audit trail'}

# Layout fixes for showing the dashboard inside another page (the Hermes
# dashboard tab), where it lives in a shadow root instead of owning <body>.
EMBED_CSS = (':host{display:block}.ls-app{display:flex;align-items:stretch;min-height:70vh;'
             'background:var(--paper);color:var(--navy);font:15px/1.6 system-ui,-apple-system,'
             'BlinkMacSystemFont,"Segoe UI",sans-serif;border-radius:10px;overflow:hidden}'
             '.ls-app .sidebar{position:relative;inset:auto;flex:0 0 245px}'
             '.ls-app .workspace{margin-left:0;flex:1;min-width:0}'
             '@media(max-width:650px){.ls-app{display:block}}')


def format_money(amount_minor, currency):
    precision = get_currency_precision(currency)
    value = Decimal(amount_minor).scaleb(-precision)
    return f"{currency} {value:,.{precision}f}"


def templates():
    env = Environment(loader=FileSystemLoader(ROOT / 'templates'), autoescape=select_autoescape(['html']))
    env.filters['money'] = format_money
    return env


def render_page(ledger, view: str = '', *, demo: bool = False, embed: bool = False, env=None) -> str:
    """Render one dashboard view. All ledger text is autoescaped by Jinja."""
    if view and view not in VIEWS:
        raise KeyError(view)
    rows = ledger.list_records(view) if view else []
    columns = list(dict.fromkeys(key for row in rows for key in row))
    summary = ledger.summary()
    return (env or templates()).get_template('dashboard.html').render(
        summary=summary, demo=demo or summary.get('is_demo', False), views=VIEWS, embed=embed,
        view=view, title=VIEWS.get(view, 'Financial overview'), rows=rows, columns=columns)


def embed_css() -> str:
    """The dashboard stylesheet scoped for a shadow root, plus embed layout fixes."""
    css = (ROOT / 'static' / 'style.css').read_text(encoding='utf-8')
    css = css.replace(':root{', ':host{', 1).replace('body{', '.ls-app{', 1)
    return css + EMBED_CSS
