# #!/usr/bin/python
# # -*- coding: utf-8 -*-
# from decimal import Decimal as D
# from unittest.mock import patch, call, MagicMock
# 
# from ccxt import BaseError
# from ccxt.base.errors import InsufficientFunds
# 
# from __init__ import VERSION
# from .conftest import buy_action, sell_action, side_effect_price
# from database import db_session
# from models import Settings, Exchange
# from utils.exchange import ExchangeHelper
# 
# 
# def test_buy_action_with_available_balance(client, app):
#     settings = Settings.query.get(1)
#     settings.exa_token = 'token'
#     exchange = Exchange.query.get(1)
#     exchange.valid = True
#     exchange.enabled = True
#     exchange.api_key = 'apikey'
#     exchange.api_secret = 'apiapisecret'
#     db_session.commit()
#     with patch('utils.exchange.ExAServerHelper') as exa_server_helper:
#         with patch('utils.exchange.ccxt') as ccxt_helper:
# 
#             ccxt_helper.binance().fetchTicker = MagicMock(side_effect=side_effect_price)
#             ccxt_helper.binance().fetchBalance.return_value = {'BTC': {'free': 200}, 'EXA': {'free': 10}}
#             ccxt_helper.binance().createMarketBuyOrder.return_value = 'response'
# 
#             ExchangeHelper(exchange='binance', version=VERSION).run_actions(buy_action[0]['actions'])
#             ccxt_helper.binance().createMarketBuyOrder.assert_called_once_with(amount=D('10.00000000'), symbol='EXA/BTC')
# 
#             exa_server_helper().confirm_action.assert_called_once_with(action_id=1, response='response', status=True)
#             exa_server_helper().sync_amount.assert_called_once_with(action_id=2, balance=D(10))
# 
# 
# def test_sync_amount_is_not_greater_then_trading_amount_regardless_real_balance(client, app):
#     settings = Settings.query.get(1)
#     settings.exa_token = 'token'
#     exchange = Exchange.query.get(1)
#     exchange.valid = True
#     exchange.enabled = True
#     exchange.api_key = 'apikey'
#     exchange.api_secret = 'apiapisecret'
#     db_session.commit()
#     with patch('utils.exchange.ExAServerHelper') as exa_server_helper:
#         with patch('utils.exchange.ccxt') as ccxt_helper:
# 
#             ccxt_helper.binance().fetchTicker = MagicMock(side_effect=side_effect_price)
#             ccxt_helper.binance().fetchBalance.return_value = {'BTC': {'free': 200}, 'EXA': {'free': 100}}
#             ccxt_helper.binance().createMarketBuyOrder.return_value = 'response'
# 
#             ExchangeHelper(exchange='binance', version=VERSION).run_actions(buy_action[0]['actions'])
#             exa_server_helper().sync_amount.assert_called_once_with(action_id=2, balance=D(10))
# 
# 
# def test_buy_reduce_amount_if_insufficend_balance_exception(client, app):
#     settings = Settings.query.get(1)
#     settings.exa_token = 'token'
#     exchange = Exchange.query.get(1)
#     exchange.valid = True
#     exchange.enabled = True
#     exchange.api_key = 'apikey'
#     exchange.api_secret = 'apiapisecret'
#     db_session.commit()
#     with patch('utils.exchange.ExAServerHelper') as exa_server_helper:
#         with patch('utils.exchange.ccxt') as ccxt_helper:
# 
#             ccxt_helper.binance().createMarketBuyOrder = MagicMock(side_effect=[InsufficientFunds, InsufficientFunds, InsufficientFunds, 'response'])
#             ccxt_helper.binance().fetchTicker = MagicMock(side_effect=side_effect_price)
#             ccxt_helper.binance().fetchBalance.return_value = {'BTC': {'free': 200}, 'EXA': {'free': 10}}
# 
#             ExchangeHelper(exchange='binance', version=VERSION).run_actions(buy_action[0]['actions'])
#             ccxt_helper.binance().createMarketBuyOrder.assert_has_calls([
#                 call(amount=D('10.00000000'), symbol='EXA/BTC'),
#                 call(amount=D('9.00000000'), symbol='EXA/BTC'),
#                 call(amount=D('8.00000000'), symbol='EXA/BTC'),
#                 call(amount=D('7.00000000'), symbol='EXA/BTC')]
#             )
# 
# 
# def test_buy_raise_exception_if_insufficend_balance_exception_exceed(client, app):
#     settings = Settings.query.get(1)
#     settings.exa_token = 'token'
#     exchange = Exchange.query.get(1)
#     exchange.valid = True
#     exchange.enabled = True
#     exchange.api_key = 'apikey'
#     exchange.api_secret = 'apiapisecret'
#     db_session.commit()
#     with patch('utils.exchange.ExAServerHelper') as exa_server_helper:
#         with patch('utils.exchange.ccxt') as ccxt_helper:
# 
#             ccxt_helper.binance().createMarketBuyOrder = MagicMock(side_effect=[InsufficientFunds, InsufficientFunds, InsufficientFunds, InsufficientFunds])
#             ccxt_helper.binance().fetchTicker = MagicMock(side_effect=side_effect_price)
#             ccxt_helper.binance().fetchBalance.return_value = {'BTC': {'free': 200}, 'EXA': {'free': 10}}
# 
#             try:
#                 ExchangeHelper(exchange='binance', version=VERSION).run_actions(buy_action[0]['actions'])
#             except BaseError:
#                 pass
# 
#             exa_server_helper().confirm_action.assert_called_once_with(action_id=1, response='', status=False)
#             exa_server_helper().sync_amount.assert_not_called()
# 
# 
# def test_buy_reduce_amount_if_not_enough_balance(client, app):
#     settings = Settings.query.get(1)
#     settings.exa_token = 'token'
#     exchange = Exchange.query.get(1)
#     exchange.valid = True
#     exchange.enabled = True
#     exchange.api_key = 'apikey'
#     exchange.api_secret = 'apiapisecret'
#     db_session.commit()
#     with patch('utils.exchange.ExAServerHelper') as exa_server_helper:
#         with patch('utils.exchange.ccxt') as ccxt_helper:
# 
#             ccxt_helper.binance().fetchTicker = MagicMock(side_effect=side_effect_price)
#             ccxt_helper.binance().fetchBalance.return_value = {'BTC': {'free': 50}, 'EXA': {'free': 10}}
#             ccxt_helper.binance().createMarketBuyOrder.return_value = 'response'
# 
#             ExchangeHelper(exchange='binance', version=VERSION).run_actions(buy_action[0]['actions'])
#             ccxt_helper.binance().createMarketBuyOrder.assert_called_once_with(amount=D('5.00000000'), symbol='EXA/BTC')
# 
# 
# def test_sell_action_with_available_balance(client, app):
#     settings = Settings.query.get(1)
#     settings.exa_token = 'token'
#     exchange = Exchange.query.get(1)
#     exchange.valid = True
#     exchange.enabled = True
#     exchange.api_key = 'apikey'
#     exchange.api_secret = 'apiapisecret'
#     db_session.commit()
#     with patch('utils.exchange.ExAServerHelper') as exa_server_helper:
#         with patch('utils.exchange.ccxt') as ccxt_helper:
# 
#             ccxt_helper.binance().fetchTicker = MagicMock(side_effect=side_effect_price)
#             ccxt_helper.binance().fetchBalance.return_value = {'BTC': {'free': 200}, 'EXA': {'free': 10}}
#             ccxt_helper.binance().createMarketSellOrder.return_value = 'response'
# 
#             ExchangeHelper(exchange='binance', version=VERSION).run_actions(sell_action[0]['actions'])
# 
#             ccxt_helper.binance().createMarketSellOrder.assert_called_once_with(amount=D('10.00000000'), symbol='EXA/BTC')
#             exa_server_helper().confirm_action.assert_called_once_with(action_id=3, response='response', status=True)
# 
# 
# def test_sell_action_with_unavailable_balance(client, app):
#     settings = Settings.query.get(1)
#     settings.exa_token = 'token'
#     exchange = Exchange.query.get(1)
#     exchange.valid = True
#     exchange.enabled = True
#     exchange.api_key = 'apikey'
#     exchange.api_secret = 'apiapisecret'
#     db_session.commit()
#     with patch('utils.exchange.ExAServerHelper') as exa_server_helper:
#         with patch('utils.exchange.ccxt') as ccxt_helper:
# 
#             ccxt_helper.binance().fetchTicker = MagicMock(side_effect=side_effect_price)
#             ccxt_helper.binance().fetchBalance.return_value = {'BTC': {'free': 200}, 'EXA': {'free': 5}}
#             ccxt_helper.binance().createMarketSellOrder.return_value = 'response'
# 
#             ExchangeHelper(exchange='binance', version=VERSION).run_actions(sell_action[0]['actions'])
#             ccxt_helper.binance().createMarketSellOrder.assert_called_once_with(amount=D('5.00000000'), symbol='EXA/BTC')
