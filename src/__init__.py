import os, sys; sys.path.append(os.path.dirname(os.path.realpath(__file__)))
import logging
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from flask import Flask

from db import init_db, db_session
from models import Exchange
from utils.action import ActionHandler
from utils.exchange import ExchangeHelper
from utils.database import get_config, get_server
from logger import SQLAlchemyHandler, log_exception
from utils.server import ExAServerHelper


__version__ = '3.0.0'
logger = logging.getLogger(__name__)
logger.addHandler(SQLAlchemyHandler())
logger.setLevel(logging.INFO)


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
        app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
    else:
        app = Flask(__name__)

    app.secret_key = os.environ.get('SECRET_KEY', 'key')

    if test_config is None:
        app.config.from_pyfile('config.py', silent=True)
    else:
        app.config.from_mapping(test_config)

    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    init_db()
    config = get_config()
    server = get_server()

    @app.context_processor
    def context():
        return dict(version=__version__, config=config, server=server)

    from blueprints import auth
    from blueprints import dashboard
    from blueprints import exchange
    from blueprints import logs
    from blueprints import transactions
    from blueprints import config
    app.register_blueprint(auth.bp)
    app.register_blueprint(dashboard.bp)
    app.register_blueprint(exchange.bp)
    app.register_blueprint(logs.bp)
    app.register_blueprint(transactions.bp)
    app.register_blueprint(config.bp)

    def run_actions():
        valid_exchanges = Exchange.query.filter_by(valid=True, enabled=True).all()
        if valid_exchanges:
            for valie_exchange in valid_exchanges:
                valie_exchange.refreshed = datetime.utcnow()
            db_session.commit()

            try:
                actions = ExAServerHelper().get_actions(exchanges=[e.name for e in valid_exchanges])
            except Exception as e:
                log_exception(e)
                return False

            if not actions:
                return False

            for action in actions:
                try:
                    ex = ExchangeHelper(Exchange.query.filter_by(name=action['exchange']).one())
                    ActionHandler(
                        action_id=action['id'],
                        buy_or_sell=action['buy_or_sell'],
                        pair=action['pair'],
                        amount=action['amount'],
                        exchange=ex,
                        deposit_asset=action.get('deposit', ''))
                except Exception as e:
                    log_exception(e, exchange=action['exchange'])

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
