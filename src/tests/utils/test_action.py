from unittest.mock import MagicMock, call

from src import Transaction
from utils.action import ActionHandler


def test_perform_buy(exchange):
    _transaction_mock = MagicMock()
    ActionHandler._transaction = _transaction_mock
    ActionHandler(
        action_id=1, buy_or_sell='buy', pair='TRX/BTC', amount=90.99181073,
        exchange=exchange).perform()
    _transaction_mock.assert_called_once_with(amount=90.99181073, pair='TRX/BTC')


def test_perform_buy_with_deposit(exchange):
    _transaction_mock = MagicMock(side_effect=[0.000347, 90.99181073])
    ActionHandler._transaction = _transaction_mock
    ActionHandler(
        action_id=1, buy_or_sell='buy', pair='TRX/BTC', amount=90.99181073,
        exchange=exchange, deposit_asset='USDT').perform()
    _transaction_mock.assert_has_calls([
        call(amount=0.000347, pair='BTC/USDT'),
        call(amount=90.83769633507853, pair='TRX/BTC')]
    )


def test_perform_sell(exchange):
    _transaction_mock = MagicMock(side_effect=[90.99181073])
    ActionHandler._transaction = _transaction_mock
    ActionHandler(
        action_id=1, buy_or_sell='sell', pair='TRX/BTC', amount=90.99181073,
        exchange=exchange).perform()
    _transaction_mock.assert_called_once_with(amount=90.99181073, pair='TRX/BTC')
    
    
def test_perform_sell_with_deposit(exchange):
    _transaction_mock = MagicMock(side_effect=[90.99181073, 0.000347])
    ActionHandler._transaction = _transaction_mock
    ActionHandler(
        action_id=1, buy_or_sell='sell', pair='TRX/BTC', amount=90.99181073,
        exchange=exchange, deposit_asset='USDT').perform()
    _transaction_mock.assert_has_calls([
        call(amount=90.99181073, pair='TRX/BTC'),
        call(amount=0.000347, pair='BTC/USDT')]
    )


def test_transaction_buy_filled_fully(mocker, exchange):
    transaction_handler = mocker.patch('utils.action.TransactionHandler')
    transaction_handler().perform.side_effect = [('closed', 90.99181073)]

    ActionHandler(
        action_id=1, buy_or_sell='buy', pair='TRX/BTC', amount=90.99181073,
        exchange=exchange)._transaction(pair='TRX/BTC', amount=90.99181073)

    transaction = Transaction.query.all()
    assert len(transaction) == 1

    transaction[0].action_id = 1
    transaction[0].pair = 'TRX/BTC'
    transaction[0].buy_or_sell = 'buy'
    transaction[0].amount = 90.99181073
    transaction[0].rate = 3.82e-06
    transaction[0].exchange = 'binance'


def test_transaction_sell_filled_fully(mocker, exchange):
    transaction_handler = mocker.patch('utils.action.TransactionHandler')
    transaction_handler().perform.side_effect = [('closed', 90.99181073)]

    ActionHandler(
        action_id=1, buy_or_sell='sell', pair='TRX/BTC', amount=90.99181073,
        exchange=exchange)._transaction(pair='TRX/BTC', amount=90.99181073)

    transaction = Transaction.query.all()
    assert len(transaction) == 1

    assert transaction[0].action_id == 1
    assert transaction[0].pair == 'TRX/BTC'
    assert transaction[0].buy_or_sell == 'sell'
    assert transaction[0].amount == 90.99181073
    assert transaction[0].rate == 3.81e-06
    assert transaction[0].exchange == 'binance'


def test_transaction_filled_partially(mocker, exchange):

    transaction_handler = mocker.patch('utils.action.TransactionHandler')
    transaction_handler().perform.side_effect = [('open', 50.99181073), ('open', 30.00000000), ('closed', 10.00000000)]

    ActionHandler(
        action_id=1, buy_or_sell='buy', pair='TRX/BTC', amount=90.99181073,
        exchange=exchange)._transaction(pair='TRX/BTC', amount=90.99181073)

    transaction = Transaction.query.all()
    assert len(transaction) == 3

    assert transaction[0].amount == 90.99181073
    assert transaction[0].rate == 3.82e-06
    assert transaction[1].amount == 40.00000000
    assert transaction[1].rate == 3.82e-06
    assert transaction[2].amount == 10.00000000
    assert transaction[2].rate == 3.82e-06


def test_transaction_aborted_if_amount_below_min_allowed(exchange):

    ActionHandler(
        action_id=1, buy_or_sell='buy', pair='TRX/BTC', amount=0.99181073,
        exchange=exchange)._transaction(pair='TRX/BTC', amount=0.99181073)
    transaction = Transaction.query.all()
    assert len(transaction) == 0


def test_transaction_buy_above_available_balance(mocker, exchange):

    transaction_handler = mocker.patch('utils.action.TransactionHandler')
    transaction_handler().perform.side_effect = [('closed', 314136.12565445027)]

    ActionHandler(
        action_id=1, buy_or_sell='buy', pair='TRX/BTC', amount=1000000.99181073,
        exchange=exchange)._transaction(pair='TRX/BTC', amount=1000000.99181073)

    transaction = Transaction.query.all()
    assert len(transaction) == 1
    assert transaction[0].amount == 314136.12565445027


def test_transaction_sell_above_available_balance(mocker, exchange):
    transaction_handler = mocker.patch('utils.action.TransactionHandler')
    transaction_handler().perform.side_effect = [('closed', 314136.12565445027)]

    ActionHandler(
        action_id=1, buy_or_sell='sell', pair='TRX/BTC', amount=1000.99181073,
        exchange=exchange)._transaction(pair='TRX/BTC', amount=1000.99181073)

    transaction = Transaction.query.all()
    assert len(transaction) == 1
    assert transaction[0].amount == 500.258


def test_transaction_not_filled(mocker, exchange):
    transaction_handler = mocker.patch('utils.action.TransactionHandler')
    transaction_handler().perform.side_effect = [('open', 0.00000000), ('open', 0.00000000), ('open', 5.00000000), ('open', 2.00000000), ('open', 2.00000000)]

    ActionHandler(
        action_id=1, buy_or_sell='sell', pair='TRX/BTC', amount=100.99181073,
        exchange=exchange)._transaction(pair='TRX/BTC', amount=100.99181073)

    transaction = Transaction.query.all()
    assert len(transaction) == 3

