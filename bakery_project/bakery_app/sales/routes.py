import json
import pyodbc
from datetime import datetime
from sqlalchemy import exc, and_, or_, func, select, cast, DATE
from sqlalchemy.sql import label
from flask import Blueprint, request, jsonify

from bakery_app import db
from bakery_app._helpers import BaseQuery
from bakery_app.customers.models import Customer
from bakery_app.inventory.models import WhseInv
from bakery_app.branches.models import Series, ObjectType, Warehouses
from bakery_app.users.routes import token_required
from bakery_app._utils import Check, ResponseMessage

from .models import (SalesHeader, SalesRow, SalesType, DiscountType)
from .sales_schema import (SalesHeaderSchema, SalesTypeSchema, DiscountTypeSchema, SalesRowSchema)

sales = Blueprint('sales', __name__)


# Create New Sales
@sales.route('/api/sales/new', methods=['POST'])
@token_required
def new_sales(curr_user):
    # check if user sales is true
    if not curr_user.is_sales():
        return ResponseMessage(False, message="Unauthorized user!").resp(), 401

    # query the whse and check if cutoff is enable
    whse = Warehouses.query.filter_by(whsecode=curr_user.whse).first()
    if whse.is_cutoff():
        return ResponseMessage(False, message="Your warehouse cutoff is enable!").resp(), 401

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

        # check if the header has discount and user is allowed to add discount
        if data['header']['discprcnt'] and not curr_user.can_discount():
            raise Exception("You're not allowed to add discount!")
        
        # add 1 to series
        series.next_num += 1

        sales = SalesHeader(**data['header'])
        sales.seriescode = series.code
        sales.transnumber = series.next_num
        sales.reference = f"{series.code}-{obj.code}-{series.next_num}"
        sales.objtype = obj.objtype
        
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

            # check if the row has discount and if user is allowed to add discount
            if row['discprcnt'] and not curr_user.can_discount():
                raise Exception("You're not allowed to add sales with discount!")

            # query the inventory of warehouse
            whseinv = WhseInv.query.filter_by(item_code=row['item_code'], warehouse=row['whsecode']).first()
            # check the quantity
            if row['quantity'] > whseinv.quantity:
                raise Exception(f"{row['item_code'].title()} below qty!")

            if row['free']:
                row['unit_price'] = 0
            # add to row the computation
            row['gross'] = row['unit_price'] * row['quantity']
            row['disc_amount'] = row['gross'] * (row['discprcnt']/100 if row['discprcnt'] else 0 / 100)
            row['linetotal'] = row['gross'] - row['disc_amount']

            s_r = SalesRow(**row)

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
@sales.route('/api/sales/void', methods=['PUT'])
@token_required
def sales_void(curr_user):
    remarks = request.args.get('remarks')
    if not curr_user.can_void() or not curr_user.is_admin():
        return ResponseMessage(False, message="Unauthorized user!").resp(), 401

    # query the whse and check if cutoff is enable
    whse = Warehouses.query.filter_by(whsecode=curr_user.whse).first()
    if whse.is_cutoff():
        return ResponseMessage(False, message="Your warehouse cutoff is enable!").resp(), 401

    try:
        ids = request.args.get('ids').rstrip(']').lstrip('[')
        ids = list(ids.split(','))
        filt_sales_h = [('id', 'in', ids)]
        sales_filt = BaseQuery.create_query_filter(SalesHeader, filters={'and': filt_sales_h})
        sales = SalesHeader.query.filter(*sales_filt).all()
        success_ref = []
        unsuccess_ref = []
        for sale in sales:
            if sale.docstatus == 'C':
                unsuccess_ref.append(sale.id)
                continue
            if sale.docstatus == 'N':
                unsuccess_ref.append(sale.reference)
                continue
            sale.void = True
            sale.docstatus = 'N'
            sale.updated_by = curr_user.id
            sale.date_updated = datetime.now()
            if remarks:
                sale.remarks = remarks
            success_ref.append(sale.reference)
            db.session.commit()

        success_message = f"Void success transaction: {str(success_ref).rstrip(']').lstrip('[')}"
        unsuccess_message = f"Void unsuccess transaction: {str(unsuccess_ref).rstrip(']').lstrip('[')}"

        return ResponseMessage(True, message=f"{success_message}" if len(success_ref) > 0 else '' \
                                    f" ,{unsuccess_message}" if len(unsuccess_ref) > 0 else '' + '.').resp()
    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500
    except Exception as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500



# GET AR Sales for confirm
@sales.route('/api/sales/for_confirm')
@token_required
def ar_for_confirm(curr_user):
    if not curr_user.is_manager() and not curr_user.is_cashier() and not curr_user.is_admin():
        return ResponseMessage(False, message="Unauthorized user!").resp(), 401

    try:
        filt = []
        transnum = request.args.get('transnum')
        user_id = request.args.get('user_id')
        transtype = request.args.get('transtype')
        date_created = request.args.get('date_created')

        if transnum:
            filt.append(('transnumber', 'like', f'%{transnum}%'))

        if user_id:
            filt.append(('created_by', '==', user_id))

        if transtype:
            filt.append(('transtype', '==', transtype))
        filt.append(('docstatus', '==', 'O'))

        sales_filter = BaseQuery.create_query_filter(
            SalesHeader, filters={'and': filt})

        if date_created:
            sales = db.session.query(SalesHeader).join(SalesRow). \
                join(Warehouses, Warehouses.whsecode == SalesRow.whsecode).filter(and_(Warehouses.branch == curr_user.branch,
                            func.cast(SalesHeader.date_created, DATE) == date_created,
                            and_(SalesHeader.confirm != True, SalesHeader.transtype !='CASH'),
                            *sales_filter)).all()
        else:
            sales = db.session.query(SalesHeader).join(SalesRow). \
                join(Warehouses, Warehouses.whsecode == SalesRow.whsecode)\
                    .filter(and_(Warehouses.branch == curr_user.branch,
                            and_(SalesHeader.confirm != True, SalesHeader.transtype !='CASH'),
                            *sales_filter)).all()

        sales_schema = SalesHeaderSchema(many=True, only=("id", "docstatus", "seriescode",
                                                            "transnumber", "reference", "transdate", "cust_code",
                                                            "cust_name", "objtype", "remarks", "transtype", "delfee",
                                                            "disctype", "discprcnt", "disc_amount", "gross",
                                                            "gc_amount", "doctotal", "reference2", "tenderamt",
                                                            "sap_number", "appliedamt", "amount_due", "void", "created_user", "confirm"))
        result = sales_schema.dump(sales)
        return ResponseMessage(True, count=len(result), data=result).resp()
    
    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500
    except Exception as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500


# Confirm AR Sales
@sales.route('/api/sales/confirm', methods=['PUT'])
@token_required
def ar_confirm(curr_user):
    if not curr_user.is_cashier() and not curr_user.is_admin() and not curr_user.is_manager():
        return ResponseMessage(False, message="Unauthorized user!").resp(), 401

    try:
        ids = request.args.get('ids').rstrip(']').lstrip('[')
        ids = list(ids.split(','))
        filt_sales_h = [('id', 'in', ids)]
        sales_filt = BaseQuery.create_query_filter(SalesHeader, filters={'and': filt_sales_h})
        sales = SalesHeader.query.filter(*sales_filt).all()
        success_ref = []
        unsuccess_ref= []
        for sale in sales:
            if sale.confirm:
                unsuccess_ref.append(sale.reference)
                continue
            sale.confirm = True
            sale.confirm_by = curr_user.id
            sale.date_confirm = datetime.now()
            success_ref.append(sale.reference)
            db.session.commit()

        success_message = f"Confirm success transaction: {str(success_ref).rstrip(']').lstrip('[')}"
        unsuccess_message = f"Confirm unsuccess transaction: {str(unsuccess_ref).rstrip(']').lstrip('[')}"

        return ResponseMessage(True, message=f"{success_message}" if len(success_ref) > 0 else '' \
                                    f" ,{unsuccess_message}" if len(unsuccess_ref) > 0 else '' + '.').resp()

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


# Get All Sales Type
@sales.route('/api/sales/type/get_all')
@token_required
def get_all_sales_type(curr_user):
    try:
        data = request.args.to_dict()
        filt = []
        filt_in = []
       
        for k, v in data.items():
            filt.append((k, '==', v))

        if curr_user.is_sales():
            if curr_user.is_ar_sales():
                filt_in.append('AR Sales')
            if curr_user.is_cash_sales():
                filt_in.append('CASH')
            if curr_user.is_agent_sales():
                filt_in.append('Agent AR Sales')
        if not curr_user.is_admin() and not curr_user.is_manager() and not curr_user.is_cashier():
            filt.append(('code', 'in', filt_in))
        sales_filter = BaseQuery.create_query_filter(SalesType, filters={'and': filt})
        stype = db.session.query(SalesType).filter(*sales_filter).all()
        stype_schema = SalesTypeSchema(many=True)
        result = stype_schema.dump(stype)
        print(curr_user.username)
        print(curr_user.is_ar_sales())
        print(filt_in)
        print(filt)
        return ResponseMessage(True, data=result).resp()
    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500
    except Exception as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500


# Create Discount Type
@sales.route('/api/disc_type/new', methods=['POST'])
@token_required
def new_discount_type(curr_user):
    if not curr_user.is_admin():
        return ResponseMessage(False, message="Unauthorized user!").resp(), 401
    
    try:
        data = request.get_json()
        
        # add to data
        data['created_by'] = curr_user.id
        data['updated_by'] = curr_user.id

        disc_type = DiscountType(**data)
        db.session.add(disc_type)
        db.session.commit()

        disc_type_schema = DiscountTypeSchema(only=("id", "code","description", "discount"))
        result = disc_type_schema.dump(disc_type)
        return ResponseMessage(True, message=f"Successfully added!", data=result).resp()

    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500
    except Exception as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500



# Get All Discount Type
@sales.route('/api/disc_type/get_all')
@token_required
def get_all_discount_type(curr_user):
    try:
        q = request.args.get('search')
        filt = []
        if q:
            filt.append(('code', 'like', f'%{q}%'))

        query_filter = BaseQuery.create_query_filter(DiscountType, filters={'and': filt})
        query = DiscountType.query.filter(*query_filter).all()
        disc_type_schema = DiscountTypeSchema(many=True, only=("id", "code","description", "discount"))
        result = disc_type_schema.dump(query)
        return ResponseMessage(True, message=f"Successfully added!", data=result).resp()
    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500
    except Exception as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500


# Get Discount Details
@sales.route('/api/disc_type/details/<int:id>')
@token_required
def get_disc_type_details(curr_user, id):
    try:
        query = DiscountType.query.get(id)
        if not query:
            raise Exception("Invalid discount id!")

        disc_type_schema = DiscountTypeSchema(only=("id", "code","description", "discount"))
        result = disc_type_schema.dump(query)
        return ResponseMessage(True, message=f"Successfully added!", data=result).resp()

    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500
    except Exception as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500