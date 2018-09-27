"""
Action handler

Action is a conteiner for transactions that need to be executed for that action to complete
"""
import logging

from typing import Dict
from database import db_session
from exceptions import DependencyException
from models import Transaction
from logger import SQLAlchemyHandler
from utils.exchange import ExchangeHelper
from utils.transaction import TransactionHandler


logger = logging.getLogger(__name__)
logger.addHandler(SQLAlchemyHandler())
logger.setLevel(logging.INFO)


class ActionHandler(object):

    def __init__(self, action_id: int, buy_or_sell: str, pair: str, amount: float,
                 exchange: ExchangeHelper, deposit_asset='') -> None:
        self.buy_or_sell = buy_or_sell
        self.action_id = action_id
        self.amount = amount
        self.pair = pair
        self.exchange = exchange
        self.transaction = TransactionHandler
        self.deposit_asset = deposit_asset
        self.use_deposit = bool(deposit_asset)

    def perform(self) -> Dict:
        logger.info(
            f'{self.action_id}:{self.pair} - Action Triggered - '
            f'buy_or_sell:{self.buy_or_sell} '
            f'amount:{self.amount} '
            f'exchange:{self.exchange.name} '
            f'deposit:{self.deposit_asset} ',
        )

        self.__getattribute__(f'_perform_{self.buy_or_sell}')()
        summary = self._summary()
        log_summary = ' '.join([f'{key}:{value}' for key,value in summary.items()])
        logger.info(f'{self.action_id}:{self.pair} - Summary - {log_summary}')
        return summary

    def _perform_buy(self) -> None:
        """Perform buy action"""
        if self.use_deposit:
            logger.info(f'{self.action_id}:{self.pair} - deposit from {self.deposit_asset}')
            if self.exchange.client.markets[self.pair]['quote'] in self.exchange.FIAT_SYMBOLS:
                raise DependencyException(
                    f'Can not use {self.deposit_asset} deposit for {self.pair} pair')

            quote, asset = self.exchange.client.markets[self.pair]['quote'], self.deposit_asset
            symbol = f'{quote}/{asset}'
            last_price = self.exchange.get_last_price(self.pair)

            deposit_amount = self.exchange.symbol_amount_prec(symbol, self.amount * last_price)
            deposit_filled = self._transaction(pair=symbol, amount=deposit_amount)
            if not deposit_filled:
                logger.error(f'{self.action_id}:{self.pair} - failed to take deposit from {asset}')
                return None

            last_price = self.exchange.get_last_price(self.pair)
            self.amount = self.exchange.symbol_amount_prec(self.pair, (deposit_filled / last_price))

        self._transaction(pair=self.pair, amount=self.amount)

    def _perform_sell(self) -> None:
        """Perform sell action"""
        sell_filled = self._transaction(pair=self.pair, amount=self.amount)
        if sell_filled and self.use_deposit:
            if self.exchange.client.markets[self.pair]['quote'] in self.exchange.FIAT_SYMBOLS:
                raise DependencyException(
                    f'Can not use {self.deposit_asset} deposit for {self.pair} pair')
            quote, asset = self.exchange.client.markets[self.pair]['quote'], self.deposit_asset
            symbol = f'{quote}/{asset}'
            last_price = self.exchange.get_last_price(self.pair)
            deposit_amount = self.exchange.symbol_amount_prec(symbol, sell_filled * last_price)
            logger.info(
                f'{self.action_id}:{self.pair} - deposit to {self.deposit_asset}')
            self._transaction(pair=symbol, amount=deposit_amount)

    def _transaction(self, pair: str, amount: float) -> float:
        """Execute transaction"""
        logger.info(
            f'{self.action_id}:{self.pair} - {self.buy_or_sell} - pair:{pair} amount:{amount}')
        filled_total = 0

        for i in range(1, 4):
            last_price = self.exchange.get_last_price(pair)

            if self.buy_or_sell == 'buy':
                quote = self.exchange.client.markets[pair]['quote']
                quantity_requested = amount * last_price
                quantity_available = self.exchange.get_balance(quote)
            else:
                base = self.exchange.client.markets[pair]['base']
                quantity_requested = amount
                quantity_available = self.exchange.get_balance(base)

            #: Make sure requested amount is available
            if quantity_requested > quantity_available:
                amount = quantity_available / last_price if self.buy_or_sell == 'buy' else \
                    quantity_available
                logger.info(
                    f'{self.action_id}:{pair} - amount reduced due to available balance: {amount}')

            rate = self.exchange.symbol_price_prec(pair=pair, price=self.exchange.get_rate_limit(
                pair=pair, buy_or_sell=self.buy_or_sell, amount=amount))
            amount = self.exchange.symbol_amount_prec(pair=pair, amount=amount)

            try:
                min_amount = self.exchange.client.markets[pair]['limits']['amount']['min']
            except KeyError:
                min_amount = 0

            if min_amount and amount < min_amount:
                logger.warning(
                    f'{self.action_id}:{pair} - requested amount is lower then min value: '
                    f'{amount} < {min_amount}')
                return filled_total

            transaction = Transaction(
                action_id=self.action_id,
                buy_or_sell=self.buy_or_sell,
                pair=pair,
                amount=amount,
                rate=rate,
                exchange=self.exchange.name)
            db_session.add(transaction)
            db_session.commit()

            status, filled = TransactionHandler(
                transaction=transaction, exchange=self.exchange).perform()
            filled_total += filled

            if status == 'closed':
                logger.info(
                    f'{self.action_id}:{pair} - filled fully {filled_total}/{filled_total}.')
                return filled
            else:
                if filled:
                    amount = amount - filled
                    logger.info(
                        f'{self.action_id}:{pair} - filled partially {filled_total}/{self.amount} '
                        f'remaining:{amount}')
                else:
                    logger.info(f'{self.action_id}:{pair} - not filled')

        logger.warning(f'{self.action_id}:{pair} - filled retry exceeded')
        return filled_total

    def _summary(self) -> Dict:
        transactions = Transaction.query.filter_by(action_id=self.action_id, pair=self.pair)
        filled = sum([t.filled for t in transactions])
        try:
            price = sum([t.rate * t.filled for t in transactions]) / filled
        except ZeroDivisionError:
            price = 0

        balance = self.exchange.get_balance(self.exchange.client.markets[self.pair]['base'])
        if balance > self.amount:
            balance = self.amount

        return {
            'exchange': self.exchange.name,
            'pair': self.pair,
            'buy_or_sell': self.buy_or_sell,
            'amount': self.amount,
            'filled': filled,
            'balance': balance,
            'avg_price': price,
            'transactions': transactions.count(),
            'deposit': self.deposit_asset or 'N/A'
        }
