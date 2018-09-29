from wtforms import Form, BooleanField, StringField, validators


class ExchangeForm(Form):
    """Exchange Form"""
    enabled = BooleanField('Enabled', default=True)
    api_key = StringField('API Key', validators=[validators.DataRequired()])
    api_secret = StringField('API Secret', validators=[validators.DataRequired()])
