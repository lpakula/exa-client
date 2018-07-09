#!/usr/bin/python
# -*- coding: utf-8 -*-
import pytest
from __init__ import create_app

buy_action = [
    {u'actions': [
        {u'action': u'order_market_buy', u'amount': u'10.00000000', u'symbol': {u'base_asset': u'EXA', u'symbol': u'EXA/BTC', u'quote_asset_precision': 8, u'step_size': u'1E-8', u'quote_asset': u'BTC', u'base_asset_precision': 8}, u'action_id': 1},
        {u'action': u'sync_amount', u'amount': 10.0, u'symbol': {u'symbol': u'EXA/BTC', u'base_asset': u'EXA', u'quote_asset': u'BTC'}, u'action_id': 2}
    ],
     u'exchange': u'binance'
    }
]

sell_action = [
    {u'actions': [
        {u'action': u'order_market_sell', u'amount': u'10.00000000', u'symbol': {u'base_asset': u'EXA', u'symbol': u'EXA/BTC', u'quote_asset_precision': 8, u'step_size': u'1E-8', u'quote_asset': u'BTC', u'base_asset_precision': 8}, u'action_id': 3}
    ],
     u'exchange': u'binance'}
]


def side_effect_price(value):
    if value == 'EXA/BTC':
        return {'last': 10}
    elif value == 'BTC/USDT':
        return {'last': 3000}


@pytest.fixture
def app():
    app = create_app({
        'TESTING': True,
    })

    yield app

@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def runner(app):
    return app.test_cli_runner()
