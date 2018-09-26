"""General helper functions"""
import math
from decimal import Decimal as D

from database import db_session
from models import Exchange, Transaction, Settings


def get_settings() -> Settings:
    """
    Returns settings
    """
    return Settings.query.get(1)


def significant_figures(price: D, figures=4) -> D:
    if price:
        return D(str(round(price, - int(math.floor(math.log10(abs(price))) - (figures - 1)))))
    else:
        return D('0')


def balance_exceeded(pair: str, balance_requested: D) -> bool:
    """
    Check if used balance is below balance limit
    """
    transactions = Transaction.query.filter_by(action_name='order_limit_buy', pair=pair)
    balance_allowed = D(get_settings().allowed_balance)
    balance_used = sum([t.balance_usdt for t in transactions])
    return not balance_allowed > D(balance_used) + D(balance_requested)


# def syslog(message: str) -> None:
#     """
#     Log to system logger
#     """
#     log = SystemLog(message=message)
#     db_session.add(log)
#     db_session.commit()


# def response_status(response) -> bool:
#     """
#     :param response:  http request response
#     """
#     code = response.code
#     if (100 <= code <= 199) or (200 <= code <= 299) or (300 <= code <= 399):
#         return True
#     elif 400 <= code <= 599:
#         return False
