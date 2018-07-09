#!/usr/bin/python
# -*- coding: utf-8 -*-
import time
import math
from decimal import Decimal as D
from math import floor

import ccxt
from ccxt.base.errors import InsufficientFunds, BaseError, ExchangeError

from utils.server import ExAServerHelper
from exceptions import ExAClientException
from models import Exchange, SystemLog, Transaction, Settings
from database import db_session


class ExchangeHelper(object):
    """
    Exchange helper

    """

    ACTIONS = {
        'order_market_buy': 'order_market_buy',
        'order_market_sell': 'order_market_sell',
        'sync_amount': 'sync_amount'
    }

    def __init__(self, exchange, version):
        """
        :param str version: client version
        """
        self.version = version
        self.exchange = Exchange.query.filter_by(name=exchange)[0]

        self.client = getattr(ccxt, self.exchange.name)(
            {'apiKey': self.exchange.api_key.strip(), 'secret': self.exchange.api_secret.strip()})
        self.settings = Settings.query.get(1)
        self.exa_helper = ExAServerHelper(version=version)

    def check_status(self):
        """
        Check account status

        """
        try:
            self.client.fetchDepositAddress('BTC')
            return True
        except ExchangeError as e:
            self._log(message='Invalid Exchange Account API Keys: {}'.format(e))
            return False

    def check_balance(self, data, balance_requested=None):
        """
        Check if used balance is below balance limit

        """
        balance_requested = 0 if not balance_requested else balance_requested
        transactions = Transaction.query.filter_by(
            action_name=data['action'], pair=data['symbol']['symbol'])
        self.balance_used = 0
        balance_allowed = D(self.settings.allowed_balance)
        for transaction in transactions:
            self.balance_used += transaction.balance_usdt
        if balance_allowed > D(self.balance_used) + D(balance_requested):
            return True
        else:
            return False

    def run_actions(self, actions):
        for action in actions:
            try:
                action_name = self.ACTIONS[action['action']]
            except KeyError:
                e = 'Unknown action: {}'.format(action['action'])
                self.exa_helper.confirm_action(
                    action_id=action['action_id'], status=False, response=e)
                raise ExAClientException(e)

            if self.settings.allowed_pairs:
                if action['symbol']['symbol'] not in self.settings.allowed_pairs:
                    message = '{} pair is not allowed'.format(action['symbol']['symbol'])
                    self.exa_helper.confirm_action(
                        action_id=action['action_id'], status=False, response=message)
                    raise ExAClientException(message)

            if self.settings.allowed_actions:
                allowed_actions = self.settings.allowed_actions + ['sync_amount']
                if action_name not in allowed_actions:
                    message = 'Action not allowed: {}'.format(action_name)
                    self.exa_helper.confirm_action(
                        action_id=action['action_id'], status=False, response=message)
                    raise ExAClientException(message)

            if action_name not in ['sync_amount']:
                balance_requested = self.get_latest_price_usdt(action['symbol']) * D(action['amount'])
            else:
                balance_requested = None

            if self.settings.allowed_balance and action_name == 'order_market_buy':
                if not self.check_balance(action, balance_requested=balance_requested):
                    message = 'Allowed balance exceeded: {} < {}'.format(
                        self.settings.allowed_balance, self.balance_used)
                    self.exa_helper.confirm_action(
                        action_id=action['action_id'], status=False, response=message)
                    raise ExAClientException(message)

            getattr(self, action_name)(data=action)

    def order_market_buy(self, data):
        """
        Perform order market buy

        """
        latest_price = self.get_latest_price(symbol=data['symbol'])
        asset_quantity_requested = D(data['amount']) * latest_price
        asset_quantity_available = self.get_balance(symbol=data['symbol']['quote_asset'])

        valid_quantity = D(data['amount'])

        #: Make sure requested amount is available
        if asset_quantity_requested > asset_quantity_available:
            valid_quantity = self.validate_quantity(
                quantity=asset_quantity_available / latest_price, symbol=data['symbol'])
            self._log('Amount reduced due to available balance: {}'.format(valid_quantity))

        params = {'symbol': data['symbol']['symbol'], 'amount': valid_quantity}

        # For very dynamic price fluctuations, reduce amount to fulfill the order if insufficient
        # balance exception is raised
        for i in range(1, 5):
            try:
                output = self._perform_order_market(
                    action_type='buy', action_id=data['action_id'], params=params)
                data['amount'] = params['amount']
                balance_requested = self.get_latest_price_usdt(data['symbol']) * D(params['amount'])
                self._log_transaction(action=data, balance_usdt=balance_requested)
                return output
            except InsufficientFunds as e:
                self._log(str(e))
                if i <= 3:
                    diff = i**2
                    new_quantity = valid_quantity - ((D(diff) / 100) * valid_quantity)
                    valid_quantity = self.validate_quantity(
                        quantity=new_quantity, symbol=data['symbol'])
                    params['amount'] = valid_quantity
                    self._log('Amount reduced due to insufficient balance: {}'.format(new_quantity))
                else:
                    self._log(str(e))
                    self.exa_helper.confirm_action(
                        action_id=data['action_id'], status=False, response=str(e))
                    raise BaseError(e)

    def order_market_sell(self, data):
        """
        Perform order market sell

        """
        quantity_available = self.get_balance(symbol=data['symbol']['base_asset'])
        valid_quantity = D(data['amount'])

        #: Make sure requested amount is available
        if quantity_available < valid_quantity:
            valid_quantity = self.validate_quantity(
                quantity=quantity_available, symbol=data['symbol'])
            self._log('Amount reduced due to available balance: {}'.format(valid_quantity))

        params = {'symbol': data['symbol']['symbol'], 'amount': valid_quantity}

        try:
            self._perform_order_market(
                action_type='sell', action_id=data['action_id'], params=params)
            balance_requested = self.get_latest_price_usdt(data['symbol']) * D(params['amount'])
            data['amount'] = params['amount']
            self._log_transaction(action=data, balance_usdt=balance_requested)
        except BaseError as e:
            self._log(str(e))
            self.exa_helper.confirm_action(
                action_id=data['action_id'], status=False, response=str(e))

    def _perform_order_market(self, action_type, action_id, params):
        """
        Perform order market action

        :param action_type: ``buy`` or ``sell``
        :param action_id: corresponding action id
        :param params: order params

        """
        self._log('Order Market {}: {}'.format(action_type.title(), params))
        if self.settings.test_mode:
            self._log('Test Mode: No transaction performed.')
            self.exa_helper.confirm_action(action_id=action_id, status=True, response='TEST MODE')
            return None
        else:
            response = getattr(self.client, 'createMarket{}Order'.format(action_type.title()))(
                **params)
            self._log(message=str(response))
            self.exa_helper.confirm_action(action_id=action_id, status=True, response=response)
            return response

    def sync_amount(self, data):
        """
        Sync trade amount with exchange balance if balance lower then current amount

        """
        amount = D(data['amount'])
        if self.settings.test_mode:
            balance = amount
        else:
            balance = self.get_balance(symbol=data['symbol']['base_asset'])
            #: never accept balance bigger then current amount
            if balance > amount:
                balance = amount

        self._log('Amount synced with ExA server: {}'.format(balance))

        self.exa_helper.sync_amount(action_id=data['action_id'], balance=balance)

    def get_balance(self, symbol):
        """
        Get balance

        :param str symbol: symbol eg. BTC/USDT

        """
        time.sleep(1)
        balance = self.client.fetchBalance()
        return D(balance[symbol]['free'])

    def get_latest_price(self, symbol):
        """
        Get latest price for symbol

        :param dict symbol: symbol data

        """
        return D(self.client.fetchTicker(symbol['symbol'])['last'])

    def get_latest_price_usdt(self, symbol):
        """
        Latest price in USDT

        :param dict symbol: symbol data

        """
        last_price_quote = self.get_latest_price(symbol)

        if symbol['quote_asset'] == 'USDT':
            usdt_price = last_price_quote
        else:
            symbol_usdt = {'symbol': '{}/USDT'.format(symbol['quote_asset'])}
            latest_price_usdt = self.get_latest_price(symbol_usdt)
            usdt_price = last_price_quote * latest_price_usdt

        return D(str(round(usdt_price, - int(math.floor(math.log10(abs(usdt_price))) - (4 - 1)))))

    def validate_quantity(self, quantity, symbol):
        """
        Validate quantity for trading

        :param quantity:
        :param dict symbol: symbol data

        """
        try:
            decimal_places = len((str(D(symbol['step_size']).normalize())).split('.')[1])
        except IndexError:
            decimal_places = 0

        output = D(floor(quantity * (10 ** decimal_places)) / float(10 ** decimal_places))
        return D("{:0.0{}f}".format(float(output), symbol['quote_asset_precision']))

    def _log(self, message):
        log = SystemLog(message=message)
        db_session.add(log)
        db_session.commit()

    def _log_transaction(self, action, balance_usdt):
        action_log = Transaction(
            pair=action['symbol']['symbol'], action_name=action['action'],
            amount=D(action['amount']), balance_usdt=balance_usdt)
        db_session.add(action_log)
        db_session.commit()

