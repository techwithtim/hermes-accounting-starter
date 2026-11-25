"""Figures for the overview and reports pages. Each currency is reported on its own; nothing is converted."""
from collections import defaultdict
from datetime import date, timedelta


def _month(value):
    return value[:7] if isinstance(value, str) and len(value) >= 7 else None


def _months_back(end, count):
    year, month = end
    out = []
    for _ in range(count):
        out.append(f'{year:04d}-{month:02d}')
        month -= 1
        if month == 0:
            year, month = year - 1, 12
    return out[::-1]


def _pct(now, before):
    if not before:
        return None
    return round((now - before) / before * 100)


def build(ledger, today=None):
    """Everything the overview and reports pages show, from one consistent read."""
    today = today or date.today()
    clients = {c['id']: c for c in ledger.list_records('clients')}
    invoices = ledger.list_records('invoices')
    payments = ledger.list_records('payments')
    expenses = ledger.list_records('expenses')
    reviews = ledger.list_records('reviews')

    invoiced = defaultdict(int)
    for inv in invoices:
        invoiced[inv['currency']] += inv['amount_minor']
    for exp in expenses:
        invoiced.setdefault(exp['currency'], 0)
    currencies = sorted(invoiced, key=lambda c: -invoiced[c])
    primary = currencies[0] if currencies else None

    latest = max([_month(r.get(f)) for r, f in
                  [(i, 'issued_date') for i in invoices] + [(e, 'incurred_date') for e in expenses]
                  + [(p, 'received_date') for p in payments] if _month(r.get(f))] or [today.isoformat()[:7]])
    end = max(latest, today.isoformat()[:7])
    months = _months_back((int(end[:4]), int(end[5:7])), 12)

    def per_currency(cur):
        revenue = {m: 0 for m in months}
        collected = {m: 0 for m in months}
        spent = {m: 0 for m in months}
        categories = defaultdict(int)
        by_client = defaultdict(int)
        for inv in invoices:
            m = _month(inv.get('issued_date'))
            if inv['currency'] == cur and m in revenue:
                revenue[m] += inv['amount_minor']
                by_client[inv['client_id']] += inv['amount_minor']
        for pay in payments:
            m = _month(pay.get('received_date'))
            if pay['currency'] == cur and m in collected:
                collected[m] += pay['amount_minor']
        for exp in expenses:
            m = _month(exp.get('incurred_date'))
            if exp['currency'] == cur and m in spent:
                spent[m] += exp['amount_minor']
                categories[exp.get('category') or 'Uncategorised'] += exp['amount_minor']
        rows, running = [], 0
        for m in months:
            net = revenue[m] - spent[m]
            running += net
            rows.append(dict(month=m, revenue=revenue[m], collected=collected[m], expenses=spent[m],
                             net=net, cumulative=running,
                             margin=round(net / revenue[m] * 100) if revenue[m] else None))
        total_rev = sum(revenue.values())
        total_exp = sum(spent.values())
        last3 = sum(r['revenue'] for r in rows[-3:])
        prev3 = sum(r['revenue'] for r in rows[-6:-3])
        first_half = sum(r['net'] for r in rows[:6])
        second_half = sum(r['net'] for r in rows[6:])
        open_invoices = []
        for inv in invoices:
            if inv['currency'] != cur or not inv['balance_minor']:
                continue
            due = inv.get('due_date')
            late = (today - date.fromisoformat(due)).days if due else 0
            open_invoices.append(dict(inv, client=clients.get(inv['client_id'], {}).get('name', '—'),
                                      days_late=max(late, 0)))
        open_invoices.sort(key=lambda i: (-i['days_late'], i.get('due_date') or ''))
        aging = {'Not due yet': 0, '1–30 days late': 0, '31–60 days late': 0, '60+ days late': 0}
        for inv in open_invoices:
            d = inv['days_late']
            bucket = 'Not due yet' if d <= 0 else '1–30 days late' if d <= 30 else '31–60 days late' if d <= 60 else '60+ days late'
            aging[bucket] += inv['balance_minor']
        top = sorted(((clients.get(cid, {}).get('name', '—'), amount) for cid, amount in by_client.items()),
                     key=lambda x: -x[1])
        return dict(
            currency=cur, rows=rows, revenue=total_rev, expenses=total_exp, net=total_rev - total_exp,
            margin=round((total_rev - total_exp) / total_rev * 100) if total_rev else None,
            collected=sum(collected.values()),
            growth=_pct(last3, prev3), profit_growth=_pct(second_half, first_half),
            avg_profit=(total_rev - total_exp) // 12,
            outstanding=sum(i['balance_minor'] for i in open_invoices),
            overdue=sum(i['balance_minor'] for i in open_invoices if i['days_late'] > 0),
            overdue_count=sum(1 for i in open_invoices if i['days_late'] > 0),
            open_invoices=open_invoices, aging=aging,
            categories=sorted(categories.items(), key=lambda x: -x[1]),
            top_clients=top[:6],
            best_month=max(rows, key=lambda r: r['net']) if total_rev else None,
        )

    activity = []
    for inv in invoices:
        if inv.get('issued_date'):
            activity.append(dict(date=inv['issued_date'], kind='Invoice sent', amount=inv['amount_minor'],
                                 currency=inv['currency'], sign='+', tone='invoice',
                                 who=clients.get(inv['client_id'], {}).get('name', '—'), what=inv.get('description', '')))
    for pay in payments:
        if pay.get('received_date'):
            activity.append(dict(date=pay['received_date'], kind='Payment received', amount=pay['amount_minor'],
                                 currency=pay['currency'], sign='+', tone='payment',
                                 who=clients.get(pay['client_id'], {}).get('name', '—'), what=pay.get('description', '')))
    for exp in expenses:
        if exp.get('incurred_date'):
            activity.append(dict(date=exp['incurred_date'], kind='Expense', amount=exp['amount_minor'],
                                 currency=exp['currency'], sign='−', tone='expense',
                                 who=clients.get(exp['client_id'], {}).get('name', '—'), what=exp.get('description', '')))
    activity.sort(key=lambda a: a['date'], reverse=True)

    return dict(
        months=months, primary=per_currency(primary) if primary else None,
        others=[per_currency(c) for c in currencies[1:]],
        activity=activity[:8], pending_reviews=sum(r.get('status') == 'pending' for r in reviews),
        has_data=bool(invoices or expenses or payments),
    )


def month_label(month, short=True):
    d = date(int(month[:4]), int(month[5:7]), 1)
    return d.strftime('%b' if short else '%B %Y')


def date_label(value):
    try:
        d = date.fromisoformat(value)
    except (TypeError, ValueError):
        return value or '—'
    return f'{d.day} {d.strftime("%b %Y")}'


def days_between(a, b):
    return (date.fromisoformat(b) - date.fromisoformat(a)).days


__all__ = ['build', 'month_label', 'date_label', 'timedelta']
