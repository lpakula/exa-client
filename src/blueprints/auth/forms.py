from wtforms import Form, StringField, validators, PasswordField


class ConnectForm(Form):
    username = StringField('Username', validators=[validators.DataRequired()])
    password = PasswordField('Passsword', validators=[validators.DataRequired()])
