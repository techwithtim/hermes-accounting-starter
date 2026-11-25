"""Typed, bounded accounting MCP operations; no raw SQL or filesystem tools."""
from typing import Literal
from mcp.server.fastmcp import FastMCP
from pydantic import StrictInt
from .ledger import Ledger

RecordKind = Literal['clients', 'invoices', 'expenses', 'payments', 'reviews', 'documents', 'allocations', 'audit']


def create_server(ledger: Ledger) -> FastMCP:
    server = FastMCP('Hermes Accounting Starter')

    @server.tool()
    def accounting_summary() -> dict:
        """Dashboard totals in separate currencies, with no implied FX conversion."""
        return ledger.summary()

    @server.tool()
    def accounting_list_records(kind: RecordKind) -> list[dict]:
        """List one permitted record type, including audit or review evidence."""
        return ledger.list_records(kind)

    @server.tool()
    def accounting_create_client(name: str, source_id: str | None = None, source: str = 'manual', evidence: str = '') -> dict:
        """Create a client/counterparty from confirmed evidence, or because the owner asked for it in chat."""
        return ledger.create_client(name, source_id=source_id, source=source, evidence=evidence)

    @server.tool()
    def accounting_create_invoice(client_id: StrictInt, amount_minor: StrictInt, currency: str, description: str = '', source_id: str | None = None, source: str = 'manual', evidence: str = '', invoice_number: str | None = None, issued_date: str | None = None, due_date: str | None = None) -> dict:
        """Record a confirmed invoice (from evidence, or because the owner asked for it in chat). Amount must be positive integer minor units, for example 250000 for USD 2,500.00. Dates are YYYY-MM-DD."""
        return ledger.create_invoice(client_id, amount_minor, currency, description=description, source_id=source_id, source=source, evidence=evidence, invoice_number=invoice_number, issued_date=issued_date, due_date=due_date)

    @server.tool()
    def accounting_create_expense(client_id: StrictInt, amount_minor: StrictInt, currency: str, description: str = '', source_id: str | None = None, source: str = 'manual', evidence: str = '', incurred_date: str | None = None, category: str = '') -> dict:
        """Record a confirmed expense, never infer uncertain amounts or currency."""
        return ledger.create_expense(client_id, amount_minor, currency, description=description, source_id=source_id, source=source, evidence=evidence, incurred_date=incurred_date, category=category)

    @server.tool()
    def accounting_record_payment(client_id: StrictInt, amount_minor: StrictInt, currency: str, description: str = '', source_id: str | None = None, source: str = 'manual', evidence: str = '', received_date: str | None = None) -> dict:
        """Record a payment; use allocation separately to settle an invoice."""
        return ledger.record_payment(client_id, amount_minor, currency, description=description, source_id=source_id, source=source, evidence=evidence, received_date=received_date)

    @server.tool()
    def accounting_allocate_payment(payment_id: StrictInt, invoice_id: StrictInt, amount_minor: StrictInt, source_id: str | None = None, source: str = 'manual', evidence: str = '') -> dict:
        """Allocate payment with currency, counterparty and balance safeguards."""
        return ledger.allocate_payment(payment_id, invoice_id, amount_minor, source_id=source_id, source=source, evidence=evidence)

    @server.tool()
    def accounting_queue_review(reason: str, evidence: str, source_id: str, source: str = 'email') -> dict:
        """Capture ambiguous evidence for human review; does not book money."""
        return ledger.queue_review(reason, evidence=evidence, source_id=source_id, source=source)

    @server.tool()
    def accounting_resolve_review(review_id: StrictInt, resolution: str) -> dict:
        """Record an explicit human review decision; does not create financial records."""
        return ledger.resolve_review(review_id, resolution)

    @server.tool()
    def accounting_add_document(title: str, url: str = '', source_id: str | None = None, source: str = 'manual', evidence: str = '') -> dict:
        """Store document metadata only; never fetch URL or open a local path."""
        return ledger.add_document(title, url, source_id=source_id, source=source, evidence=evidence)

    return server


def main():
    """Serve live data over stdio. Demo seeding is intentionally unavailable."""
    import os
    from pathlib import Path
    data_dir = Path(os.environ.get('ACCOUNTING_DATA_DIR', '~/.local/share/hermes-accounting-starter')).expanduser()
    ledger = Ledger(data_dir / 'ledger.sqlite3').initialize()
    create_server(ledger).run(transport='stdio')


if __name__ == '__main__':
    main()
