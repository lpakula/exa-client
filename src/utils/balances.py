"""
Tracker for balance used by client
"""
from collections import defaultdict
from typing import Dict, Any

from models import Transaction
from utils.database import get_config


def get_balances() -> Dict:
    """Get balance stats"""
    config = get_config()
    if not config.allowed_balance:
        return {}

    buy_transaction_entries = Transaction.query.filter_by(buy_or_sell='buy')
    balances = defaultdict(Dict[0, Any])
    for transaction in buy_transaction_entries:
        balances[transaction.pair]['balance'] += transaction.balance_usdt

    for key, value in balances.items():
        usage = (value['balance'] / config.allowed_balance) * 100
        if usage > 100:
            label = 'danger'
        elif usage > 70:
            label = 'warning'
        else:
            label = 'navy'
        balances[key]['label'] = label

    return balances


def balance_exceeded(pair: str, balance_requested: float) -> bool:
    """Check if requested balance does not exeed limit"""
    transactions = Transaction.query.filter_by(buy_or_sell='buy', pair=pair)
    balance_allowed = get_config().allowed_balance
    balance_used = sum([t.price_fiat * t.amount for t in transactions])
    return not balance_allowed > balance_used + balance_requested
