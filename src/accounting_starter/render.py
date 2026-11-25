"""Dashboard page rendering, kept free of the web server so `render` starts fast."""
from collections import defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path

from babel.numbers import get_currency_precision
from jinja2 import Environment, FileSystemLoader, select_autoescape

from . import charts, reports

ROOT = Path(__file__).parent

# Record views (ledger kinds) plus the two report pages.
VIEWS = {'reports': 'Reports', 'invoices': 'Invoices', 'payments': 'Payments', 'expenses': 'Expenses',
         'clients': 'Clients', 'reviews': 'Review queue', 'documents': 'Documents', 'audit': 'Activity log'}
NAV = [[('', 'Overview'), ('reports', 'Reports')],
       [('invoices', 'Invoices'), ('payments', 'Payments'), ('expenses', 'Expenses'), ('clients', 'Clients')],
       [('reviews', 'Review queue'), ('documents', 'Documents'), ('audit', 'Activity log')]]

# Extra layout rules for the Hermes dashboard tab, where the page lives in a
# shadow root instead of owning <body>.
EMBED_CSS = ':host{display:block}.ls-app{border-radius:14px;overflow:hidden;min-height:80vh}'


def format_money(amount_minor, currency):
    precision = get_currency_precision(currency)
    value = Decimal(amount_minor).scaleb(-precision)
    return f"{currency} {value:,.{precision}f}"


def templates():
    env = Environment(loader=FileSystemLoader(ROOT / 'templates'), autoescape=select_autoescape(['html']),
                      trim_blocks=True, lstrip_blocks=True)
    env.filters['money'] = format_money
    env.filters['cash'] = charts.money
    env.filters['day'] = reports.date_label
    env.filters['monthname'] = lambda m: reports.month_label(m, short=False)
    env.filters['initials'] = initials
    env.filters['hue'] = hue
    return env


def _cell(text, cls='', avatar=None, new=False):
    return {'text': text, 'cls': cls, 'avatar': avatar, 'new': new}


def initials(name):
    words = [w for w in str(name).replace('&', ' ').split() if w[:1].isalnum()]
    return ''.join(w[0] for w in words[:2]).upper() or '?'


def hue(name):
    """One of six palette tones, stable per name."""
    return sum(map(ord, str(name))) % 6


FILTERS = {'invoices': {'open': 'Open', 'overdue': 'Overdue', 'paid': 'Paid'}}


def _num(amount, currency, cls='num'):
    return _cell(charts.money(amount, currency, cents=True), cls)


STATUS = {'paid': ('Paid', 'ok'), 'partial': ('Part paid', 'warn'), 'unpaid': ('Open', 'open'),
          'overdue': ('Overdue', 'bad'), 'pending': ('Needs review', 'warn'), 'resolved': ('Resolved', 'ok')}


def _pill(status):
    label, tone = STATUS.get(status, (status or '—', 'open'))
    return _cell(label, 'pill pill-' + tone)


def table(ledger, view, status_filter=''):
    """Columns and rows for one record view, newest first, with names instead of IDs."""
    clients = {c['id']: c for c in ledger.list_records('clients')}

    def name(cid):
        return clients.get(cid, {}).get('name', '—')

    if view == 'audit':
        records = ledger.list_records('audit')[::-1]
        cols = [('When', ''), ('What happened', ''), ('Record', ''), ('Number', 'num')]
        rows = [[_cell(r['created_at'][:16].replace('T', ' ')), _cell(r['action'].capitalize()),
                 _cell(r['kind'].rstrip('s').capitalize()), _cell(f"#{r['record_id']}", 'num')] for r in records]
        return cols, rows, {}
    records = ledger.list_records(view)
    totals = defaultdict(int)
    today = date.today().isoformat()
    if view == 'invoices':
        records.sort(key=lambda r: (r.get('issued_date') or '', r['id']), reverse=True)
        if status_filter == 'open':
            records = [r for r in records if r['status'] in ('unpaid', 'partial')]
        elif status_filter in ('overdue', 'paid'):
            records = [r for r in records if r['status'] == status_filter]
        cols = [('Invoice', ''), ('Client', ''), ('Issued', ''), ('Due', ''), ('Amount', 'num'),
                ('Still owed', 'num'), ('Status', '')]
        rows = []
        for r in records:
            totals[r['currency']] += r['balance_minor']
            rows.append([_cell(r.get('invoice_number') or f"#{r['id']}", 'strong', new=r.get('issued_date') == today),
                         _cell(name(r['client_id']), avatar=name(r['client_id'])),
                         _cell(reports.date_label(r.get('issued_date'))), _cell(reports.date_label(r.get('due_date'))),
                         _num(r['amount_minor'], r['currency']),
                         _num(r['balance_minor'], r['currency']) if r['balance_minor'] else _cell('—', 'num'),
                         _pill(r['status'])])
        return cols, rows, {'Still owed': dict(totals)}
    if view in ('payments', 'expenses'):
        field = 'received_date' if view == 'payments' else 'incurred_date'
        records.sort(key=lambda r: (r.get(field) or '', r['id']), reverse=True)
        who = 'From' if view == 'payments' else 'Paid to'
        cols = [('Date', ''), (who, '')] + ([('Category', '')] if view == 'expenses' else []) + \
               [('Description', ''), ('Amount', 'num')]
        rows = []
        for r in records:
            totals[r['currency']] += r['amount_minor']
            row = [_cell(reports.date_label(r.get(field)), new=r.get(field) == today),
                   _cell(name(r['client_id']), 'strong', avatar=name(r['client_id']))]
            if view == 'expenses':
                row.append(_cell(r.get('category') or '—', 'tag'))
            row += [_cell(r.get('description') or '—', 'muted'), _num(r['amount_minor'], r['currency'])]
            rows.append(row)
        return cols, rows, {'Received' if view == 'payments' else 'Spent': dict(totals)}
    if view == 'clients':
        billed, owed, spent = defaultdict(int), defaultdict(int), defaultdict(int)
        currency = {}
        for inv in ledger.list_records('invoices'):
            billed[inv['client_id']] += inv['amount_minor']
            owed[inv['client_id']] += inv['balance_minor']
            currency[inv['client_id']] = inv['currency']
        for exp in ledger.list_records('expenses'):
            spent[exp['client_id']] += exp['amount_minor']
            currency.setdefault(exp['client_id'], exp['currency'])
        records.sort(key=lambda r: (-(billed[r['id']] or 0), -(spent[r['id']] or 0), r['name']))
        cols = [('Name', ''), ('Type', ''), ('Billed', 'num'), ('Still owed', 'num'), ('Paid to them', 'num')]
        rows = []
        for r in records:
            cur = currency.get(r['id'])
            role = r.get('role') or ('customer' if billed[r['id']] else 'vendor' if spent[r['id']] else '')
            rows.append([_cell(r['name'], 'strong', avatar=r['name']), _cell(role.capitalize() or '—', 'tag'),
                         _num(billed[r['id']], cur) if billed[r['id']] else _cell('—', 'num muted'),
                         _num(owed[r['id']], cur) if owed[r['id']] else _cell('—', 'num muted'),
                         _num(spent[r['id']], cur) if spent[r['id']] else _cell('—', 'num muted')])
        return cols, rows, {}
    if view == 'reviews':
        records.sort(key=lambda r: (r.get('status') != 'pending', -r['id']))
        cols = [('Status', ''), ('What needs checking', ''), ('Evidence', ''), ('Decision', '')]
        rows = [[_pill(r.get('status')), _cell(r.get('reason', ''), 'strong'), _cell(r.get('evidence', ''), 'muted'),
                 _cell(r.get('resolution') or '—', 'muted')] for r in records]
        return cols, rows, {}
    # documents
    cols = [('Document', ''), ('Where it came from', '')]
    rows = [[_cell(r.get('title', ''), 'strong'),
             _cell('Email' if r.get('source') == 'email' else (r.get('evidence') or 'Added by your agent'), 'muted')]
            for r in records[::-1]]
    return cols, rows, {}


def render_page(ledger, view: str = '', *, demo: bool = False, embed: bool = False, env=None,
                status_filter: str = '') -> str:
    """Render one dashboard view. All ledger text is autoescaped by Jinja."""
    if view and view not in VIEWS:
        raise KeyError(view)
    if status_filter and status_filter not in FILTERS.get(view, {}):
        raise KeyError(status_filter)
    summary = ledger.summary()
    context = dict(summary=summary, demo=demo or summary.get('is_demo', False), views=VIEWS, nav=NAV,
                   embed=embed, view=view, title=VIEWS.get(view, 'Overview'),
                   today=date.today().isoformat(), filters=FILTERS.get(view, {}), status_filter=status_filter)
    if view in ('', 'reports'):
        data = reports.build(ledger)
        context['r'] = data
        primary = data['primary']
        if primary and data['has_data']:
            labels = [reports.month_label(m) for m in data['months']]
            cur = primary['currency']
            context['trend_svg'] = charts.trend(primary['rows'], cur, labels)
            context['cum_svg'] = charts.cumulative(primary['rows'], cur, labels)
            context['category_svg'] = charts.bars(primary['categories'][:7], cur, uid='cat')
            context['clients_svg'] = charts.bars(primary['top_clients'], cur, color=charts.REVENUE, uid='top')
            aging = [(k, v) for k, v in primary['aging'].items() if v]
            context['aging_svg'] = charts.bars(aging, cur, color=charts.PROFIT, uid='aging')
    else:
        columns, rows, totals = table(ledger, view, status_filter)
        context.update(columns=columns, rows=rows, totals=totals)
    return (env or templates()).get_template('dashboard.html').render(**context).strip()


def embed_css() -> str:
    """The dashboard stylesheet scoped for a shadow root, plus embed layout rules."""
    css = (ROOT / 'static' / 'style.css').read_text(encoding='utf-8')
    css = css.replace(':root{', ':host{', 1).replace('body{', '.ls-app{', 1)
    return css + EMBED_CSS
