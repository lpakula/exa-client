import os
import sys
import logging
import traceback

from db import db_session
from models import Log


class SQLAlchemyHandler(logging.Handler):
    """Logger that commits a LogRecord to the SQL Db"""

    def emit(self, record):
        # from __init__ import __version__
        trace = None
        exc = record.__dict__['exc_info']
        if exc:
            trace = traceback.format_exc(exc)
        log = Log(
            logger=record.__dict__['name'],
            level=record.__dict__['levelname'],
            trace=trace,
            msg=record.__dict__['msg'],
            )
        db_session.add(log)
        db_session.commit()


def log_exception(e, exchange: str = '') -> None:
    """Log exception stack"""
    exc_type, exc_obj, exc_tb = sys.exc_info()
    stack = []
    while True:
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        lineno = exc_tb.tb_lineno
        stack.append(f'{fname}: {lineno}')
        exc_tb = exc_tb.tb_next
        if not exc_tb:
            break

    logger = logging.getLogger(__name__)
    logger.addHandler(SQLAlchemyHandler())
    logger.setLevel(logging.error)
    logger.error(f'{e} | type: {exc_type} | stack: {stack} | exchange: {exchange}')
