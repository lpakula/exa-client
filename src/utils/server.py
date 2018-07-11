#!/usr/bin/python
# -*- coding: utf-8 -*-
import os
import requests

from exceptions import ExAServerException
from models import SystemLog, Settings, Symbol
from database import db_session


class ExAServerHelper(object):
    """
    ExA Server communication helper
    """

    SERVER_URL = os.environ.get('SERVER_URL', 'https://exchangeautomation.com')

    def __init__(self, version):
        self.version = version
        self.settings = Settings.query.get(1)

    def log(self, message):
        log = SystemLog(message=message)
        db_session.add(log)
        db_session.commit()

    def connect(self, username, password):
        """
        Connect to  ExA server

        """
        response = requests.get(
           '{}/api/connect/'.format(self.SERVER_URL), timeout=7, auth=(username, password))

        if response.status_code == 200:
            self.settings.connected = True
            self.settings.exa_token = response.json()['api_token']
            db_session.commit()
            self.log('ExA server is connected')
            return True
        else:
            self.log('ExA server connection failed: {}'.format(response.content))
            return False

    def get_actions(self, exchanges):
        """
        Get actions for exchanges

        """
        try:
            response = requests.get('{}/api/actions/?exchange={}'.format(
                self.SERVER_URL, '&exchanges='.join(exchanges)), timeout=7,
                headers={'Authorization': 'Token {}'.format(self.settings.exa_token.strip())})
        except requests.exceptions.Timeout:
            self.log(message='Server Timeout')
            return []
        except requests.exceptions.ConnectionError:
            self.log(message='Server Connection Error')
            return []

        if response.status_code == 200:
            content = response.json()
            return content
        elif response.status_code == 502:
            self.log(message='Server Maintenance')
        elif response.status_code in [401, 404]:
            raise ExAServerException('Wrong client configuration. Exception: {}'.format(
                response.content))
        else:
            self.log(
                'Error while getting actions from ExA server. Exception: {}'.format(
                    response.content))
        return []

    def confirm_action(self, action_id, status, response):
        """
        Confirm action execution on ExA server

        """
        payload = {
            'action_id': action_id,
            'status': status,
            'response': str(response),
            'version': self.version
        }
        response = requests.put(
            '{}/api/actions/'.format(self.SERVER_URL),
            timeout=7, data=payload, headers={'Authorization': 'Token {}'.format(
                self.settings.exa_token.strip())})
        if response.status_code != 200:
            raise ExAServerException(
                'Error while connecting to ExA server. If problem persist please contact '
                'administrator. Response: {}'.format(response.content))

    def sync_amount(self, action_id, balance):
        """
        Confirm sync_amount action on ExA server

        """
        payload = {
            'action_id': action_id,
            'status': True,
            'response': 'Balance: {}'.format(balance),
            'balance': balance
        }

        response = requests.put(
            '{}/api/actions/'.format(self.SERVER_URL), timeout=7, data=payload,
            headers={'Authorization': 'Token {}'.format(self.settings.exa_token.strip())})
        if response.status_code != 200:
            raise ExAServerException(
                'Error while connecting to ExA server. If problem persist please contact '
                'administrator. Response: {}'.format(response.content))

    def send_logs(self):
        """
        Send logs to ExA server

        """
        log_messages = ['client: {}'.format(self.version)]
        logs = SystemLog.query.all()
        for log in logs:
            log_messages.append('{}: {}'.format(log.created, log.message))

        response = requests.post('{}/api/client/logs/'.format(
            self.SERVER_URL), timeout=7, data={'logs': str(log_messages)},
            headers={'Authorization': 'Token {}'.format(self.settings.exa_token.strip())})
        if response.status_code == 200:
            SystemLog.query.delete()
            db_session.commit()
            return True
        else:
            self.log(message='Send logs failed: {}'.format(response.content))
            return False

    def sync_symbols(self):
        response = requests.get('{}/api/symbols/'.format(
            self.SERVER_URL), timeout=7,
            headers={'Authorization': 'Token {}'.format(self.settings.exa_token.strip())})

        if response.status_code == 200:
            for item in response.json():
                symbol = Symbol.query.filter_by(name=item).first()
                if not symbol:
                    db_session.add(Symbol(name=item))
            db_session.commit()
        else:
            self.log(message='Sync symbols failed: {}'.format(response.content))

