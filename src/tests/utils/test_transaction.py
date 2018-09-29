import pytest
from unittest.mock import MagicMock

from db import db_session
from models import Transaction
from utils.transaction import TransactionHandler


@pytest.fixture
def buy_transaction():
    transaction = Transaction(
        action_id=1,
        buy_or_sell='buy',
        pair='TRX/BTC',
        amount=90.99181073,
        rate=0.00000100,
        exchange='binance')
    db_session.add(transaction)
    db_session.commit()
    return transaction


@pytest.fixture
def sell_transaction():
    transaction = Transaction(
        action_id=2,
        buy_or_sell='sell',
        pair='TRX/BTC',
        amount=90.99181073,
        rate=0.00000200,
        exchange='binance')
    db_session.add(transaction)
    db_session.commit()
    return transaction


def test_buy_transaction_execute_buy_action(exchange, buy_transaction, limit_buy_order):
    buy_mock = MagicMock()
    exchange.buy = buy_mock
    exchange.get_order = MagicMock(return_value=limit_buy_order)
    TransactionHandler(transaction=buy_transaction, exchange=exchange).perform()
    exchange.buy.assert_called_with('TRX/BTC', 0.00000100, 90.99181073)


def test_sell_transaction_execute_sell_action(exchange, sell_transaction, limit_sell_order):
    sell_mock = MagicMock()
    exchange.sell = sell_mock
    exchange.get_order = MagicMock(return_value=limit_sell_order)
    TransactionHandler(transaction=sell_transaction, exchange=exchange).perform()
    exchange.sell.assert_called_with('TRX/BTC', 0.00000200, 90.99181073)


def test_transaction_is_checked_untill_closed(exchange, buy_transaction, limit_buy_order_partial, limit_buy_order):
    exchange.buy = MagicMock(return_value={'id': 1})
    get_order_mock = MagicMock(side_effect=[limit_buy_order_partial, limit_buy_order])
    exchange.get_order = get_order_mock
    TransactionHandler(transaction=buy_transaction, exchange=exchange).perform()

    transaction = Transaction.query.get(1)
    assert get_order_mock.call_count == 2
    assert transaction.status == 'closed'
    assert transaction.rate == 0.00001099
    assert transaction.filled == transaction.amount


def test_transaction_is_closed_if_timeout(exchange, buy_transaction, limit_buy_order_partial, limit_buy_order_cancel):
    exchange.buy = MagicMock(return_value={'id': 1})
    get_order_mock = MagicMock(side_effect=[limit_buy_order_partial, limit_buy_order_partial, limit_buy_order_partial, limit_buy_order_partial, limit_buy_order_cancel])
    cancel_order_mock = MagicMock(side_effect=[limit_buy_order_partial])
    exchange.get_order = get_order_mock
    exchange.cancel_order = cancel_order_mock
    TransactionHandler(transaction=buy_transaction, exchange=exchange).perform()

    transaction = Transaction.query.get(1)
    assert get_order_mock.call_count == 5
    assert cancel_order_mock.call_count == 1
    assert transaction.status == 'canceled'
