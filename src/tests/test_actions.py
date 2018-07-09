#!/usr/bin/python
# -*- coding: utf-8 -*-
from unittest.mock import patch, call

from __init__ import VERSION
from .conftest import buy_action
from database import db_session
from models import Settings, Exchange
from utils.server import ExAServerHelper


def test_exa_server_not_called_if_invalid_exchange(client, app):
    exchange = Exchange.query.get(1)
    assert exchange.valid == False
    with patch('__init__.ExAServerHelper') as exa_server:
        assert client.get('/test/run_actions').status_code == 200
        exa_server.assert_not_called()


def test_exa_server_called_if_valid_and_enabled_exchange(client, app):
    exchange = Exchange.query.get(1)
    exchange.valid = True
    exchange.enabled = True
    db_session.commit()

    with patch('__init__.ExAServerHelper') as exa_server:
        assert client.get('/test/run_actions').status_code == 200
        exa_server().get_actions.assert_called_with(exchanges=['binance'])


def test_exa_server_helper_return_actions(client, app):
    settings = Settings.query.get(1)
    settings.exa_token = 'token'
    exchange = Exchange.query.get(1)
    exchange.valid = True
    exchange.enabled = True
    db_session.commit()

    with patch('utils.server.requests', autospec=True) as requests:
        assert client.get('/test/run_actions').status_code == 200
        requests.get.assert_called_with(
            '{}/api/actions/?exchange=binance'.format(ExAServerHelper.SERVER_URL),
            headers={'Authorization': 'Token token'}, timeout=7)


def test_exchange_helper_call_each_trade_action_separately(client, app):
    exchange = Exchange.query.get(1)
    exchange.valid = True
    exchange.enabled = True
    db_session.commit()

    with patch('__init__.ExAServerHelper') as exa_server_helper:
        with patch('__init__.ExchangeHelper') as exchange_helper:
            exa_server_helper().get_actions.return_value = buy_action
            client.get('/test/run_actions')

            assert exchange_helper.call_count == 1
            exchange_helper.assert_called_with(exchange=buy_action[0]['exchange'], version=VERSION)
            exchange_helper().run_actions.assert_called_with(actions=buy_action[0]['actions'])

            exchange_helper.reset_mock()
            exa_server_helper().get_actions.return_value = buy_action + buy_action
            client.get('/test/run_actions')
            assert exchange_helper.call_count == 2
