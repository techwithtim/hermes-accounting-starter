import pytest
from accounting_starter import web

@pytest.mark.parametrize('minor,currency,expected', [(125000,'USD','USD 1,250.00'), (1200,'JPY','JPY 1,200'), (1234,'KWD','KWD 1.234')])
def test_currency_display_respects_minor_units(minor, currency, expected):
    assert hasattr(web, 'format_money'), 'currency display formatter missing'
    assert web.format_money(minor, currency) == expected
