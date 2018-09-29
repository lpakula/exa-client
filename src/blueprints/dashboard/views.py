from flask import render_template, flash, request, redirect, url_for

from models import Exchange, Transaction, Log
from utils.database import get_server
from utils.auth import connect_required
from utils.balances import get_balances

from . import bp


@bp.route("/")
@connect_required
def index():
    exchanges = Exchange.query.all()
    transactions = Transaction.query.count()
    logs = Log.query.count()

    balances = get_balances()
    for key in list(balances.keys()):
        if balances[key]['label'] not in ['warning', 'danger']:
            del balances[key]

    return render_template(
        'dashboard/index.html', exchanges=exchanges, balances=balances,
        transactions=transactions, logs=logs)
