from functools import wraps
from flask import redirect, url_for, g
from utils.database import get_server


def login_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for('auth.login'))
        return view(**kwargs)
    return wrapped_view


def connect_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not get_server().connected:
            return redirect(url_for('auth.connect'))
        return f(*args, **kwargs)
    return decorated_function


