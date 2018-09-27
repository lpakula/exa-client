from functools import wraps
from flask import redirect, url_for, g
from utils.helpers import get_settings


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
        settings = get_settings()
        if not settings.connected and False:
            return redirect(url_for('connect'))
        return f(*args, **kwargs)
    return decorated_function


