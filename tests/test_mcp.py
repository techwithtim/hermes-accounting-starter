import asyncio
import json
import os
import sys
from pathlib import Path


def test_stdio_main_uses_external_data_dir_and_never_seeds(tmp_path):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    async def exercise():
        data = tmp_path / 'external'
        env = dict(os.environ, ACCOUNTING_DATA_DIR=str(data))
        params = StdioServerParameters(command=sys.executable, args=['-m', 'accounting_starter.mcp_server'], env=env)
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool('accounting_summary', {})
                assert not result.isError
                assert '"is_demo": false' in result.content[0].text
        assert (data / 'ledger.sqlite3').is_file()
        assert Ledger(data / 'ledger.sqlite3').summary()['counts']['invoices'] == 0
    asyncio.run(exercise())


def test_mcp_accepts_dates_and_rejects_coerced_amounts(tmp_path):
    async def exercise():
        ledger = Ledger(tmp_path / 'db').initialize()
        c = ledger.create_client('Fictional')['id']
        server = create_server(ledger)
        await server.call_tool('accounting_create_invoice', {'client_id': c, 'amount_minor': 100, 'currency': 'USD', 'invoice_number': 'DEMO-1', 'issued_date': '2025-01-01', 'due_date': '2025-02-01'})
        assert ledger.list_records('invoices')[0]['invoice_number'] == 'DEMO-1'
        await server.call_tool('accounting_create_expense', {'client_id': c, 'amount_minor': 100, 'currency': 'USD', 'incurred_date': '2025-01-01', 'category': 'Supplies'})
        assert ledger.list_records('expenses')[0]['category'] == 'Supplies'
        await server.call_tool('accounting_record_payment', {'client_id': c, 'amount_minor': 100, 'currency': 'USD', 'received_date': '2025-01-01'})
        assert ledger.list_records('payments')[0]['received_date'] == '2025-01-01'
        import pytest
        for amount in (True, 1.5, '100'):
            with pytest.raises(Exception):
                await server.call_tool('accounting_record_payment', {'client_id': c, 'amount_minor': amount, 'currency': 'USD'})
    asyncio.run(exercise())
from accounting_starter.ledger import Ledger
from accounting_starter.mcp_server import create_server


def test_typed_mcp_tools_execute_real_ledger(tmp_path):
    async def exercise():
        ledger = Ledger(tmp_path / 'db').initialize()
        server = create_server(ledger)
        tools = {tool.name: tool for tool in await server.list_tools()}
        assert set(tools) == {'accounting_summary', 'accounting_list_records', 'accounting_create_client',
            'accounting_create_invoice', 'accounting_create_expense', 'accounting_record_payment',
            'accounting_allocate_payment', 'accounting_queue_review', 'accounting_resolve_review', 'accounting_add_document'}
        assert tools['accounting_create_invoice'].inputSchema['properties']['amount_minor']['type'] == 'integer'
        await server.call_tool('accounting_create_client', {'name': 'Fictional MCP client'})
        client = ledger.list_records('clients')[0]['id']
        for tool in ('accounting_create_invoice', 'accounting_create_expense', 'accounting_record_payment'):
            await server.call_tool(tool, {'client_id': client, 'amount_minor': 100, 'currency': 'USD'})
        invoice = ledger.list_records('invoices')[0]['id']
        payment = ledger.list_records('payments')[0]['id']
        await server.call_tool('accounting_allocate_payment', {'payment_id': payment, 'invoice_id': invoice, 'amount_minor': 50})
        await server.call_tool('accounting_queue_review', {'reason': 'Missing currency', 'source_id': 'email:fictional', 'evidence': 'Fictional email'})
        review = ledger.list_records('reviews')[0]['id']
        await server.call_tool('accounting_resolve_review', {'review_id': review, 'resolution': 'Rejected by user'})
        await server.call_tool('accounting_add_document', {'title': 'Fictional document'})
        result = await server.call_tool('accounting_summary', {})
        assert 'USD' in str(result)
        assert ledger.summary()['by_currency']['USD']['allocated_minor'] == 50
        result = await server.call_tool('accounting_list_records', {'kind': 'clients'})
        assert 'Fictional MCP client' in str(result)
    asyncio.run(exercise())
