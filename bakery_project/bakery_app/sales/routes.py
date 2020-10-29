import json
import pyodbc
from datetime import datetime
from sqlalchemy import exc, and_, or_, func, select
from sqlalchemy.sql import label
from flask import Blueprint, request, jsonify

from bakery_app import db
from bakery_app._helpers import BaseQuery
from bakery_app.customers.models import Customer
from bakery_app.inventory.models import WhseInv
from bakery_app.branches.models import Series, ObjectType
from bakery_app.users.routes import token_required
from bakery_app._utils import Check, ResponseMessage

from .models import (SalesHeader, SalesRow, SalesType)
from .sales_schema import (SalesHeaderSchema, SalesTypeSchema)

sales = Blueprint('sales', __name__)


@sales.route('/api/sales/new', methods=['POST'])
@token_required
def new_sales(curr_user):
    # check if user sales is true
    if not curr_user.is_sales():
        return ResponseMessage(False, message="Unauthorized user!").resp(), 401

    # get the json data from request body
    data = request.get_json()

    # get the all details from data key rows
    details = data['rows']

    # check if has transdate and convert to datetime object
    if data['header']['transdate']:
        data['header']['transdate'] = datetime.strptime(data['header']['transdate'], '%Y/%m/%d %H:%M')

    # add to header dictionary
    data['header']['created_by'] = curr_user.id
    data['header']['updated_by'] = curr_user.id
    try:
        obj = ObjectType.query.filter_by(code='SLES').first()
        if not obj:
            raise Exception("Invalid object type!")
        series = Series.query.filter_by(whsecode=curr_user.whse, objtype=obj.objtype).first()
        if not series:
            raise Exception("Invalid series!")

        if data['header']['transtype'].upper() == 'CASH':
            cust = db.session.query(Customer). \
                filter(and_(Customer.whse == curr_user.whse, Customer.code.contains('Cash'))).first()
            data['header']['cust_code'] = cust.code
            data['header']['cust_name'] = cust.name

        sales = SalesHeader(**data['header'])
        sales.seriescode = series.code
        sales.transnumber = series.next_num
        sales.reference = series.code + str(series.next_num)
        sales.objtype = obj.objtype
        series.next_num += 1
        db.session.add_all([series, sales])
        db.session.flush()

        for row in details:
            row['whsecode'] = curr_user.whse
            row['sales_id'] = sales.id
            check = Check(**row)
            if not check.itemcode_exist():
                raise Exception("Invalid item code!")
            elif not check.uom_exist():
                raise Exception("Invalid uom!")
            elif not check.whsecode_exist():
                raise Exception("Invalid whsecode!")

            # query the inventory of warehouse
            whseinv = WhseInv.query.filter_by(item_code=row['item_code'], warehouse=row['whsecode']).first()
            # check the quantity
            if row['quantity'] > whseinv.quantity:
                raise Exception(f"{row['item_code'].title()} below qty!")
            s_r = SalesRow(**row)

            # compute gross and discount
            if row['free']:
                s_r.unit_price = 0
            s_r.gross = s_r.unit_price * s_r.quantity
            s_r.disc_amount = s_r.gross * (s_r.discprcnt if row['discprcnt'] else 0 / 100)
            s_r.linetotal = s_r.gross - s_r.disc_amount

            db.session.add(s_r)

        db.session.commit()
        sales_schema = SalesHeaderSchema()
        result = sales_schema.dump(sales)
        return ResponseMessage(True, message="Successfully added!", data=result).resp()
    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        db.session.rollback()
        return ResponseMessage(False, message=f"{err}").resp(), 500
    except Exception as err:
        db.session.rollback()
        return ResponseMessage(False, message=f"{err}").resp(), 500
    finally:
        db.session.close()


# Get all sales
@sales.route('/api/sales/get_all')
@token_required
def get_all_sales(curr_user):
    q = request.args.get('transnum')
    try:
        obj = ObjectType.query.filter_by(code='SLES').first()
        # get series of the user
        series = Series.query.filter_by(whsecode=curr_user.whse, objtype=obj.objtype).first()
        if not series:
            return ResponseMessage(False, message="No series found!").resp(), 401
        if q:
            sales = db.session.query(SalesHeader). \
                filter(and_(SalesHeader.seriescode == series.code,
                            SalesRow.whsecode == curr_user.whse,
                            SalesHeader.void == False,
                            SalesHeader.transnumber == q)).all()
        else:
            sales = db.session.query(SalesHeader). \
                filter(and_(SalesHeader.seriescode == series.code,
                            SalesRow.whsecode == curr_user.whse,
                            SalesHeader.void == False)).all()
        if not sales:
            raise Exception("No record found!")
        sales_schema = SalesHeaderSchema(many=True, exclude=(
            "date_created", "date_updated", "created_by", "updated_by", "salesrow"))
        result = sales_schema.dump(sales)
        return ResponseMessage(True, count=len(result), data=result).resp()
    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500
    except Exception as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500


# Get sales details
@sales.route('/api/sales/details/<int:id>')
@token_required
def get_sales_details(curr_user, id):
    try:
        sales = SalesHeader.query.get(id)
        sales_schema = SalesHeaderSchema()
        result = sales_schema.dump(sales)
        return ResponseMessage(True, data=result).resp()
    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500
    except Exception as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500


# Void Sales
@sales.route('/api/sales/void/<int:id>', methods=['PUT'])
@token_required
def sales_void(curr_user, id):
    void = request.json['void']
    remarks = request.json['remarks']
    if not curr_user.can_void() or not curr_user.is_admin():
        return ResponseMessage(False, message="Unauthorized user!").resp(), 401

    try:
        sales = SalesHeader.query.get(id)
        if not sales:
            raise Exception("Invalid sales id!")
        if sales.void and sales.docstatus != 'O':
            raise Exception("Sales is already closed!")
        sales.void = void
        sales.docstatus = 'N'
        sales.updated_by = curr_user.id
        sales.date_updated = datetime.now()
        if remarks:
            sales.remarks = remarks
        db.session.commit()
        sales_schema = SalesHeaderSchema(
            exclude=("date_created", "date_updated", "created_by", "updated_by", "salesrow"))
        result = sales_schema.dump(sales)
        return ResponseMessage(True, message="Void successfully", data=result).resp()
    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500
    except Exception as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500


# Add New Sales Type
@sales.route('/api/sales/type/new', methods=['POST'])
@token_required
def new_salestype(curr_user):
    if not curr_user.is_admin():
        return ResponseMessage(False, message="Unauthorized user!").resp(), 401

    data = request.get_json()
    if SalesType.query.filter_by(code=data['code']).first():
        return ResponseMessage(False, message="Code already exist!").resp(), 401
    try:
        data['created_by'] = curr_user.id
        data['updated_by'] = curr_user.id
        salestype = SalesType(**data)
        db.session.add(salestype)
        db.session.commit()
        stype_schema = SalesTypeSchema(exclude=("date_created", "date_updated"))
        result = stype_schema.dump(salestype)
        return ResponseMessage(True, message="Successfully added!", data=result).resp()
    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        db.session.rollback()
        return ResponseMessage(False, message=f"{err}").resp(), 500
    except Exception as err:
        db.session.rollback()
        return ResponseMessage(False, message=f"{err}").resp(), 500
    finally:
        db.session.close()
