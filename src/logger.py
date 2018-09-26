import logging
import traceback

from database import db_session
from models import Log


class SQLAlchemyHandler(logging.Handler):
    """Logger that commits a LogRecord to the SQL Db"""

    def emit(self, record):
        trace = None
        exc = record.__dict__['exc_info']
        if exc:
            trace = traceback.format_exc(exc)
        log = Log(
            logger=record.__dict__['name'],
            level=record.__dict__['levelname'],
            trace=trace,
            msg=record.__dict__['msg'],)
        db_session.add(log)
        db_session.commit()
