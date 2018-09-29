from wtforms import Form, FloatField, SelectMultipleField, validators


class ConfigForm(Form):
    """Config form"""
    allowed_pairs = SelectMultipleField(choices=[])
    allowed_balance = FloatField('Allowed Buy Balance', validators=(validators.Optional(),))
