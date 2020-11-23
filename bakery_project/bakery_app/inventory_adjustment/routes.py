import pyodbc

from datetime import datetime
from flask import Blueprint, request
from sqlalchemy import exc, and_, or_, DATE, func

from bakery_app import db
from bakery_app._utils import Check, ResponseMessage
from bakery_app._helpers import BaseQuery
from bakery_app.users.models import User
from bakery_app.branches.models import Series, ObjectType, Warehouses
from bakery_app.users.routes import token_required
from bakery_app.items.models import PriceListRow, Items

from .models import (ItemAdjustmentIn, ItemAdjustmentInRow, ItemAdjustmentOut, ItemAdjustmentOutRow)


inventory_adjustment = Blueprint('inventory_adjustment', __name__, url_prefix='/api/inv_adj')

