"""Database Models"""
import arrow

from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, ForeignKey
from sqlalchemy_utils import ScalarListType

from database import Base


class Settings(Base):
    """Model to store user config"""
    __tablename__ = 'settings'

    id = Column(Integer, primary_key=True)
    connected = Column(Boolean())
    exa_token = Column(String(100))
    allowed_pairs = Column(ScalarListType())
    allowed_actions = Column(ScalarListType())
    allowed_balance = Column(Float(precision=4))
    test_mode = Column(Boolean())


class Exchange(Base):
    """Model to store exchange credentials"""
    __tablename__ = 'exchange'

    id = Column(Integer, primary_key=True)
    name = Column(String(10), nullable=False)
    valid = Column(Boolean())
    enabled = Column(Boolean())
    refreshed = Column(DateTime())

    api_key = Column(String(66), default='')
    api_secret = Column(String(66), default='')
    password = Column(String, default='')
    uid = Column(Integer)

    def __init__(self, name, api_key=None, api_secret=None, password=None, uid=None,
                 enabled=True, valid=False, refreshed=None):
        self.name = name
        self.valid = valid
        self.enabled = enabled
        self.refreshed = refreshed
        self.api_key = api_key
        self.api_secret = api_secret
        self.password = password
        self.uid = uid


class Pair(Base):
    """Model to store available trading pairs"""
    __tablename__ = 'pair'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    

# class Action(Base):
#     """
#     Action to perorm.
#
#     Some actions group transactions that complete it
#     eg. order_limit_buy action that use USD deposit will perform at least two buy transactions
#     to complete
#     """
#     id = Column(Integer, primary_key=True)
#     action_id = Column(Integer, nullable=False)
#     action_type = Column(String, nullable=False)
#     pair = Column('pair_id', Integer, ForeignKey("pair.id"), nullable=False),
#     amount = Column(Float(precision=8))
#     deposit = Column(String)
#     deposit_amount = Column(Float(precision=8))


class Transaction(Base):
    """Transaction to perform"""
    __tablename__ = 'transactions'

    id = Column(Integer, primary_key=True)
    action_id = Column(Integer, nullable=False)
    buy_or_sell = Column(String, nullable=False)
    exchange = Column(String, nullable=False)
    pair = Column(String, nullable=False)
    rate = Column(Float(precision=8), default=0, nullable=False)
    amount = Column(Float(precision=8), default=0, nullable=False)
    order_id = Column(Integer)
    filled = Column(Float(precision=8), default=0)
    status = Column(String)
    created = Column(DateTime, default=arrow.utcnow().datetime)



    # def perform(self):

    # def __init__(self, action_id, buy_or_sell, exchange, pair, rate, amount,
    #              order_id=None, filled=0):
    #
    #     self.action_id = action_id
    #     self.buy_or_sell = buy_or_sell
    #     self.exchange = exchange
    #     self.pair = pair
    #     self.rate = rate
    #     self.amount = amount
    #     self.order_id = order_id
    #     self.filled = filled

    def check_status(self):
        """Check order status"""
        pass

    def create_order(self):
        pass

    def cancel_order(self):
        pass


class Log(Base):
    """Database Log"""
    __tablename__ = 'logs'
    id = Column(Integer, primary_key=True) 
    logger = Column(String)
    level = Column(String)
    trace = Column(String)
    msg = Column(String)
    created_at = Column(DateTime, default=arrow.utcnow().datetime)

    def __init__(self, logger=None, level=None, trace=None, msg=None):
        self.logger = logger
        self.level = level
        self.trace = trace
        self.msg = msg

    def __unicode__(self):
        return self.__repr__()

    def __repr__(self):
        return "<Log: %s - %s>" % (self.created_at.strftime('%m/%d/%Y-%H:%M:%S'), self.msg[:50])



