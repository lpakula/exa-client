"""ExA server support class"""
import os
import logging
import requests
from typing import List

from exceptions import ExAServerException
from models import Pair
from database import db_session
from utils.helpers import get_settings

logger = logging.getLogger(__name__)


class ExAServerHelper(object):
    """Helper to communicate with ExA server"""

    SERVER_URL = os.environ.get('SERVER_URL', 'https://exchangeautomation.com')

    def __init__(self) -> None:
        from __init__ import VERSION
        self.version = VERSION
        self.settings = get_settings()
        self.token = self.settings.exa_token.strip()

    def connect(self, username: str, password: str) -> bool:
        """Connect to  ExA server"""
        response = requests.get(
            f'{self.SERVER_URL}/api/connect/', timeout=7, auth=(username, password))

        if response.status_code == 200:
            self.settings.connected = True
            self.settings.exa_token = response.json()['api_token']
            db_session.commit()
            logger.info('ExA server connected successfully.')
            return True
        else:
            logger.error(f'Connection to ExA server failed. Message: {response.content}')
            return False

    def get_actions(self, exchanges: list) -> List:
        """Get actions to execute for given exchanges"""
        try:
            response = requests.get(
                '{}/api/actions/?exchange={}'.format( self.SERVER_URL, '&exchanges='.join(exchanges)), 
                timeout=7, headers={'Authorization': f'Token {self.token}'})
        except requests.exceptions.Timeout as e:
            logger.warning(f'Server Timeout. Message: {e}')
            return []
        except requests.exceptions.ConnectionError as e:
            logger.error(f'Server Connection Error. Message: {e}')
            return []

        if response.status_code == 200:
            content = response.json()
            return content
        elif response.status_code == 502:
            logger.info('Server Maintenance')
        elif response.status_code in [401, 404]:
            logger.error(f'Incorrect client configuration. Message: {response.content}')
            raise ExAServerException()
        else:
            logger.error(
                f'Error while getting actions from ExA server. Message: {response.content}')
        return []

    def confirm_action(self, action_id: int, status: str, payload: str) -> bool:
        """Confirm action status"""
        payload = {
            'action_id': action_id,
            'status': status,
            'response': f'{payload}',
            'version': self.version
        }

        response = requests.put(
            f'{self.SERVER_URL}/api/actions/', timeout=7, data=payload, 
            headers={'Authorization': f'Token {self.token}'})
        if response.status_code == 200:
            logger.info(f'Action {action_id} confirmed with ExA server.')
            return True
        else:
            logger.error(
                f'Error while connecting to ExA server. If problem persist please contact '
                f'administrator. Message: {response.content}')
            return False

    def sync_amount(self, action_id: int, balance) -> bool:
        """Confirm exact purchased ammount"""
        payload = {
            'action_id': action_id,
            'status': True,
            'response': f'balance: {balance}',
            'balance': balance,
            'version': self.version
        }

        response = requests.put(
            f'{self.SERVER_URL}/api/actions/', timeout=7, data=payload, 
            headers={'Authorization': f'Token {self.token}'})
        if response.status_code == 200:
            logger.info(f'Amount synced with ExA server {balance}')
            return True
        else:
            logger.error(
                f'Error while connecting to ExA server. If problem persist please contact '
                f'administrator. Message: {response.content}')
            return False

    # def send_logs(self) -> bool:
    #     """Send system logs"""
    #     log_messages = [f'client: {self.version}']
    #     logs = SystemLog.query.all()
    #     for log in logs:
    #         log_messages.append(f'{log.created}: {log.message}')
    #
    #     response = requests.post(
    #         f'{self.SERVER_URL}/api/client/logs/', timeout=7, data={'logs': f'{log_messages}'},
    #         headers={'Authorization': f'Token {self.token}'})
    #     if response.status_code == 200:
    #         logger.info('Logs sent successfully')
    #         SystemLog.query.delete()
    #         db_session.commit()
    #         return True
    #     else:
    #         logger.error(f'Sending logs failed. Message: {response.content}')
    #         return False

    def sync_symbols(self) -> None:
        """Fetch supported symbols"""
        response = requests.get(
            f'{self.SERVER_URL}/api/symbols/', timeout=7, 
            headers={'Authorization': f'Token {self.token}'})

        if response.status_code == 200:
            logger.info('Symbols synced successfully')
            for item in response.json():
                symbol = Pair.query.filter_by(name=item).first()
                if not symbol:
                    db_session.add(Pair(name=item))
            db_session.commit()
        else:
            logger.error(f'Sync symbols failed. Message: {response.content}')
