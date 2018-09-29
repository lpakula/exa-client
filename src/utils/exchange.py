"""
ccxt abstraction for common exchange actions

Helper is based on ``Exchange`` class from freqtrade repo
https://github.com/freqtrade/freqtrade
"""
import ccxt
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from math import floor, ceil

from ccxt.base.errors import ExchangeError

from exceptions import DependencyException, OperationalException, TemporaryError
from models import Exchange
from logger import SQLAlchemyHandler


logger = logging.getLogger(__name__)
logger.addHandler(SQLAlchemyHandler())
logger.setLevel(logging.INFO)


def retrier(f):
    def wrapper(*args, **kwargs):
        count = kwargs.pop('count', 5)
        try:
            return f(*args, **kwargs)
        except (TemporaryError, DependencyException) as ex:
            logger.warning('%s() returned exception: "%s"', f.__name__, ex)
            if count > 0:
                count -= 1
                kwargs.update({'count': count})
                logger.warning('retrying %s() still for %s times', f.__name__, count)
                return wrapper(*args, **kwargs)
            else:
                logger.warning('Giving up retrying: %s()', f.__name__)
                raise ex
    return wrapper


class ExchangeHelper(object):
    """
    ccxt abstraction for common exchange actions
    """
    FIAT_SYMBOLS = ['USDT', 'TUSD', 'USD']

    _cached_ticker: Dict[str, Any] = {}

    def __init__(self, exchange: Exchange) -> None:
        """
        :param str exchange: exchange name
        """
        config = {
            'apiKey': exchange.api_key.strip(),
            'secret': exchange.api_secret.strip(),
            # 'password': exchange.password.strip() or '',
            # 'uid': exchange.uid.strip() or ''
            'options': {
                'adjustForTimeDifference': True
            }
        }

        self.client = getattr(ccxt, exchange.name)(config)
        self.client.load_markets()

    @property
    def name(self) -> str:
        """
        Exchange Name (from ccxt)
        """
        return self.client.name

    @property
    def id(self) -> str:
        """
        Exchange ccxt id
        """
        return self.client.id

    @property
    def status(self) -> bool:
        """
        Returns client status
        """
        try:
            self.client.fetchDepositAddress('BTC')
            return True
        except ExchangeError as e:
            logger.error(f'Invalid Exchange Account API Keys: {e}')
            return False
        
    def exchange_has(self, endpoint: str) -> bool:
        """
        Checks if exchange implements a specific API endpoint.
        Wrapper around ccxt 'has' attribute
        :param endpoint: Name of endpoint (e.g. 'fetchOHLCV', 'fetchTickers')
        :return: bool
        """
        return endpoint in self.client.has and self.client.has[endpoint]
    
    def symbol_amount_prec(self, pair, amount: float):
        """
        Returns the amount to buy or sell to a precision the Exchange accepts
        Rounded down
        """
        if self.client.markets[pair]['precision']['amount']:
            symbol_prec = self.client.markets[pair]['precision']['amount']
            big_amount = amount * pow(10, symbol_prec)
            amount = floor(big_amount) / pow(10, symbol_prec)
        return amount

    def symbol_price_prec(self, pair, price: float):
        """
        Returns the price buying or selling with to the precision the Exchange accepts
        Rounds up
        """
        if self.client.markets[pair]['precision']['price']:
            symbol_prec = self.client.markets[pair]['precision']['price']
            big_price = price * pow(10, symbol_prec)
            price = ceil(big_price) / pow(10, symbol_prec)
        return price
    
    def buy(self, pair: str, rate: float, amount: float) -> Dict:
        try:
            amount = self.symbol_amount_prec(pair, amount)
            rate = self.symbol_price_prec(pair, rate)

            return self.client.create_limit_buy_order(pair, amount, rate)
        except ccxt.InsufficientFunds as e:
            raise DependencyException(
                f'Insufficient funds to create limit buy order on market {pair}.'
                f'Tried to buy amount {amount} at rate {rate} (total {rate*amount}).'
                f'Message: {e}')
        except ccxt.InvalidOrder as e:
            raise DependencyException(
                f'Could not create limit buy order on market {pair}.'
                f'Tried to buy amount {amount} at rate {rate} (total {rate*amount}).'
                f'Message: {e}')
        except (ccxt.NetworkError, ccxt.ExchangeError) as e:
            raise TemporaryError(
                f'Could not place buy order due to {e.__class__.__name__}. Message: {e}')
        except ccxt.BaseError as e:
            raise OperationalException(e)

    def sell(self, pair: str, rate: float, amount: float) -> Dict:
        try:
            # Set the precision for amount and price(rate) as accepted by the exchange
            amount = self.symbol_amount_prec(pair, amount)
            rate = self.symbol_price_prec(pair, rate)

            return self.client.create_limit_sell_order(pair, amount, rate)
        except ccxt.InsufficientFunds as e:
            raise DependencyException(
                f'Insufficient funds to create limit sell order on market {pair}.'
                f'Tried to sell amount {amount} at rate {rate} (total {rate*amount}).'
                f'Message: {e}')
        except ccxt.InvalidOrder as e:
            raise DependencyException(
                f'Could not create limit sell order on market {pair}.'
                f'Tried to sell amount {amount} at rate {rate} (total {rate*amount}).'
                f'Message: {e}')
        except (ccxt.NetworkError, ccxt.ExchangeError) as e:
            raise TemporaryError(
                f'Could not place sell order due to {e.__class__.__name__}. Message: {e}')
        except ccxt.BaseError as e:
            raise OperationalException(e)

    @retrier
    def get_balance(self, currency: str) -> float:
        balances = self.get_balances()
        balance = balances.get(currency)
        if balance is None:
            raise TemporaryError(
                f'Could not get {currency} balance due to malformed exchange response: {balances}')
        return balance['free']

    @retrier
    def get_balances(self) -> dict:
        try:
            balances = self.client.fetch_balance()
            # Remove additional info from ccxt results
            balances.pop("info", None)
            balances.pop("free", None)
            balances.pop("total", None)
            balances.pop("used", None)

            return balances
        except (ccxt.NetworkError, ccxt.ExchangeError) as e:
            raise TemporaryError(
                f'Could not get balance due to {e.__class__.__name__}. Message: {e}')
        except ccxt.BaseError as e:
            raise OperationalException(e)

    @retrier
    def get_tickers(self) -> Dict:
        try:
            return self.client.fetch_tickers()
        except ccxt.NotSupported as e:
            raise OperationalException(
                f'Exchange {self.client.name} does not support fetching tickers in batch.'
                f'Message: {e}')
        except (ccxt.NetworkError, ccxt.ExchangeError) as e:
            raise TemporaryError(
                f'Could not load tickers due to {e.__class__.__name__}. Message: {e}')
        except ccxt.BaseError as e:
            raise OperationalException(e)

    @retrier
    def get_ticker(self, pair: str, refresh: Optional[bool] = True) -> dict:
        if refresh or pair not in self._cached_ticker.keys():
            try:
                data = self.client.fetch_ticker(pair)
                try:
                    self._cached_ticker[pair] = {
                        'bid': float(data['bid']),
                        'ask': float(data['ask']),
                        'last': float(data['last'])
                    }
                except KeyError:
                    logger.debug("Could not cache ticker data for %s", pair)
                return self._cached_ticker[pair]
            except (ccxt.NetworkError, ccxt.ExchangeError) as e:
                raise TemporaryError(
                    f'Could not load ticker due to {e.__class__.__name__}. Message: {e}')
            except ccxt.BaseError as e:
                raise OperationalException(e)
        else:
            logger.info("returning cached ticker-data for %s", pair)
            return self._cached_ticker[pair]

    @retrier
    def cancel_order(self, order_id: str, pair: str) -> None:
        try:
            return self.client.cancel_order(order_id, pair)
        except ccxt.InvalidOrder as e:
            raise DependencyException(
                f'Could not cancel order. Message: {e}')
        except (ccxt.NetworkError, ccxt.ExchangeError) as e:
            raise TemporaryError(
                f'Could not cancel order due to {e.__class__.__name__}. Message: {e}')
        except ccxt.BaseError as e:
            raise OperationalException(e)

    @retrier
    def get_order(self, order_id: str, pair: str) -> Dict:
        try:
            return self.client.fetch_order(order_id, pair)
        except ccxt.InvalidOrder as e:
            raise DependencyException(
                f'Could not get order. Message: {e}')
        except (ccxt.NetworkError, ccxt.ExchangeError) as e:
            raise TemporaryError(
                f'Could not get order due to {e.__class__.__name__}. Message: {e}')
        except ccxt.BaseError as e:
            raise OperationalException(e)

    @retrier
    def get_order_book(self, pair: str, limit: int = 100) -> dict:
        """
        get order book level 2 from exchange

        Notes:
        20180619: bittrex doesnt support limits -.-
        20180619: binance support limits but only on specific range
        """
        try:
            if self.client.name == 'Binance':
                limit_range = [5, 10, 20, 50, 100, 500, 1000]
                # get next-higher step in the limit_range list
                limit = min(list(filter(lambda x: limit <= x, limit_range)))
                # above script works like loop below (but with slightly better performance):
                #   for limitx in limit_range:
                #        if limit <= limitx:
                #           limit = limitx
                #           break

            return self.client.fetch_l2_order_book(pair, limit)
        except ccxt.NotSupported as e:
            raise OperationalException(
                f'Exchange {self.client.name} does not support fetching order book.'
                f'Message: {e}')
        except (ccxt.NetworkError, ccxt.ExchangeError) as e:
            raise TemporaryError(
                f'Could not get order book due to {e.__class__.__name__}. Message: {e}')
        except ccxt.BaseError as e:
            raise OperationalException(e)

    @retrier
    def get_trades_for_order(self, order_id: str, pair: str, since: datetime) -> List:
        if not self.exchange_has('fetchMyTrades'):
            return []
        try:
            my_trades = self.client.fetch_my_trades(pair, since.timestamp())
            matched_trades = [trade for trade in my_trades if trade['order'] == order_id]

            return matched_trades

        except ccxt.NetworkError as e:
            raise TemporaryError(
                f'Could not get trades due to networking error. Message: {e}')
        except ccxt.BaseError as e:
            raise OperationalException(e)

    @retrier
    def get_markets(self) -> List[dict]:
        try:
            return self.client.fetch_markets()
        except (ccxt.NetworkError, ccxt.ExchangeError) as e:
            raise TemporaryError(
                f'Could not load markets due to {e.__class__.__name__}. Message: {e}')
        except ccxt.BaseError as e:
            raise OperationalException(e)

    @retrier
    def get_fee(self, symbol='ETH/BTC', type='', side='', amount=1,
                price=1, taker_or_maker='maker') -> float:
        try:
            # validate that markets are loaded before trying to get fee
            if self.client.markets is None or len(self.client.markets) == 0:
                self.client.load_markets()
            return self.client.calculate_fee(
                symbol=symbol, type=type, side=side, amount=amount, price=price,
                takerOrMaker=taker_or_maker)['rate']
        except (ccxt.NetworkError, ccxt.ExchangeError) as e:
            raise TemporaryError(
                f'Could not get fee info due to {e.__class__.__name__}. Message: {e}')
        except ccxt.BaseError as e:
            raise OperationalException(e)

    def get_rate_limit(self, pair: str, buy_or_sell: str, amount: float,
                       use_order_book: bool = True) -> float:
        """
        Get rate limit for order.
        If use order book, check price required to fill the entire amount
        """

        ticker = self.get_ticker(pair)
        ticker_rate = ticker['ask'] if buy_or_sell == 'buy' else ticker['bid']

        if use_order_book:
            order_book = self.get_order_book(pair, 1000)
            order_type = 'asks' if buy_or_sell == 'buy' else 'bids'
            order_book_amount = 0

            for order in order_book[order_type]:
                order_book_amount += order[1]
                if order_book_amount > amount:
                    ticker_rate = order[0]
                    break

        return ticker_rate

    def get_last_price(self, pair: str, fiat: str = '') -> float:
        """
        Get last pair price.
        :param pair: trading pair
        :param fiat: define fiat substitution eg. USDT, TUSDT, (or USD if supported) to express
                     value in fiat
        """
        ticker = self.get_ticker(pair)
        last_price = ticker['last']
        quote_asset = self.client.markets[pair]['quote']
        if fiat and quote_asset not in self.FIAT_SYMBOLS:
            fiat_last_price = self.get_ticker(f'{quote_asset}/{fiat}')['last']
            last_price = last_price * fiat_last_price
        return last_price

