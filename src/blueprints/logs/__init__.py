from flask import Blueprint
bp = Blueprint('logs', __name__, url_prefix='/logs')
from .views import *
