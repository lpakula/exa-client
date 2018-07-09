#!/usr/bin/python
# -*- coding: utf-8 -*-
from datetime import datetime

from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime
from sqlalchemy_utils import ScalarListType

from database import Base


class Settings(Base):
    """
    Settings model
    """
    __tablename__ = 'settings'

    id = Column(Integer, primary_key=True)
    connected = Column(Boolean())
    exa_token = Column(String(100))
    allowed_pairs = Column(ScalarListType())
    allowed_actions = Column(ScalarListType())
    allowed_balance = Column(Float(precision=4))
    test_mode = Column(Boolean())


class Exchange(Base):
    """
    Exchange model
    """
    __tablename__ = 'exchange'

    id = Column(Integer, primary_key=True)
    name = Column(String(10))
    valid = Column(Boolean())
    enabled = Column(Boolean())
    refreshed = Column(DateTime())

    api_key = Column(String(66))
    api_secret = Column(String(66))

    def __init__(self, name, api_key=None, api_secret=None, enabled=True, valid=False, refreshed=None):
        self.name = name
        self.valid = valid
        self.enabled = enabled
        self.refreshed = refreshed
        self.api_key = api_key
        self.api_secret = api_secret


class Transaction(Base):
    """
    Track transactions executed by client
    """
    __tablename__ = 'transactions'

    id = Column(Integer, primary_key=True)
    pair = Column(String(10))
    action_name = Column(String(20))
    amount = Column(Float(precision=4))
    balance_usdt = Column(Float(precision=4))
    created = Column(DateTime, default=datetime.now)


class SystemLog(Base):
    """
    Log model
    """
    __tablename__ = 'log'

    id = Column(Integer, primary_key=True)
    message = Column(String)
    created = Column(DateTime, default=datetime.now)


class Symbol(Base):
    """
    Symbols model
    """
    __tablename__ = 'symbol'

    id = Column(Integer, primary_key=True)
    name = Column(String)
