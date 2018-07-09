#!/usr/bin/python
# -*- coding: utf-8 -*-
import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base

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
    import models

    Base.metadata.create_all(bind=engine)

    setting = models.Settings.query.get(1)
    if not setting:
        settings = models.Settings()
        db_session.add(settings)
        db_session.commit()

    for exchange_name in ['binance']:
        exchange = models.Exchange.query.filter_by(name=exchange_name).all()
        if not exchange:
            exchange = models.Exchange(name=exchange_name)
            db_session.add(exchange)
            db_session.commit()






