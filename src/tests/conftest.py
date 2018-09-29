import logging
import sys
import arrow
import pytest

from unittest.mock import patch

from models import Exchange
from utils.exchange import ExchangeHelper
from db import Base, engine
from .. import create_app


logger = logging.getLogger()
logger.level = logging.INFO
stream_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stream_handler)


@pytest.fixture
def app():
    app = create_app({
        'TESTING': True,
    })
    yield app
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def runner(app):
    return app.test_cli_runner()


def tickers(pair):
    val = {
        'TRX/BTC': {'symbol': 'TRX/BTC', 'timestamp': 1537562054479, 'datetime': '2018-09-21T20:34:14.479Z', 'high': 3.9e-06, 'low': 3.13e-06, 'bid': 3.81e-06, 'bidVolume': 385809.0, 'ask': 3.82e-06, 'askVolume': 678218.0, 'vwap': 3.46e-06, 'open': 3.16e-06, 'close': 3.82e-06, 'last': 3.82e-06, 'previousClose': 3.17e-06, 'change': 6.6e-07, 'percentage': 20.886, 'average': None, 'baseVolume': 1708915433.0, 'quoteVolume': 5909.78848032, 'info': {'symbol': 'TRXBTC', 'priceChange': '0.00000066', 'priceChangePercent': '20.886', 'weightedAvgPrice': '0.00000346', 'prevClosePrice': '0.00000317', 'lastPrice': '0.00000382', 'lastQty': '344.00000000', 'bidPrice': '0.00000381', 'bidQty': '385809.00000000', 'askPrice': '0.00000382', 'askQty': '678218.00000000', 'openPrice': '0.00000316', 'highPrice': '0.00000390', 'lowPrice': '0.00000313', 'volume': '1708915433.00000000', 'quoteVolume': '5909.78848032', 'openTime': 1537475654479, 'closeTime': 1537562054479, 'firstId': 33768592, 'lastId': 33853473, 'count': 84882}},
        'BTC/USDT': {'symbol': 'BTC/USDT', 'timestamp': 1537562198664, 'datetime': '2018-09-21T20:36:38.664Z', 'high': 6784.86, 'low': 6325.0, 'bid': 6762.53, 'bidVolume': 0.3, 'ask': 6764.49, 'askVolume': 0.802495, 'vwap': 6635.14130788, 'open': 6381.67, 'close': 6758.77, 'last': 6758.77, 'previousClose': 6384.97, 'change': 377.1, 'percentage': 5.909, 'average': None, 'baseVolume': 54590.306811, 'quoteVolume': 362214399.7315992, 'info': {'symbol': 'BTCUSDT', 'priceChange': '377.10000000', 'priceChangePercent': '5.909', 'weightedAvgPrice': '6635.14130788', 'prevClosePrice': '6384.97000000', 'lastPrice': '6758.77000000', 'lastQty': '0.18699000', 'bidPrice': '6762.53000000', 'bidQty': '0.30000000', 'askPrice': '6764.49000000', 'askQty': '0.80249500', 'openPrice': '6381.67000000', 'highPrice': '6784.86000000', 'lowPrice': '6325.00000000', 'volume': '54590.30681100', 'quoteVolume': '362214399.73159921', 'openTime': 1537475798664, 'closeTime': 1537562198664, 'firstId': 71049339, 'lastId': 71356706, 'count': 307368}}
    }
    return val[pair]


def markets():
    return {
        'TRX/BTC': {'fee_loaded': False, 'percentage': True, 'tierBased': False, 'taker': 0.001, 'maker': 0.001, 'precision': {'base': 8, 'quote': 8, 'amount': 0, 'price': 8}, 'limits': {'amount': {'min': 1.0, 'max': 90000000.0}, 'price': {'min': 3.1e-07, 'max': 3.04e-05}, 'cost': {'min': 0.001, 'max': None}}, 'id': 'TRXBTC', 'symbol': 'TRX/BTC', 'base': 'TRX', 'quote': 'BTC', 'baseId': 'TRX', 'quoteId': 'BTC'},
        'BTC/USDT': {'fee_loaded': False, 'percentage': True, 'tierBased': False, 'taker': 0.001, 'maker': 0.001, 'precision': {'base': 8, 'quote': 8, 'amount': 6, 'price': 2}, 'limits': {'amount': {'min': 1e-06, 'max': 10000000.0}, 'price': {'min': 630.02, 'max': 63001.85}, 'cost': {'min': 10.0, 'max': None}}, 'id': 'BTCUSDT', 'symbol': 'BTC/USDT', 'base': 'BTC', 'quote': 'USDT', 'baseId': 'BTC', 'quoteId': 'USDT'}
    }


def balances():
    return {
        'TRX': {'free': 500.258, 'used': 0.0, 'total': 500.258},
        'BTC': {'free': 1.20000000, 'used': 0.0, 'total': 1.20000000},
        'USDT': {'free': 1000.23253732, 'used': 100.0, 'total': 900.23253732}
    }


@pytest.fixture
def exchange(mocker, app):
    mocker.patch('utils.exchange.ccxt')
    exchange = ExchangeHelper(exchange=Exchange.query.get(1))
    exchange.client.name = 'binance'
    exchange.client.markets = markets()
    exchange.client.fetch_ticker.side_effect = tickers
    exchange.client.fetch_balance.return_value = balances()
    return exchange


@pytest.fixture(scope='function')
def limit_buy_order():
    return {
        'id': 'mocked_limit_buy',
        'type': 'limit',
        'side': 'buy',
        'pair': 'mocked',
        'datetime': arrow.utcnow().isoformat(),
        'price': 0.00001099,
        'amount': 90.99181073,
        'filled': 90.99181073,
        'remaining': 0.0,
        'status': 'closed'
    }


@pytest.fixture
def limit_buy_order_partial():
    return {
        'id': 'mocked_limit_buy_old_partial',
        'type': 'limit',
        'side': 'buy',
        'pair': 'ETH/BTC',
        'datetime': arrow.utcnow().shift(minutes=-1).isoformat(),
        'price': 0.00001099,
        'amount': 90.99181073,
        'remaining': 67.99181073,
        'filled': 23.00000000,
        'status': 'open'
    }


@pytest.fixture(scope='function')
def limit_buy_order_cancel():
    return {
        'id': 'mocked_limit_buy',
        'type': 'limit',
        'side': 'buy',
        'pair': 'mocked',
        'datetime': arrow.utcnow().isoformat(),
        'price': 0.00001099,
        'amount': 90.99181073,
        'filled': 23.00000000,
        'remaining': 67.99181073,
        'status': 'canceled'
    }


@pytest.fixture
def limit_sell_order():
    return {
        'id': 'mocked_limit_sell',
        'type': 'limit',
        'side': 'sell',
        'pair': 'mocked',
        'datetime': arrow.utcnow().isoformat(),
        'price': 0.00001173,
        'amount': 90.99181073,
        'filled': 90.99181073,
        'remaining': 0.0,
        'status': 'closed'
    }


@pytest.fixture
def limit_sell_order_partial():
    return {
        'id': 'mocked_limit_sell',
        'type': 'limit',
        'side': 'sell',
        'pair': 'mocked',
        'datetime': arrow.utcnow().shift(minutes=-1).isoformat(),
        'price': 0.00001173,
        'amount': 90.99181073,
        'remaining': 67.99181073,
        'filled': 23.00000000,
        'status': 'open'
    }
