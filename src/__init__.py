#!/usr/bin/python
# -*- coding: utf-8 -*-
import os, sys; sys.path.append(os.path.dirname(os.path.realpath(__file__)))
import logging
from datetime import datetime
from functools import wraps

from flask import Flask, render_template, flash, request, redirect, url_for, g
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import desc

from models import Settings, Exchange, Transaction, SystemLog, Symbol
from utils.balances import get_balances
from utils.server import ExAServerHelper
from utils.exchange import ExchangeHelper
from database import init_db, db_session
from forms import SettingsForm, ConnectForm, ExchangeForm

VERSION = '2.0.0'


def create_app(test_config=None):

    scheduler = BackgroundScheduler()
    log = logging.getLogger('apscheduler.executors.default')
    log.setLevel(logging.WARNING)
    fmt = logging.Formatter('%(levelname)s:%(name)s:%(message)s')
    h = logging.StreamHandler()
    h.setFormatter(fmt)
    log.addHandler(h)

    if getattr(sys, 'frozen', False):
        template_folder = os.path.join(sys._MEIPASS, 'templates')
        static_folder = os.path.join(sys._MEIPASS, 'static')
        app = Flask( __name__, template_folder=template_folder, static_folder=static_folder)
    else:
        app = Flask(__name__)

    app.secret_key = os.environ.get('EXA_APP_SECRET_KEY', 'key')

    if test_config is None:
        app.config.from_pyfile('config.py', silent=True)
    else:
        app.config.from_mapping(test_config)

    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    init_db()

    def connect_required(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            settings = Settings.query.get(1)
            if not settings.connected:
                return redirect(url_for('connect'))
            return f(*args, **kwargs)
        return decorated_function

    @app.route("/", methods=['GET', 'POST'])
    def connect():
        setting = Settings.query.get(1)
        if setting.connected:
            return redirect(url_for('dashboard'))
        if request.method == 'POST':
            form = ConnectForm(request.form)
            if form.validate():
                status = ExAServerHelper(version=VERSION).connect(
                    username=form.username.data, password=form.password.data)
                if status:
                    flash('You have been connected with the server successfully.', 'success')
                    return redirect(url_for('dashboard'))
                else:
                    flash("You can't connect to the server with provided details. "
                          "Please make sure username and password are correct. "
                          "<br>Please check <a href='{}'> Logs </a> for more details.".format(
                            url_for('logs')), 'danger')
        form = ConnectForm()
        return render_template('connect.html', form=form)

    @app.route("/dashboard")
    @connect_required
    def dashboard():
        exchanges = Exchange.query.all()
        setting = Settings.query.get(1)
        transactions = Transaction.query.all()
        logs = SystemLog.query.all()

        balances = get_balances()
        for key in list(balances.keys()):
            if balances[key]['label'] not in ['warning', 'danger']:
                del balances[key]

        if setting.test_mode:
            flash('ExA client is running in test mode. No transations are performed on exchange. '
                  'You can inspect executed actions in logs', 'warning')
        return render_template(
            'dashboard.html', exchanges=exchanges, setting=setting, balances=balances,
            transactions=transactions, logs=logs, version=VERSION)

    @app.route("/exchange/<int:exchange_id>/edit", methods=['GET', 'POST'])
    @connect_required
    def exchange_edit(exchange_id):
        exchange = Exchange.query.get(exchange_id)
        form = ExchangeForm(obj=exchange)
        if request.method == 'POST':
            form = ExchangeForm(request.form)
            exchange.enabled = form.enabled.data
            exchange.api_key = form.api_key.data
            exchange.api_secret = form.api_secret.data
            exchange.valid = ExchangeHelper(exchange=exchange.name, version=VERSION).check_status()
            db_session.commit()

            if exchange.valid:
                flash('Account has been updated.', 'success')
            else:
                flash("Account has been updated but is invalid. Please checks the logs for more "
                      "details", 'warning')

            return redirect(url_for('dashboard'))
        return render_template('exchange.html', form=form, exchange=exchange)

    @app.route("/security/", methods=['GET', 'POST'])
    @connect_required
    def security():
        setting = Settings.query.get(1)
        pair_choices = [(i.name, i.name) for i in Symbol.query.all()]

        form = SettingsForm(obj=setting)
        form.allowed_pairs.choices = pair_choices
        if request.method == 'POST':
            form = SettingsForm(request.form)
            form.allowed_pairs.choices = pair_choices
            if form.validate():
                setting.allowed_pairs = form.allowed_pairs.data
                setting.allowed_actions = form.allowed_actions.data
                setting.allowed_balance = form.allowed_balance.data
                setting.test_mode = form.test_mode.data
                db_session.commit()
                flash('Settings have been updated.', 'success')
                return redirect(url_for('dashboard'))

        return render_template('security.html', form=form)

    @app.route("/symbols/sync/")
    @connect_required
    def sync_symbols():
        ExAServerHelper(version=VERSION).sync_symbols()
        flash('Trading pairs have been refreshed.', 'success')
        return redirect(url_for('security'))

    @app.route("/logs")
    def logs():
        log_entries = SystemLog.query.order_by(desc(SystemLog.created)).all()
        settings = Settings.query.get(1)
        return render_template('logs.html', logs=log_entries, is_connected=settings.connected)

    @app.route("/logs/send")
    @connect_required
    def logs_send():
        log_entries = SystemLog.query.order_by(desc(SystemLog.created)).all()
        if log_entries:
            status = ExAServerHelper(version=VERSION).send_logs()
            if status:
                flash('Logs have been sent successfully.', 'success')
            else:
                flash('Logs have not been sent. If problem persists please contact administrator.',
                      'danger')
        else:
            flash('No logs to send.', 'warning')
        return redirect(url_for('logs'))

    @app.route("/logs/delete")
    def logs_delete():
        SystemLog.query.delete()
        db_session.commit()
        flash('Logs have been deleted.', 'success')
        return redirect(url_for('logs'))

    @app.route("/transactions")
    @connect_required
    def transactions():
        setting = Settings.query.get(1)
        transaction_entries = Transaction.query.order_by(desc(Transaction.created)).all()
        balances = get_balances()
        return render_template(
            'transactions.html', transactions=transaction_entries, balances=balances,
            setting=setting)

    @app.route("/transactions/delete")
    @connect_required
    def transactions_delete():
        Transaction.query.delete()
        db_session.commit()
        flash('Transactions have been deleted.', 'success')
        return redirect(url_for('transactions'))

    def run_actions():
        valid_exchanges = Exchange.query.filter_by(valid=True, enabled=True).all()
        if valid_exchanges:
            for valie_exchange in valid_exchanges:
                valie_exchange.refreshed = datetime.utcnow()
            db_session.commit()

            try:
                actions = ExAServerHelper(version=VERSION).get_actions(
                    exchanges=[e.name for e in valid_exchanges])
            except Exception as e:
                _log_exception(e)
                return False

            if not actions:
                return False

            for trade_actions in actions:
                try:
                    ExchangeHelper(
                        exchange=trade_actions['exchange'], version=VERSION).run_actions(
                        actions=trade_actions['actions'])
                except Exception as e:
                    _log_exception(e, exchange=trade_actions['exchange'])

    def _log_exception(e, exchange=None):
        if exchange:
            exchange_name = exchange
            exchange_obj = Exchange.query.get(name=exchange_name)
            exchange_obj.enabled = False
        else:
            exchange_name = None

        exc_type, exc_obj, exc_tb = sys.exc_info()
        stack = []
        while True:
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            lineno = exc_tb.tb_lineno
            stack.append('{}: {}'.format(fname, lineno))
            exc_tb = exc_tb.tb_next
            if not exc_tb:
                break

        log_entry = SystemLog(
            message='{message} | type: {type} | stack: {stack} | exchange: {exchange}'
            .format(message=e, type=exc_type, stack=stack, exchange=exchange_name))
        db_session.add(log_entry)
        db_session.commit()

    if app.config['TESTING']:
        @app.route("/test/run_actions")
        def test_run_actions():
            run_actions()
            return ''
    else:
        @app.teardown_appcontext
        def shutdown_session(exception=None):
            db_session.remove()

        trigger = IntervalTrigger(seconds=10)
        scheduler.add_job(run_actions, trigger=trigger, id='run_actions')
        scheduler.start()

    return app


if __name__ == '__main__':
    create_app().run()
