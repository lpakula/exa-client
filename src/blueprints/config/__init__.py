from flask import Blueprint
bp = Blueprint('config', __name__, url_prefix='/config')
from .views import *
