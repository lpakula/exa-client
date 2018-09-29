from flask import render_template, flash,  redirect, url_for
from sqlalchemy import desc

from db import db_session
from models import Log
from utils.auth import connect_required

from . import bp


@bp.route("/")
@connect_required
def index():
    logs = Log.query.order_by(desc(Log.id)).all()
    return render_template('logs/index.html', logs=logs)


@bp.route("/delete")
@connect_required
def delete():
    Log.query.delete()
    db_session.commit()
    flash('Logs have been deleted.', 'success')
    return redirect(url_for('logs.index'))
