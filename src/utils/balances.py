"""
Tracker for balance used by client
"""
from models import Transaction, Settings


def get_balances():
    """Get used balance"""
    settings = Settings.query.get(1)
    if not settings.allowed_balance:
        return {}

    buy_transaction_entries = Transaction.query.filter_by(action_name='order_market_buy')
    balances = {}
    for transaction in buy_transaction_entries:
        try:
            balances[transaction.pair]['balance'] += transaction.balance_usdt
        except KeyError:
            balances[transaction.pair] = {}
            balances[transaction.pair]['balance'] = 0
            balances[transaction.pair]['balance'] += transaction.balance_usdt

    for key, value in balances.items():
        usage = (value['balance'] / settings.allowed_balance) * 100
        if usage > 100:
            label = 'danger'
        elif usage > 70:
            label = 'warning'
        else:
            label = 'navy'
        balances[key]['label'] = label

    return balances
