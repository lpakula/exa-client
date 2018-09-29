"""
Configure database
"""
import os
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm.exc import NoResultFound

if getattr(sys, 'frozen', False):
    application_path = os.path.dirname(sys.executable)
else:
    application_path = os.path.dirname(__file__)

engine = create_engine(
    os.environ.get('DB', 'sqlite:///{}/exa.db'.format(application_path)),
    convert_unicode=True)
db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

Base = declarative_base()
Base.query = db_session.query_property()


def init_db():
    """Init database and create initial objecs"""
    import models

    Base.metadata.create_all(bind=engine)

    try:
        models.Config.query.one()
    except NoResultFound:
        config = models.Config()
        db_session.add(config)
        db_session.commit()

    try:
        models.ExAServer.query.one()
    except NoResultFound:
        server = models.ExAServer()
        db_session.add(server)
        db_session.commit()

    for e in ['binance', 'bittrex']:
        try:
            models.Exchange.query.filter_by(name=e).one()
        except NoResultFound:
            exchange = models.Exchange(name=e)
            db_session.add(exchange)
            db_session.commit()
