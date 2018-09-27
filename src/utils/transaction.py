"""
Helper class to perform buy and sell actions
"""
import time
import logging

from typing import Dict, Tuple

from exceptions import DependencyException, TemporaryError, OperationalException
from models import Transaction, Exchange
from db import db_session
from logger import SQLAlchemyHandler
from .exchange import ExchangeHelper


logger = logging.getLogger(__name__)
logger.addHandler(SQLAlchemyHandler())
logger.setLevel(logging.INFO)


class TransactionHandler(object):
    """Perform Transaction"""

    def __init__(self, transaction: Transaction, exchange: ExchangeHelper) -> None:
        self.action_id = transaction.action_id
        self.transaction = transaction
        self.exchange = exchange
        self.pair = transaction.pair
        self.buy_or_sell = transaction.buy_or_sell
        self.amount = transaction.amount
        self.rate_limit = transaction.rate

    def perform(self) -> Tuple[str, float]:
        """Perform Transaction on exchange"""
        try:
            
            order_id = getattr(self.exchange, self.transaction.buy_or_sell)(
                self.pair, self.rate_limit, self.amount)['id']
        except (DependencyException, TemporaryError, OperationalException) as e:
            logger.error(f'{self.action_id}:{self.pair} - Order Failed - message: {e}')
            return self.transaction.status, self.transaction.filled

        logger.info(
            f'{self.action_id}:{order_id}:{self.pair} - Order Created - '
            f'buy_or_sell:{self.buy_or_sell} amount:{self.amount} rate:{self.rate_limit}')
        for i in range(1, 4):
            time.sleep(i)
            order = self.exchange.get_order(order_id=order_id, pair=self.pair)
            logger.info(
                f"{self.action_id}:{order_id}:{self.pair} - Order Status - "
                f"filled:{order['filled']}/{order['amount']} "
                f"status:{order['status']}"
            )
            self.transaction.filled = order['filled']
            self.transaction.status = order['status']
            self.transaction.rate = order['price']
            db_session.commit()
            if self.transaction.status == 'closed':
                break
        else:
            logger.warning(f'{self.action_id}:{order_id}:{self.pair} '
                           f'- cancel order because of timeout.')
            self.exchange.cancel_order(order_id=order_id, pair=self.pair)
            for i in range(1, 4):
                time.sleep(i)
                order = self.exchange.get_order(order_id=order_id, pair=self.pair)
                if order['status'] == 'canceled':
                    self.transaction.status = order['status']
                    db_session.commit()
                    logger.info(
                        f'{self.action_id}"{order_id}:{self.pair} - '
                        f'order has been cancelled successfully.')
                    break
            else:
                logger.error(
                    f'{self.action_id}"{order_id}:{self.pair} - '
                    f'order has not been cancelled - status:{order}')
        return self.transaction.status, self.transaction.filled
