"""Small local ledger. Amounts are integer minor units, never converted."""
from contextlib import contextmanager
from pathlib import Path
from datetime import date
import json
import os
import sqlite3


class Ledger:
    KINDS = ('clients', 'invoices', 'expenses', 'payments', 'reviews', 'documents')

    def __init__(self, path):
        self.path = Path(path)

    @contextmanager
    def _db(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        try:
            with db:
                yield db
        finally:
            db.close()

    def initialize(self):
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        # Create privately before SQLite opens the file (no world-readable window).
        fd = os.open(self.path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            os.fchmod(fd, 0o600)
        finally:
            os.close(fd)
        with self._db() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS records (
                    id INTEGER PRIMARY KEY, kind TEXT NOT NULL,
                    data TEXT NOT NULL, source_id TEXT UNIQUE
                );
                CREATE TABLE IF NOT EXISTS audit (
                    id INTEGER PRIMARY KEY, action TEXT NOT NULL, kind TEXT NOT NULL,
                    record_id INTEGER NOT NULL, data TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
                );
                CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT);
            ''')
        return self

    @staticmethod
    def _text(value, field):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f'{field} must be nonempty text')
        return value.strip()

    def _insert(self, db, kind, data):
        source_id = data.get('source_id')
        if source_id is not None:
            self._text(source_id, 'source_id')
            old = db.execute('SELECT * FROM records WHERE source_id=?', (source_id,)).fetchone()
            if old:
                existing = json.loads(old['data'])
                comparable = dict(existing)
                if kind == 'reviews':
                    comparable.update(status='pending', resolution='')
                if old['kind'] != kind or comparable != data:
                    raise ValueError('source_id already used with different content')
                return dict(existing, id=old['id'])
        cursor = db.execute('INSERT INTO records(kind,data,source_id) VALUES(?,?,?)',
                            (kind, json.dumps(data, sort_keys=True), source_id))
        result = dict(data, id=cursor.lastrowid)
        self._audit(db, 'create', kind, result)
        return result

    def _audit(self, db, action, kind, record):
        db.execute('INSERT INTO audit(action,kind,record_id,data) VALUES(?,?,?,?)',
                   (action, kind, record['id'], json.dumps(record, sort_keys=True)))

    def create_client(self, name, *, source_id=None, source='manual', evidence=''):
        data = dict(name=self._text(name, 'name'), source_id=source_id, source=source, evidence=evidence)
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE')
            return self._insert(db, 'clients', data)

    @staticmethod
    def _amount(amount):
        if type(amount) is not int or not 0 < amount < 2**63:
            raise ValueError('amount_minor must be a positive 64-bit integer')
        return amount

    def _get(self, db, kind, record_id):
        if type(record_id) is not int:
            raise ValueError('record id must be an integer')
        row = db.execute('SELECT * FROM records WHERE id=? AND kind=?', (record_id, kind)).fetchone()
        if not row:
            raise ValueError(f'{kind} record not found')
        return dict(json.loads(row['data']), id=row['id'])

    def _money(self, kind, client_id, amount_minor, currency, description, source_id, source, evidence, **extra):
        amount_minor = self._amount(amount_minor)
        currency = self._text(currency, 'currency').upper()
        if len(currency) != 3 or not currency.isascii() or not currency.isalpha():
            raise ValueError('currency must be a three-letter code')
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE')
            self._get(db, 'clients', client_id)
            return self._insert(db, kind, dict(client_id=client_id, amount_minor=amount_minor,
                currency=currency, description=description, source_id=source_id, source=source, evidence=evidence, **extra))

    @staticmethod
    def _date(value):
        if value is not None:
            if not isinstance(value, str) or date.fromisoformat(value).isoformat() != value:
                raise ValueError('Dates must use YYYY-MM-DD')
        return value

    def create_invoice(self, client_id, amount_minor, currency, *, description='', source_id=None, source='manual', evidence='', invoice_number=None, issued_date=None, due_date=None):
        self._date(issued_date)
        self._date(due_date)
        if issued_date and due_date and due_date < issued_date:
            raise ValueError('due_date precedes issued_date')
        if invoice_number is not None:
            invoice_number = self._text(invoice_number, 'invoice_number')
        return self._money('invoices', client_id, amount_minor, currency, description, source_id, source, evidence,
            invoice_number=invoice_number, issued_date=issued_date, due_date=due_date)

    def create_expense(self, client_id, amount_minor, currency, *, description='', source_id=None, source='manual', evidence='', incurred_date=None, category=''):
        self._date(incurred_date)
        return self._money('expenses', client_id, amount_minor, currency, description, source_id, source, evidence,
                           incurred_date=incurred_date, category=category)

    def record_payment(self, client_id, amount_minor, currency, *, description='', source_id=None, source='manual', evidence='', received_date=None):
        self._date(received_date)
        return self._money('payments', client_id, amount_minor, currency, description, source_id, source, evidence,
                           received_date=received_date)

    def allocate_payment(self, payment_id, invoice_id, amount_minor, *, source_id=None, source='manual', evidence=''):
        self._amount(amount_minor)
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE')
            payment = self._get(db, 'payments', payment_id)
            invoice = self._get(db, 'invoices', invoice_id)
            if payment['currency'] != invoice['currency']:
                raise ValueError('Allocation currency mismatch')
            if payment['client_id'] != invoice['client_id']:
                raise ValueError('Allocation client mismatch')
            data = dict(payment_id=payment_id, invoice_id=invoice_id, amount_minor=amount_minor,
                        currency=payment['currency'], source_id=source_id, source=source, evidence=evidence)
            if source_id is not None and db.execute('SELECT 1 FROM records WHERE source_id=?', (source_id,)).fetchone():
                return self._insert(db, 'allocations', data)
            allocations = [json.loads(r[0]) for r in db.execute("SELECT data FROM records WHERE kind='allocations'")]
            for key, record in [('payment_id', payment), ('invoice_id', invoice)]:
                used = sum(a['amount_minor'] for a in allocations if a[key] == record['id'])
                if used + amount_minor > record['amount_minor']:
                    raise ValueError('Allocation exceeds remaining balance')
            return self._insert(db, 'allocations', data)

    def queue_review(self, reason, *, evidence, source_id, source='email'):
        data = dict(reason=self._text(reason, 'reason'), evidence=self._text(evidence, 'evidence'),
                    source_id=self._text(source_id, 'source_id'), source=source, status='pending', resolution='')
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE')
            return self._insert(db, 'reviews', data)

    def resolve_review(self, review_id, resolution):
        resolution = self._text(resolution, 'resolution')
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE')
            review = self._get(db, 'reviews', review_id)
            if review['status'] != 'pending':
                raise ValueError('Review already resolved')
            review.update(status='resolved', resolution=resolution)
            data = {k: v for k, v in review.items() if k != 'id'}
            db.execute('UPDATE records SET data=? WHERE id=?', (json.dumps(data, sort_keys=True), review_id))
            self._audit(db, 'resolve', 'reviews', review)
            return review

    def add_document(self, title, url='', *, source_id=None, source='manual', evidence=''):
        # Metadata only: URLs are not fetched and local paths are not opened.
        data = dict(title=self._text(title, 'title'), url=url, source_id=source_id, source=source, evidence=evidence)
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE')
            return self._insert(db, 'documents', data)

    def list_records(self, kind):
        if kind == 'audit':
            with self._db() as db:
                return [dict(r) for r in db.execute('SELECT * FROM audit ORDER BY id')]
        if kind not in (*self.KINDS, 'allocations'):
            raise ValueError('Unknown record kind')
        with self._db() as db:
            records = [dict(json.loads(r['data']), id=r['id']) for r in db.execute(
                'SELECT * FROM records WHERE kind=? ORDER BY id', (kind,))]
            if kind == 'invoices':
                allocations = [json.loads(r[0]) for r in db.execute("SELECT data FROM records WHERE kind='allocations'")]
                for record in records:
                    paid = sum(a['amount_minor'] for a in allocations if a['invoice_id'] == record['id'])
                    balance = record['amount_minor'] - paid
                    overdue = bool(balance and record.get('due_date') and record['due_date'] < date.today().isoformat())
                    record.update(paid_minor=paid, balance_minor=balance, status=(
                        'paid' if not balance else 'overdue' if overdue else 'partial' if paid else 'unpaid'))
            return records

    def seed_demo(self):
        """Explicit fictional fixture; refuses a populated non-demo database."""
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute("SELECT 1 FROM metadata WHERE key='is_demo'").fetchone():
                return
            if db.execute('SELECT 1 FROM records LIMIT 1').fetchone():
                raise ValueError('Demo seed requires an empty database')
            def add(kind, key, **data):
                return self._insert(db, kind, dict(data, source_id='demo:' + key,
                    source='demo', evidence='DEMO — entirely fictional sample data'))
            client = add('clients', 'client', name='DEMO — Fictional Aurora Studio')['id']
            invoice = add('invoices', 'invoice-usd', client_id=client, amount_minor=125000,
                          currency='USD', description='DEMO fictional design service', invoice_number='DEMO-001',
                          issued_date='2025-01-01', due_date='2025-02-01')['id']
            add('invoices', 'invoice-eur', client_id=client, amount_minor=40000,
                currency='EUR', description='DEMO fictional consulting', invoice_number='DEMO-002',
                issued_date='2025-01-01', due_date='2025-02-01')
            add('expenses', 'expense', client_id=client, amount_minor=7500,
                currency='USD', description='DEMO fictional supplies', incurred_date='2025-01-10', category='Supplies')
            payment = add('payments', 'payment', client_id=client, amount_minor=50000,
                          currency='USD', description='DEMO fictional partial payment', received_date='2025-01-15')['id']
            add('allocations', 'allocation', payment_id=payment, invoice_id=invoice,
                amount_minor=50000, currency='USD')
            add('reviews', 'review', reason='DEMO email has no currency', status='pending', resolution='')
            add('documents', 'document', title='DEMO fictional agreement', url='https://example.invalid/demo')
            db.execute("INSERT INTO metadata(key,value) VALUES('is_demo','true')")

    def summary(self):
        # A single read transaction gives dashboard totals a consistent snapshot.
        records = {k: [] for k in (*self.KINDS, 'allocations')}
        with self._db() as db:
            db.execute('BEGIN')
            for row in db.execute('SELECT * FROM records ORDER BY id'):
                records[row['kind']].append(dict(json.loads(row['data']), id=row['id']))
            demo = db.execute("SELECT value FROM metadata WHERE key='is_demo'").fetchone()
        totals = {}
        fields = {'invoices': 'invoiced_minor', 'expenses': 'expenses_minor', 'payments': 'payments_minor'}
        for kind, field in fields.items():
            for record in records[kind]:
                bucket = totals.setdefault(record['currency'], dict(invoiced_minor=0, expenses_minor=0,
                    payments_minor=0, allocated_minor=0, outstanding_minor=0, unallocated_minor=0))
                bucket[field] += record['amount_minor']
        for allocation in records['allocations']:
            totals[allocation['currency']]['allocated_minor'] += allocation['amount_minor']
        for bucket in totals.values():
            bucket['outstanding_minor'] = bucket['invoiced_minor'] - bucket['allocated_minor']
            bucket['unallocated_minor'] = bucket['payments_minor'] - bucket['allocated_minor']
        return {'counts': {k: len(records[k]) for k in self.KINDS},
                'by_currency': totals, 'pending_reviews': sum(r['status'] == 'pending' for r in records['reviews']), 'is_demo': bool(demo)}
