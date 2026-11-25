"""A year of fictional books for a small design and development studio.

Every name, amount and document here is invented. Dates are generated relative
to the month the demo is created, so the charts always end at the current
month. The records carry source='demo' and the database is flagged as a demo.
"""
from datetime import date, timedelta
import random

CUSTOMERS = [
    # name, currency
    ('Halcyon Health', 'USD'),
    ('Juniper & Vale', 'USD'),
    ('Brightline Logistics', 'USD'),
    ('Orbitfield Labs', 'USD'),
    ('Copperleaf Coffee Co.', 'USD'),
    ('Meridian Outdoor', 'USD'),
    ('Kestrel Analytics', 'USD'),
    ('Lumen Atelier', 'USD'),
]

VENDORS = [
    ('Fernlight Coworking', 'Rent'),
    ('Tidewater Cloud', 'Hosting'),
    ('Quillstone Software', 'Software'),
    ('Ana Ribeiro', 'Contractors'),
    ('Devon Okafor', 'Contractors'),
    ('Signal & Sail Ads', 'Marketing'),
    ('Harborline Insurance', 'Insurance'),
    ('Skyharbor Air', 'Travel'),
    ('Brightwork Hardware', 'Equipment'),
]


def _month_start(anchor, offset):
    """First day of the month `offset` months after `anchor` (negative goes back)."""
    index = anchor.year * 12 + anchor.month - 1 + offset
    return date(index // 12, index % 12 + 1, 1)


def build(today=None):
    """Return the demo as plain lists of dicts, oldest first. Deterministic for a given month."""
    today = today or date.today()
    anchor = date(today.year, today.month, 1)
    rng = random.Random(anchor.year * 100 + anchor.month)
    months = [_month_start(anchor, offset) for offset in range(-11, 1)]

    clients = [dict(key=f'client-{i}', name=name, role='customer', currency=cur)
               for i, (name, cur) in enumerate(CUSTOMERS)]
    clients += [dict(key=f'vendor-{i}', name=name, role='vendor', category=cat)
                for i, (name, cat) in enumerate(VENDORS)]
    by_name = {c['name']: c['key'] for c in clients}

    invoices, payments, expenses = [], [], []
    number = 1041

    def day(month, d):
        last = (_month_start(month, 1) - timedelta(days=1)).day
        return month.replace(day=min(d, last))

    def invoice(client, month, issue_day, amount, description, *, terms=30, pay_after=None, partial=None):
        nonlocal number
        number += 1
        issued = day(month, issue_day)
        if issued > today:
            return
        due = issued + timedelta(days=terms)
        currency = next(c['currency'] for c in clients if c['name'] == client)
        key = f'invoice-{number}'
        invoices.append(dict(key=key, client=client, amount_minor=amount, currency=currency,
                             description=description, invoice_number=f'INV-{number}',
                             issued_date=issued.isoformat(), due_date=due.isoformat(),
                             evidence=f'Invoice INV-{number} sent to {client}'))
        if pay_after is None:
            return
        received = issued + timedelta(days=pay_after)
        if received > today:
            return
        paid = partial or amount
        payments.append(dict(key=f'payment-{number}', client=client, amount_minor=paid, currency=currency,
                             description=f'Payment for INV-{number}', received_date=received.isoformat(),
                             invoice=key, evidence=f'Bank transfer notice referencing INV-{number}'))

    def expense(vendor, month, spend_day, amount, description, currency='USD'):
        spent = day(month, spend_day)
        if spent > today:
            return
        category = next(c['category'] for c in clients if c['name'] == vendor)
        expenses.append(dict(key=f'expense-{len(expenses) + 1}', client=vendor, amount_minor=amount,
                             currency=currency, description=description, category=category,
                             incurred_date=spent.isoformat(), evidence=f'Receipt from {vendor}'))

    for i, month in enumerate(months):
        label = month.strftime('%B')
        recent = i >= 10  # the last two months still have open invoices
        # Retainers
        invoice('Halcyon Health', month, 1, 650000, f'{label} product design retainer',
                pay_after=None if i == 11 else 12 + rng.randint(0, 8))
        juniper = 380000 if i < 6 else 480000
        invoice('Juniper & Vale', month, 1, juniper, f'{label} brand and web retainer',
                pay_after=None if i == 11 else 20 + rng.randint(0, 6))
        invoice('Lumen Atelier', month, 3, 240000, f'{label} site maintenance',
                pay_after=None if i == 11 else 9 + rng.randint(0, 6))
        if i >= 9:
            invoice('Kestrel Analytics', month, 2, 520000, f'{label} analytics product retainer',
                    pay_after=None if i == 11 else 14 + rng.randint(0, 5))
        # Project work
        if i % 2 == 0 or i >= 7:
            amount = rng.choice([420000, 560000, 640000, 780000]) + i * 25000
            invoice('Brightline Logistics', month, 14, amount, 'Fleet dashboard sprint',
                    terms=45, pay_after=None if recent else 30 + rng.randint(0, 20))
        if i >= 4:
            amount = 650000 + (i - 4) * 120000 + rng.randint(0, 4) * 10000
            phase = 'Phase 1 build' if i < 8 else 'Phase 2 platform build'
            # One Orbitfield invoice is the overdue story of the demo.
            late = i == 9
            invoice('Orbitfield Labs', month, 18, amount, phase,
                    pay_after=None if (late or i >= 11) else 21 + rng.randint(0, 9))
        if i in (1, 4, 7, 8, 10):
            amount = rng.choice([120000, 165000, 210000, 245000])
            partial = amount // 2 if i == 10 else None
            invoice('Copperleaf Coffee Co.', month, 22, amount, 'Packaging and menu design',
                    terms=14, pay_after=10 if i == 10 else 9 + rng.randint(0, 5), partial=partial)
        if month.month in (3, 4, 5, 6, 7):
            invoice('Meridian Outdoor', month, 10, rng.choice([300000, 450000, 520000]),
                    'Seasonal campaign site', pay_after=25 + rng.randint(0, 10))
        if i == 6:
            invoice('Meridian Outdoor', month, 26, 380000, 'Trail app prototype',
                    terms=30, pay_after=34)

        # Expenses
        expense('Fernlight Coworking', month, 1, 185000, f'{label} studio desks')
        expense('Tidewater Cloud', month, 3, 42000 + i * 4200, f'{label} hosting')
        expense('Quillstone Software', month, 5, 31000 + (i // 3) * 7000, f'{label} design and dev tools')
        expense('Ana Ribeiro', month, 25, 280000 + i * 26000 + rng.randint(0, 8) * 5000, 'Freelance illustration and UI')
        if i >= 5:
            expense('Devon Okafor', month, 26, 150000 + (i - 5) * 30000, 'Contract front-end development')
        expense('Signal & Sail Ads', month, 12, 60000 + i * 7500 + rng.randint(0, 5) * 4000, 'Paid social and search ads')
        if month.month in (1, 4, 7, 10):
            expense('Harborline Insurance', month, 15, 96000, 'Quarterly liability insurance')
        if i in (2, 6, 9):
            expense('Skyharbor Air', month, 8, rng.choice([42000, 88000, 136000, 178000]), 'Client workshop travel')
        if i in (3, 8):
            expense('Brightwork Hardware', month, 19, 240000 if i == 3 else 162000,
                    'Laptop for new hire' if i == 3 else 'Display and test devices')
        if i % 3 == 0:
            expense('Ana Ribeiro', month, 27, 36000, 'Illustration licence for Lumen Atelier')

    last = months[-1]
    reviews = [
        dict(key='review-1', reason='Payout email lists three transfers but no invoice numbers',
             evidence='Processor payout summary, 4 transfers totalling $9,180', status='pending', resolution=''),
        dict(key='review-2', reason='Receipt amount does not match the card statement line',
             evidence='Tidewater Cloud receipt shows $798; statement shows $812', status='pending', resolution=''),
        dict(key='review-3', reason='Remittance mentions INV-10' + str(number - 3) + ' and a credit note',
             evidence='Orbitfield Labs remittance advice PDF', status='pending', resolution=''),
        dict(key='review-4', reason='Duplicate receipt forwarded twice',
             evidence='Quillstone Software receipt, two copies', status='resolved',
             resolution='Same receipt; kept one expense'),
        dict(key='review-5', reason='Invoice currency unclear',
             evidence='Lumen Atelier invoice PDF without currency symbol', status='resolved',
             resolution='Confirmed USD from the contract'),
    ]
    documents = [
        dict(key='doc-1', title='Halcyon Health master services agreement', url=''),
        dict(key='doc-2', title='Orbitfield Labs statement of work, phase 2', url=''),
        dict(key='doc-3', title='Fernlight Coworking membership terms', url=''),
        dict(key='doc-4', title='Lumen Atelier maintenance contract', url=''),
        dict(key='doc-5', title=f'Brightline Logistics purchase order, {last.strftime("%B %Y")}', url=''),
    ]
    return dict(clients=clients, invoices=invoices, payments=payments, expenses=expenses,
                reviews=reviews, documents=documents, by_name=by_name)
