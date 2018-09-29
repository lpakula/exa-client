from flask import render_template, flash, request, redirect, url_for

from db import db_session
from models import Exchange
from utils.exchange import ExchangeHelper
from utils.auth import connect_required

from . import bp
from .forms import ExchangeForm


@bp.route("/<int:exchange_id>/edit", methods=['GET', 'POST'])
@connect_required
def edit(exchange_id):
    exchange = Exchange.query.get(exchange_id)
    form = ExchangeForm(obj=exchange)
    if request.method == 'POST':
        form = ExchangeForm(request.form)
        exchange.enabled = form.enabled.data
        exchange.api_key = form.api_key.data
        exchange.api_secret = form.api_secret.data
        exchange.valid = ExchangeHelper(exchange=exchange).status
        db_session.commit()

        if exchange.valid:
            flash('Account has been updated.', 'success')
        else:
            flash("Account has been updated but is invalid. Please checks the logs for more "
                  "details", 'warning')

        return redirect(url_for('dashboard.index'))
    return render_template('exchange/edit.html', form=form, exchange=exchange)

