from unittest.mock import MagicMock, call

from utils.action import ActionHandler


def test_perform_buy(exchange):
    _transaction_mock = MagicMock()
    ActionHandler._transaction = _transaction_mock
    ActionHandler(
        action_id=1, buy_or_sell='buy', pair='TRX/BTC', amount=90.99181073,
        exchange=exchange).perform()
    _transaction_mock.assert_called_once_with(amount=90.99181073, pair='TRX/BTC')


def test_prform_buy_with_deposit(exchange):
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
    # assert False, _transaction_mock.mock_calls


# def test_buy_action(mocker, exchange):
#     transaction_handler = mocker.patch('utils.action.TransactionHandler')
#     transaction_handler().perform.side_effect = [20, 70.99181073]
#
#     # exchange.get_balance = MagicMock(side_effect=balance)
#     exchange.get_rate_limit = MagicMock(side_effect=[0.00000100, 0.00000200])
#     # exchange.get_last_price = MagicMock(side_effect=last_price)
#
#     ActionHandler(
#         action_id=1, buy_or_sell='buy', pair='TRX/BTC', amount=90.99181073,
#         exchange=exchange).perform()
#
#     transactions = Transaction.query.filter_by(action_id=1)
#     assert 2 == transactions.count()
#     assert transactions[0].buy_or_sell == 'buy'
#     assert transactions[0].pair == 'TRX/BTC'
#     assert transactions[0].exchange == 'binance'
#     assert transactions[0].amount == 90.99181073
#     assert transactions[0].rate == 0.00000100
#
#     assert transactions[1].buy_or_sell == 'buy'
#     assert transactions[1].pair == 'TRX/BTC'
#     assert transactions[1].exchange == 'binance'
#     assert transactions[1].amount == 70.99181073
#     assert transactions[1].rate == 0.00000200
#
#
# def test_buy_deposit(exchange):
#
#     action_handler = ActionHandler(
#         action_id=1, buy_or_sell='buy', pair='TRX/BTC', amount=90.99181073,
#         exchange=exchange, deposit_asset='USDT')
#
#     buy_mock = MagicMock(side_effect=[0.000347, 90.99181073])
#     action_handler._buy = buy_mock
#     action_handler.perform()
#     buy_mock.assert_has_calls(
#         calls=[
#             call(amount=0.000347, pair='BTC/USDT'),
#             call(amount=90.83769633507853, pair='TRX/BTC')],
#         any_order=False)
#
# def test_buy_action_no_balance(mocker, exchange):
#     pass
