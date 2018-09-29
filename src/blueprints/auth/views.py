from flask import render_template, flash, request, redirect, url_for

from utils.database import get_server
from utils.server import ExAServerHelper
from models import Log

from . import bp
from .forms import ConnectForm


@bp.route("/", methods=['GET', 'POST'])
def connect():
    server = get_server()
    if server.connected:
        return redirect(url_for('dashboard.index'))
    if request.method == 'POST':
        form = ConnectForm(request.form)
        if form.validate():
            status = ExAServerHelper().connect(
                username=form.username.data, password=form.password.data)
            if status:
                flash('You have been connected with the server successfully.', 'success')
                return redirect(url_for('dashboard.index'))
            else:
                log = Log.query.first()
                flash(f'You can\'t connect to the server with provided details. '
                      f'<br><b>Message</b>: {log.msg}', 'danger')
    form = ConnectForm()
    return render_template('auth/connect.html', form=form)
