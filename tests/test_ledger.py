import pytest


def test_client_provenance_dedup_and_audit(tmp_path):
    ledger = Ledger(tmp_path / 'ledger.db').initialize()
    client = ledger.create_client('Fictional Studio', source_id='mail:1', source='manual', evidence='User request')
    assert client['name'] == 'Fictional Studio'
    assert client['source_id'] == 'mail:1'
    assert client['evidence'] == 'User request'
    assert ledger.create_client('Fictional Studio', source_id='mail:1', source='manual', evidence='User request') == client
    with pytest.raises(ValueError, match='source'):
        ledger.create_client('Different', source_id='mail:1')
    assert len(ledger.list_records('clients')) == 1
    assert ledger.list_records('audit')[0]['action'] == 'create'
    with pytest.raises(ValueError):
        ledger.create_client('  ')

from accounting_starter.ledger import Ledger


def test_money_records_and_currency_summary(tmp_path):
    ledger = Ledger(tmp_path / 'db').initialize()
    client = ledger.create_client('DEMO customer')['id']
    ledger.create_invoice(client, 10000, 'usd', description='Fictional service', source_id='invoice:1')
    ledger.create_expense(client, 500, 'USD', description='Fictional fee')
    ledger.record_payment(client, 3000, 'USD', source_id='payment:1')
    ledger.create_invoice(client, 7000, 'AED')
    assert ledger.summary()['by_currency'] == {
        'USD': {'invoiced_minor': 10000, 'expenses_minor': 500, 'payments_minor': 3000, 'allocated_minor': 0, 'outstanding_minor': 10000, 'unallocated_minor': 3000},
        'AED': {'invoiced_minor': 7000, 'expenses_minor': 0, 'payments_minor': 0, 'allocated_minor': 0, 'outstanding_minor': 7000, 'unallocated_minor': 0}}
    for amount in (True, 1.5, '10', 0, -1, 2**63):
        with pytest.raises(ValueError):
            ledger.create_invoice(client, amount, 'USD')
    with pytest.raises(ValueError):
        ledger.record_payment(999, 100, 'USD')
    for currency in ('', 'US', 'US1'):
        with pytest.raises(ValueError):
            ledger.create_expense(client, 100, currency)



def test_allocation_bounds_currency_and_client(tmp_path):
    ledger = Ledger(tmp_path / 'db').initialize()
    client = ledger.create_client('Fictional')['id']
    invoice = ledger.create_invoice(client, 100, 'USD')['id']
    payment = ledger.record_payment(client, 150, 'USD')['id']
    allocation = ledger.allocate_payment(payment, invoice, 60, source_id='allocation:1')
    assert ledger.allocate_payment(payment, invoice, 60, source_id='allocation:1') == allocation
    for amount in (41, -1, True):
        with pytest.raises(ValueError):
            ledger.allocate_payment(payment, invoice, amount)
    other = ledger.create_invoice(client, 200, 'USD')['id']
    with pytest.raises(ValueError):
        ledger.allocate_payment(payment, other, 91)
    foreign = ledger.create_invoice(client, 200, 'EUR')['id']
    with pytest.raises(ValueError, match='currency'):
        ledger.allocate_payment(payment, foreign, 1)
    stranger = ledger.create_client('Another fictional')['id']
    wrong = ledger.create_invoice(stranger, 200, 'USD')['id']
    with pytest.raises(ValueError, match='client'):
        ledger.allocate_payment(payment, wrong, 1)
    ledger.allocate_payment(payment, invoice, 40)
    totals = ledger.summary()['by_currency']['USD']
    assert totals['allocated_minor'] == 100
    assert totals['outstanding_minor'] == 400
    assert totals['unallocated_minor'] == 50
    assert len(ledger.list_records('allocations')) == 2


def test_review_is_not_money_and_resolution_is_audited(tmp_path):
    ledger = Ledger(tmp_path / 'db').initialize()
    review = ledger.queue_review('Unclear currency', evidence='Fictional email says 100', source_id='mail:unclear', source='email')
    assert review['status'] == 'pending'
    assert ledger.summary()['by_currency'] == {}
    assert ledger.summary()['pending_reviews'] == 1
    with pytest.raises(ValueError):
        ledger.resolve_review(review['id'], '')
    resolved = ledger.resolve_review(review['id'], 'Rejected: insufficient evidence')
    assert resolved['status'] == 'resolved'
    assert ledger.summary()['pending_reviews'] == 0
    assert ledger.queue_review('Unclear currency', evidence='Fictional email says 100', source_id='mail:unclear', source='email') == resolved
    assert ledger.list_records('audit')[-1]['action'] == 'resolve'
    with pytest.raises(ValueError):
        ledger.resolve_review(review['id'], 'Overwrite')
    document = ledger.add_document('Fictional contract', 'https://example.invalid/contract', source_id='doc:1')
    assert ledger.list_records('documents') == [document]


def test_demo_is_explicit_deterministic_and_cannot_mix_with_live(tmp_path):
    live = Ledger(tmp_path / 'live.db').initialize()
    demo = Ledger(tmp_path / 'demo.db').initialize()
    demo.seed_demo()
    before = demo.summary()
    demo.seed_demo()
    assert demo.summary() == before
    assert before['is_demo'] is True
    assert before['counts']['invoices'] > 0
    assert before['pending_reviews'] > 0
    invoices = demo.list_records('invoices')
    assert len(invoices) > 50 and len(demo.list_records('expenses')) > 50
    assert invoices[0]['invoice_number'].startswith('INV-')
    assert len({i['issued_date'][:7] for i in invoices}) == 12
    names = [c['name'] for c in demo.list_records('clients')]
    assert not any('demo' in n.lower() for n in names)
    assert {i['status'] for i in invoices} >= {'paid', 'overdue'}
    assert live.summary()['counts']['invoices'] == 0
    second = Ledger(tmp_path / 'second-demo.db').initialize()
    second.seed_demo()
    for kind in demo.KINDS:
        assert second.list_records(kind) == demo.list_records(kind)
        assert all(r['source'] == 'demo' for r in demo.list_records(kind))
    live.create_client('Actual user supplied')
    with pytest.raises(ValueError, match='empty'):
        live.seed_demo()
    assert live.summary()['is_demo'] is False


def test_invoice_dates_number_and_computed_balance(tmp_path):
    ledger = Ledger(tmp_path / 'db').initialize()
    c = ledger.create_client('Fictional')['id']
    inv = ledger.create_invoice(c, 100, 'USD', invoice_number='DEMO-001', issued_date='2020-01-01', due_date='2020-02-01')
    listed = ledger.list_records('invoices')[0]
    assert listed['invoice_number'] == 'DEMO-001'
    assert listed['status'] == 'overdue'
    assert listed['balance_minor'] == 100
    p = ledger.record_payment(c, 100, 'USD')['id']
    ledger.allocate_payment(p, inv['id'], 100)
    assert ledger.list_records('invoices')[0]['status'] == 'paid'
    assert ledger.list_records('invoices')[0]['balance_minor'] == 0
    other = ledger.create_invoice(c, 100, 'USD')['id']
    assert ledger.list_records('invoices')[1]['status'] == 'unpaid'
    p = ledger.record_payment(c, 50, 'USD')['id']
    ledger.allocate_payment(p, other, 50)
    assert ledger.list_records('invoices')[1]['status'] == 'partial'
    for fields in ({'issued_date': 'bad'}, {'due_date': '2025-02-30'}, {'issued_date': '2025-02-01', 'due_date': '2025-01-01'}):
        with pytest.raises(ValueError):
            ledger.create_invoice(c, 100, 'USD', **fields)


def test_expense_payment_dates_and_category(tmp_path):
    ledger = Ledger(tmp_path / 'db').initialize()
    c = ledger.create_client('Fictional')['id']
    expense = ledger.create_expense(c, 100, 'USD', incurred_date='2025-01-01', category='Supplies')
    assert expense['incurred_date'] == '2025-01-01'
    assert expense['category'] == 'Supplies'
    payment = ledger.record_payment(c, 100, 'USD', received_date='2025-02-01')
    assert payment['received_date'] == '2025-02-01'
    with pytest.raises(ValueError):
        ledger.create_expense(c, 100, 'USD', incurred_date='tomorrow')
    with pytest.raises(ValueError):
        ledger.record_payment(c, 100, 'USD', received_date='20250201')


def test_private_database_permissions(tmp_path):
    import stat
    path = tmp_path / 'private' / 'ledger.db'
    Ledger(path).initialize()
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert stat.S_IMODE(path.parent.stat().st_mode) == 0o700


def test_concurrent_allocations_cannot_overpay(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    ledger = Ledger(tmp_path / 'db').initialize()
    client = ledger.create_client('Fictional')['id']
    invoice = ledger.create_invoice(client, 100, 'USD')['id']
    payment = ledger.record_payment(client, 100, 'USD')['id']
    def allocate(_):
        try:
            ledger.allocate_payment(payment, invoice, 60)
            return True
        except ValueError:
            return False
    with ThreadPoolExecutor(max_workers=4) as pool:
        assert sum(pool.map(allocate, range(4))) == 1
    assert ledger.summary()['by_currency']['USD']['allocated_minor'] == 60


def test_new_database_is_empty_and_persistent(tmp_path):
    path = tmp_path / 'live' / 'ledger.sqlite3'
    ledger = Ledger(path)
    ledger.initialize()
    assert ledger.summary() == {'counts': {'clients': 0, 'invoices': 0, 'expenses': 0, 'payments': 0, 'reviews': 0, 'documents': 0}, 'by_currency': {}, 'pending_reviews': 0, 'is_demo': False}
    assert ledger.list_records('invoices') == []
    Ledger(path).initialize()
    with pytest.raises(ValueError):
        ledger.list_records('sqlite_master')
