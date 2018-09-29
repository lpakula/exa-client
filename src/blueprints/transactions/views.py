from flask import render_template, flash, request, redirect, url_for
from sqlalchemy import desc

from db import db_session
from models import Transaction
from utils.auth import connect_required
from utils.balances import get_balances

from . import bp


@bp.route("/")
@connect_required
def index():
    transactions = Transaction.query.order_by(desc(Transaction.created)).all()
    balances = get_balances()
    return render_template(
        'transactions/index.html', transactions=transactions, balances=balances,
        )


@bp.route("/delete")
@connect_required
def delete():
    Transaction.query.delete()
    db_session.commit()
    flash('Transactions have been deleted.', 'success')
    return redirect(url_for('transactions.index'))

