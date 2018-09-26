"""
ccxt abstraction for common exchange actions

Helper is based on ``Exchange`` class from freqtrade repo
https://github.com/freqtrade/freqtrade
"""
import ccxt
import time
import math
import arrow
import logging
from decimal import Decimal as D
from datetime import datetime
from typing import List, Dict, Any, Optional
from math import floor, ceil

from ccxt.base.errors import InsufficientFunds, BaseError, ExchangeError

from utils.helpers import get_settings
from utils.server import ExAServerHelper
from exceptions import DependencyException, OperationalException, TemporaryError
from models import Exchange, Transaction
from database import db_session


logger = logging.getLogger(__name__)


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
        self.settings = get_settings()
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
        # self.exa_server = ExAServerHelper()

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

    # @retrier
    # def get_candle_history(self, pair: str, tick_interval: str,
    #                        since_ms: Optional[int] = None) -> List[Dict]:
    #     try:
    #         # last item should be in the time interval [now - tick_interval, now]
    #         till_time_ms = arrow.utcnow().shift(
    #                         minutes=-constants.TICKER_INTERVAL_MINUTES[tick_interval]
    #                     ).timestamp * 1000
    #         # it looks as if some exchanges return cached data
    #         # and they update it one in several minute, so 10 mins interval
    #         # is necessary to skeep downloading of an empty array when all
    #         # chached data was already downloaded
    #         till_time_ms = min(till_time_ms, arrow.utcnow().shift(minutes=-10).timestamp * 1000)
    #
    #         data: List[Dict[Any, Any]] = []
    #         while not since_ms or since_ms < till_time_ms:
    #             data_part = self.client.fetch_ohlcv(pair, timeframe=tick_interval, since=since_ms)
    #
    #             # Because some exchange sort Tickers ASC and other DESC.
    #             # Ex: Bittrex returns a list of tickers ASC (oldest first, newest last)
    #             # when GDAX returns a list of tickers DESC (newest first, oldest last)
    #             data_part = sorted(data_part, key=lambda x: x[0])
    #
    #             if not data_part:
    #                 break
    #
    #             logger.debug('Downloaded data for %s time range [%s, %s]',
    #                          pair,
    #                          arrow.get(data_part[0][0] / 1000).format(),
    #                          arrow.get(data_part[-1][0] / 1000).format())
    #
    #             data.extend(data_part)
    #             since_ms = data[-1][0] + 1
    #
    #         return data
    #     except ccxt.NotSupported as e:
    #         raise OperationalException(
    #             f'Exchange {self.client.name} does not support fetching historical candlestick data.'
    #             f'Message: {e}')
    #     except (ccxt.NetworkError, ccxt.ExchangeError) as e:
    #         raise TemporaryError(
    #             f'Could not load ticker history due to {e.__class__.__name__}. Message: {e}')
    #     except ccxt.BaseError as e:
    #         raise OperationalException(f'Could not fetch ticker data. Msg: {e}')

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

    # def get_pair_detail_url(self, pair: str) -> str:
    #     try:
    #         url_base = self.client.urls.get('www')
    #         base, quote = pair.split('/')
    #
    #         return url_base + self._EXCHANGE_URLS[self.client.id].format(base=base, quote=quote)
    #     except KeyError:
    #         logger.warning('Could not get exchange url for %s', self.name)
    #         return ""

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


    # def run_actions(self, actions):
    #     for action in actions:
    #         try:
    #             action_name = self.ACTIONS[action['action']]
    #         except KeyError:
    #             e = 'Unknown action: {}'.format(action['action'])
    #             self.exa_server.confirm_action(
    #                 action_id=action['action_id'], status=False, response=e)
    #             raise ExAClientException(e)
    #
    #         if self.settings.allowed_pairs:
    #             if action['symbol']['symbol'] not in self.settings.allowed_pairs:
    #                 message = '{} pair is not allowed'.format(action['symbol']['symbol'])
    #                 self.exa_server.confirm_action(
    #                     action_id=action['action_id'], status=False, response=message)
    #                 raise ExAClientExcemption(message)
    #
    #         if self.settings.allowed_actions:
    #             allowed_actions = self.settings.allowed_actions + ['sync_amount']
    #             if action_name not in allowed_actions:
    #                 message = 'Action not allowed: {}'.format(action_name)
    #                 self.exa_server.confirm_action(
    #                     action_id=action['action_id'], status=False, response=message)
    #                 raise ExAClientException(message)
    #
    #         if action_name not in ['sync_amount']:
    #             balance_requested = self.get_latest_price_usdt(action['symbol']) * D(action['amount'])
    #         else:
    #             balance_requested = None
    #
    #         if self.settings.allowed_balance and action_name == 'order_market_buy':
    #             if not self.check_balance(action, balance_requested=balance_requested):
    #                 message = 'Allowed balance exceeded: {} < {}'.format(
    #                     self.settings.allowed_balance, self.balance_used)
    #                 self.exa_server.confirm_action(
    #                     action_id=action['action_id'], status=False, response=message)
    #                 raise ExAClientException(message)
    #
    #         getattr(self, action_name)(data=action)
    #
    # def order_market_buy(self, data):
    #     """
    #     Perform order market buy
    #
    #     """
    #     latest_price = self.get_latest_price(symbol=data['symbol'])
    #     asset_quantity_requested = D(data['amount']) * latest_price
    #     asset_quantity_available = self.get_balance(symbol=data['symbol']['quote_asset'])
    #
    #     valid_quantity = D(data['amount'])
    #
    #     #: Make sure requested amount is available
    #     if asset_quantity_requested > asset_quantity_available:
    #         valid_quantity = self.validate_quantity(
    #             quantity=asset_quantity_available / latest_price, symbol=data['symbol'])
    #         self._log('Amount reduced due to available balance: {}'.format(valid_quantity))
    #
    #     params = {'symbol': data['symbol']['symbol'], 'amount': valid_quantity}
    #
    #     # For very dynamic price fluctuations, reduce amount to fulfill the order if insufficient
    #     # balance exception is raised
    #     for i in range(1, 5):
    #         try:
    #             output = self._perform_order_market(
    #                 action_type='buy', action_id=data['action_id'], params=params)
    #             data['amount'] = params['amount']
    #             balance_requested = self.get_latest_price_usdt(data['symbol']) * D(params['amount'])
    #             self._log_transaction(action=data, balance_usdt=balance_requested)
    #             return output
    #         except InsufficientFunds as e:
    #             self._log(str(e))
    #             if i <= 3:
    #                 diff = i**2
    #                 new_quantity = valid_quantity - ((D(diff) / 100) * valid_quantity)
    #                 valid_quantity = self.validate_quantity(
    #                     quantity=new_quantity, symbol=data['symbol'])
    #                 params['amount'] = valid_quantity
    #                 self._log('Amount reduced due to insufficient balance: {}'.format(new_quantity))
    #             else:
    #                 self._log(str(e))
    #                 self.exa_server.confirm_action(
    #                     action_id=data['action_id'], status=False, response=str(e))
    #                 raise BaseError(e)
    #
    # def order_market_sell(self, data):
    #     """
    #     Perform order market sell
    #
    #     """
    #     quantity_available = self.get_balance(symbol=data['symbol']['base_asset'])
    #     valid_quantity = D(data['amount'])
    #
    #     #: Make sure requested amount is available
    #     if quantity_available < valid_quantity:
    #         valid_quantity = self.validate_quantity(
    #             quantity=quantity_available, symbol=data['symbol'])
    #         self._log('Amount reduced due to available balance: {}'.format(valid_quantity))
    #
    #     params = {'symbol': data['symbol']['symbol'], 'amount': valid_quantity}
    #
    #     try:
    #         self._perform_order_market(
    #             action_type='sell', action_id=data['action_id'], params=params)
    #         balance_requested = self.get_latest_price_usdt(data['symbol']) * D(params['amount'])
    #         data['amount'] = params['amount']
    #         self._log_transaction(action=data, balance_usdt=balance_requested)
    #     except BaseError as e:
    #         self._log(str(e))
    #         self.exa_server.confirm_action(
    #             action_id=data['action_id'], status=False, response=str(e))
    #
    # def _perform_order_market(self, action_type, action_id, params):
    #     """
    #     Perform order market action
    #
    #     :param action_type: ``buy`` or ``sell``
    #     :param action_id: corresponding action id
    #     :param params: order params
    #
    #     """
    #     self._log('Order Market {}: {}'.format(action_type.title(), params))
    #     if self.settings.test_mode:
    #         self._log('Test Mode: No transaction performed.')
    #         self.exa_server.confirm_action(action_id=action_id, status=True, response='TEST MODE')
    #         return None
    #     else:
    #         response = getattr(self.client, 'createMarket{}Order'.format(action_type.title()))(
    #             **params)
    #         self._log(message=str(response))
    #         self.exa_server.confirm_action(action_id=action_id, status=True, response=response)
    #         return response
    #
    # def sync_amount(self, data):
    #     """
    #     Sync trade amount with exchange balance if balance lower then current amount
    #
    #     """
    #     amount = D(data['amount'])
    #     if self.settings.test_mode:
    #         balance = amount
    #     else:
    #         balance = self.get_balance(symbol=data['symbol']['base_asset'])
    #         #: never accept balance bigger then current amount
    #         if balance > amount:
    #             balance = amount
    #
    #     self._log('Amount synced with ExA server: {}'.format(balance))
    #
    #     self.exa_server.sync_amount(action_id=data['action_id'], balance=balance)
    #
    # def get_balance(self, symbol):
    #     """
    #     Get balance
    #
    #     :param str symbol: symbol eg. BTC/USDT
    #
    #     """
    #     time.sleep(1)
    #     balance = self.client.fetchBalance()
    #     return D(balance[symbol]['free'])
    #
    # def get_latest_price(self, symbol):
    #     """
    #     Get latest price for symbol
    #
    #     :param dict symbol: symbol data
    #
    #     """
    #     return D(self.client.fetchTicker(symbol['symbol'])['last'])
    #
    # def get_latest_price_usdt(self, symbol):
    #     """
    #     Latest price in USDT
    #
    #     :param dict symbol: symbol data
    #
    #     """
    #     last_price_quote = self.get_latest_price(symbol)
    #
    #     if symbol['quote_asset'] == 'USDT':
    #         usdt_price = last_price_quote
    #     else:
    #         symbol_usdt = {'symbol': '{}/USDT'.format(symbol['quote_asset'])}
    #         latest_price_usdt = self.get_latest_price(symbol_usdt)
    #         usdt_price = last_price_quote * latest_price_usdt
    #
    #     return usdt_price
    #
    #     # return D(str(round(usdt_price, - int(math.floor(math.log10(abs(usdt_price))) - (4 - 1)))))
    #
    # def validate_quantity(self, quantity, symbol):
    #     """
    #     Validate quantity for trading
    #
    #     :param quantity:
    #     :param dict symbol: symbol data
    #
    #     """
    #     try:
    #         decimal_places = len((str(D(symbol['step_size']).normalize())).split('.')[1])
    #     except IndexError:
    #         decimal_places = 0
    #
    #     output = D(floor(quantity * (10 ** decimal_places)) / float(10 ** decimal_places))
    #     return D("{:0.0{}f}".format(float(output), symbol['quote_asset_precision']))
    #
    # def symbol_amount_prec(self, pair, amount: float):
    #     """
    #     Returns the amount to buy or sell to a precision the Exchange accepts
    #     Rounded down
    #     """
    #     if self.client.markets[pair]['precision']['amount']:
    #         symbol_prec = self.client.markets[pair]['precision']['amount']
    #         big_amount = amount * pow(10, symbol_prec)
    #         amount = floor(big_amount) / pow(10, symbol_prec)
    #     return amount
    #
    # def symbol_price_prec(self, pair, price: float):
    #     '''
    #     Returns the price buying or selling with to the precision the Exchange accepts
    #     Rounds up
    #     '''
    #     if self.client.markets[pair]['precision']['price']:
    #         symbol_prec = self.client.markets[pair]['precision']['price']
    #         big_price = price * pow(10, symbol_prec)
    #         price = ceil(big_price) / pow(10, symbol_prec)
    #     return price
    #
    # # def _log(self, message):
    # #     log = SystemLog(message=message)
    # #     db_session.add(log)
    # #     db_session.commit()
    #
    # def _log_transaction(self, action, balance_usdt):
    #     action_log = Transaction(
    #         pair=action['symbol']['symbol'], action_name=action['action'],
    #         amount=D(action['amount']), balance_usdt=balance_usdt)
    #     db_session.add(action_log)
    #     db_session.commit()

