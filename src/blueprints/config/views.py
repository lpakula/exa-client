from flask import render_template, flash, request, redirect, url_for

from db import db_session
from utils.auth import connect_required
from utils.database import get_config

from . import bp
from .forms import ConfigForm


@bp.route("/", methods=['GET', 'POST'])
@connect_required
def index():
    config = get_config
    pair_choices = []

    form = ConfigForm(obj=config)
    form.allowed_pairs.choices = pair_choices
    if request.method == 'POST':
        form = ConfigForm(request.form)
        form.allowed_pairs.choices = pair_choices
        if form.validate():
            config.allowed_pairs = form.allowed_pairs.data
            config.allowed_balance = form.allowed_balance.data
            db_session.commit()
            flash('Config have been updated.', 'success')
            return redirect(url_for('dashboard.index'))

    return render_template('config/edit.html', form=form)

# @bp.route("/logs/send")
# @connect_required
# def logs_send():
#     log_entries = SystemLog.query.order_by(desc(SystemLog.created)).all()
#     if log_entries:
#         status = ExAServerHelper(version=VERSION).send_logs()
#         if status:
#             flash('Logs have been sent successfully.', 'success')
#         else:
#             flash('Logs have not been sent. If problem persists please contact administrator.',
#                   'danger')
#     else:
#         flash('No logs to send.', 'warning')
#     return redirect(url_for('logs'))
