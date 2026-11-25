"""Server-rendered SVG charts. No scripts: they work under a strict CSP and inside the Hermes tab.

Tooltips use SVG <title>, so hovering a month shows its exact figures.
"""
from decimal import Decimal
import math

from babel.numbers import format_compact_currency, format_currency, get_currency_precision
from markupsafe import Markup, escape

INK = '#17211C'
GRID = '#D5DED8'
REVENUE = '#1F8A65'
EXPENSE = '#8B4A6B'
PROFIT = '#B88A2B'


def _major(amount_minor, currency):
    return Decimal(amount_minor).scaleb(-get_currency_precision(currency))


def money(amount_minor, currency, *, cents=False):
    """$12,480 by default; cents=True keeps the minor units ($12,480.50)."""
    if amount_minor is None or currency is None:
        return '—'
    value = _major(amount_minor, currency)
    if cents:
        return format_currency(value, currency, locale='en_US')
    return format_currency(value, currency, format='¤#,##0', locale='en_US', currency_digits=False)


def compact(amount_minor, currency):
    return format_compact_currency(_major(amount_minor, currency), currency, locale='en_US', fraction_digits=0)


def _nice_ceiling(value):
    if value <= 0:
        return 1, 1
    raw = value / 4
    power = 10 ** math.floor(math.log10(raw))
    for step in (1, 2, 2.5, 5, 10):
        if step * power >= raw:
            break
    step *= power
    return step * math.ceil(value / step), step


def _monotone_path(points):
    """Smooth line through points without overshooting (Fritsch-Carlson monotone cubic)."""
    if len(points) < 2:
        return ''
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    n = len(points)
    d = [(ys[i + 1] - ys[i]) / (xs[i + 1] - xs[i]) for i in range(n - 1)]
    m = [d[0]] + [(d[i - 1] + d[i]) / 2 if d[i - 1] * d[i] > 0 else 0 for i in range(1, n - 1)] + [d[-1]]
    for i in range(n - 1):
        if d[i] == 0:
            m[i] = m[i + 1] = 0
        else:
            a, b = m[i] / d[i], m[i + 1] / d[i]
            s = a * a + b * b
            if s > 9:
                t = 3 / math.sqrt(s)
                m[i], m[i + 1] = t * a * d[i], t * b * d[i]
    path = [f'M{xs[0]:.1f},{ys[0]:.1f}']
    for i in range(n - 1):
        h = (xs[i + 1] - xs[i]) / 3
        path.append(f'C{xs[i] + h:.1f},{ys[i] + m[i] * h:.1f} {xs[i + 1] - h:.1f},{ys[i + 1] - m[i + 1] * h:.1f} '
                    f'{xs[i + 1]:.1f},{ys[i + 1]:.1f}')
    return ' '.join(path)


def trend(rows, currency, labels, *, uid='trend'):
    """Revenue and expenses as lines, profit as bars, one column per month."""
    width, height = 860, 300
    left, right, top, bottom = 64, 16, 18, 34
    plot_w, plot_h = width - left - right, height - top - bottom
    peak = max([r['revenue'] for r in rows] + [r['expenses'] for r in rows] + [1])
    ceiling, step = _nice_ceiling(peak)
    n = len(rows)
    col = plot_w / n

    def x(i):
        return left + col * i + col / 2

    def y(v):
        return top + plot_h - (max(v, 0) / ceiling) * plot_h

    out = [f'<svg class="chart chart-trend" viewBox="0 0 {width} {height}" role="img" '
           f'aria-labelledby="{uid}-t" preserveAspectRatio="xMidYMid meet">',
           f'<title id="{uid}-t">Monthly revenue, expenses and profit in {escape(currency)}</title>',
           f'<defs><linearGradient id="{uid}-fill" x1="0" y1="0" x2="0" y2="1">'
           f'<stop offset="0" stop-color="{REVENUE}" stop-opacity=".22"/>'
           f'<stop offset="1" stop-color="{REVENUE}" stop-opacity="0"/></linearGradient></defs>']
    tick = 0
    while tick <= ceiling + 1e-9:
        ty = y(tick)
        out.append(f'<line x1="{left}" x2="{width - right}" y1="{ty:.1f}" y2="{ty:.1f}" stroke="{GRID}" '
                   f'stroke-width="1"{"" if tick else ""}/>')
        out.append(f'<text x="{left - 10}" y="{ty + 4:.1f}" text-anchor="end" class="axis">'
                   f'{escape(compact(int(tick), currency))}</text>')
        tick += step
    bar_w = min(col * 0.42, 26)
    for i, r in enumerate(rows):
        if r['net'] > 0:
            out.append(f'<rect x="{x(i) - bar_w / 2:.1f}" y="{y(r["net"]):.1f}" width="{bar_w:.1f}" '
                       f'height="{y(0) - y(r["net"]):.1f}" rx="3" fill="{PROFIT}" opacity=".85"/>')
        out.append(f'<text x="{x(i):.1f}" y="{height - 10}" text-anchor="middle" class="axis">'
                   f'{escape(labels[i])}</text>')
    rev = [(x(i), y(r['revenue'])) for i, r in enumerate(rows)]
    exp = [(x(i), y(r['expenses'])) for i, r in enumerate(rows)]
    line = _monotone_path(rev)
    if line:
        out.append(f'<path d="{line} L{rev[-1][0]:.1f},{y(0):.1f} L{rev[0][0]:.1f},{y(0):.1f} Z" '
                   f'fill="url(#{uid}-fill)"/>')
        out.append(f'<path d="{line}" fill="none" stroke="{REVENUE}" stroke-width="3" stroke-linecap="round"/>')
        out.append(f'<path d="{_monotone_path(exp)}" fill="none" stroke="{EXPENSE}" stroke-width="2.5" '
                   f'stroke-linecap="round" stroke-dasharray="1 0"/>')
        px, py = rev[-1]
        out.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="5" fill="#fff" stroke="{REVENUE}" stroke-width="3"/>')
    for i, r in enumerate(rows):
        tip = (f'{labels[i]}: revenue {money(r["revenue"], currency)}, expenses {money(r["expenses"], currency)}, '
               f'profit {money(r["net"], currency) if r["net"] >= 0 else "−" + money(-r["net"], currency)}')
        out.append(f'<rect x="{left + col * i:.1f}" y="{top}" width="{col:.1f}" height="{plot_h}" '
                   f'fill="transparent"><title>{escape(tip)}</title></rect>')
    out.append('</svg>')
    return Markup(''.join(out))


def cumulative(rows, currency, labels, *, uid='cum'):
    """Profit kept so far this year, month by month."""
    width, height = 860, 220
    left, right, top, bottom = 64, 16, 16, 30
    plot_w, plot_h = width - left - right, height - top - bottom
    values = [r['cumulative'] for r in rows]
    low = min(values + [0])
    high = max(values + [1])
    ceiling, step = _nice_ceiling(high - low)
    n = len(rows)

    def x(i):
        return left + plot_w * i / max(n - 1, 1)

    def y(v):
        return top + plot_h - ((v - low) / ceiling) * plot_h

    out = [f'<svg class="chart" viewBox="0 0 {width} {height}" role="img" aria-labelledby="{uid}-t">',
           f'<title id="{uid}-t">Profit kept over the year in {escape(currency)}</title>',
           f'<defs><linearGradient id="{uid}-fill" x1="0" y1="0" x2="0" y2="1">'
           f'<stop offset="0" stop-color="{PROFIT}" stop-opacity=".28"/>'
           f'<stop offset="1" stop-color="{PROFIT}" stop-opacity="0"/></linearGradient></defs>']
    for k in range(0, 5):
        value = low + step * k
        if value > low + ceiling + 1e-9:
            break
        out.append(f'<line x1="{left}" x2="{width - right}" y1="{y(value):.1f}" y2="{y(value):.1f}" stroke="{GRID}"/>')
        out.append(f'<text x="{left - 10}" y="{y(value) + 4:.1f}" text-anchor="end" class="axis">'
                   f'{escape(compact(int(value), currency))}</text>')
    pts = [(x(i), y(v)) for i, v in enumerate(values)]
    line = _monotone_path(pts)
    if line:
        out.append(f'<path d="{line} L{pts[-1][0]:.1f},{y(low):.1f} L{pts[0][0]:.1f},{y(low):.1f} Z" fill="url(#{uid}-fill)"/>')
        out.append(f'<path d="{line}" fill="none" stroke="{PROFIT}" stroke-width="3" stroke-linecap="round"/>')
    for i, (px, py) in enumerate(pts):
        if i in (0, n - 1) or i % 3 == 0:
            out.append(f'<text x="{px:.1f}" y="{height - 8}" text-anchor="middle" class="axis">{escape(labels[i])}</text>')
        out.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="3.5" fill="{PROFIT}">'
                   f'<title>{escape(labels[i])}: {escape(money(values[i], currency))} kept so far</title></circle>')
    out.append('</svg>')
    return Markup(''.join(out))


def bars(items, currency, *, color=EXPENSE, uid='bars'):
    """Ranked list: label and amount as text, a thin SVG bar under each (text stays readable at any width)."""
    if not items:
        return Markup('')
    peak = max(v for _, v in items) or 1
    total = sum(v for _, v in items) or 1
    out = [f'<ul class="hbars" aria-label="{escape(uid)}">']
    for label, value in items:
        w = max(100 * value / peak, 1.5)
        share = round(value / total * 100)
        out.append(f'<li><div class="hb-row"><span class="hb-label">{escape(label)}</span>'
                   f'<span class="hb-value">{escape(money(value, currency))}<small>{share}%</small></span></div>'
                   f'<svg class="hb" viewBox="0 0 100 6" preserveAspectRatio="none" aria-hidden="true">'
                   f'<rect width="100" height="6" rx="1.5" fill="{GRID}" opacity=".6"/>'
                   f'<rect width="{w:.2f}" height="6" rx="1.5" fill="{color}"/></svg></li>')
    out.append('</ul>')
    return Markup(''.join(out))
