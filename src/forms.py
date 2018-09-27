#!/usr/bin/python
# -*- coding: utf-8 -*-
from wtforms import Form, BooleanField, FloatField, StringField, SelectMultipleField, validators, \
    PasswordField


ACTION_CHOICES = (
    ('order_limit_buy', 'order_limit_buy'),
    ('order_limit_sell', 'order_limit_sell')
)


class ConnectForm(Form):
    username = StringField('Username', validators=[validators.DataRequired()])
    password = PasswordField('Passsword', validators=[validators.DataRequired()])


class SettingsForm(Form):
    """
    Settings Form
    """
    allowed_pairs = SelectMultipleField(choices=[])
    allowed_balance = FloatField('Allowed Buy Balance', default=0, validators=(validators.Optional(),))


class ExchangeForm(Form):
    """
    Exchange Form
    """
    enabled = BooleanField('Enabled', default=True)
    api_key = StringField('API Key', validators=[validators.DataRequired()])
    api_secret = StringField('API Secret', validators=[validators.DataRequired()])


