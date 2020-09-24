from flask import Blueprint
from bakery_app.users.models import Users

users = Blueprint('users', __name__)