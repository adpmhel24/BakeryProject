import json
import pyodbc
from datetime import datetime
from sqlalchemy import exc, and_, or_
from flask import Blueprint, request, jsonify
from bakery_app import db, auth
from bakery_app.sales.models import (SalesHeader, SalesRow, SalesType, SalesHeaderSchema, SalesTypeSchema)
from bakery_app.customers.models import Customer
from bakery_app.inventory.models import InvTransaction, WhseInv
from bakery_app.branches.models import Branch, Series, ObjectType
from bakery_app.users.routes import token_required
from bakery_app._utils import Check, ResponseMessage



sales = Blueprint('sales', __name__)


@sales.route('/api/sales/new', methods=['POST'])
@token_required
def new_sales(curr_user):

    data = request.get_json()
    data['header']['created_by'] = curr_user.id
    data['header']['updated_by'] = curr_user.id

    details = data['rows']
    
    if data['header']['transdate']:
        data['header']['transdate'] = datetime.strptime(data['header']['transdate'], '%Y/%m/%d %H:%M')

    try:
        obj = ObjectType.query.filter_by(code='SLES').first()
        if not obj:
            raise Exception("Invalid object type!")
        series = Series.query.filter_by(whsecode=curr_user.whse, \
            objtype=obj.objtype).first()
        if not series:
            raise Exception("Invalid series!")
        sales = SalesHeader(**data['header'])
        sales.seriescode = series.code
        sales.transnumber = series.next_num
        sales.reference = series.code + str(series.next_num)
        sales.objtype = obj.objtype
        series.next_num += 1
        db.session.add_all([series , sales])
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

            whseinv = WhseInv.query.filter_by(item_code=row['item_code'], warehouse=row['whsecode']).first()
            if row['quantity'] > whseinv.quantity:
                raise Exception("Insufficient stock!")
            s_r = SalesRow(**row)

            # compute gross and discount
            if row['free']:
                s_r.unit_price = 0
            s_r.gross = s_r.unit_price * s_r.quantity
            s_r.disc_amount =  s_r.gross * (s_r.discprcnt if row['discprcnt'] else 0 / 100)
            s_r.linetotal = s_r.gross - s_r.disc_amount

            db.session.add(s_r)
            
        db.session.commit()
        sales_schema = SalesHeaderSchema()
        result = sales_schema.dump(sales)
        return ResponseMessage(True, message="Successfully added!", data=result).resp()
    except Exception as err:
        db.session.rollback()
        return ResponseMessage(False, message=f"{err}").resp()
    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        db.session.rollback()
        return ResponseMessage(False, message=f"{err}").resp()
    except:
        db.session.rollback()
        return ResponseMessage(False, message=f"Unknown error!").resp()
    finally:
        db.session.close()
        

@sales.route('/api/sales/type/new', methods=['POST'])
@token_required
def new_salestype(curr_user):
    if not curr_user.is_admin():
        return ResponseMessage(False, message="Unathorized user!").resp()
    
    data = request.get_json()
    if SalesType.query.filter_by(code=data['code']).first():
        return ResponseMessage(False, message="Code already exist!").resp()
    try:
        data['created_by'] = curr_user.id
        data['updated_by'] = curr_user.id
        salestype = SalesType(**data)
        db.session.add(salestype)
        db.session.commit()
        stype_schema = SalesTypeSchema(exclude=("date_created", "date_updated"))
        result = stype_schema.dump(salestype)
        return ResponseMessage(True, message="Successfully added!", data=result).resp()
    except Exception as err:
        db.session.rollback()
        return ResponseMessage(False, message=f"{err}").resp()
    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        db.session.rollback()
        return ResponseMessage(False, message=f"{err}").resp()
    except:
        db.session.rollback()
        return ResponseMessage(False, message="Unknown error!").resp()
    finally:
        db.session.close()

@sales.route('/api/sales/getall')
@token_required
def get_all_sales(curr_user):

    q = request.args.get('transnum')  
    try:
        obj = ObjectType.query.filter_by(code='SLES').first()
        # check if has object
        if not obj:
            raise Exception("Invalid object type!")
        # get series of the user
        series = Series.query.filter_by(whsecode=curr_user.whse, \
            objtype=obj.objtype).first()
        if q:
            sales = db.session.query(SalesHeader).\
                filter(and_(SalesHeader.seriescode==series.code,\
                        SalesRow.whsecode==curr_user.whse,\
                        SalesHeader.void==False, \
                        SalesHeader.transnumber==q)).all()
        else:
            sales = db.session.query(SalesHeader).\
                filter(and_(SalesHeader.seriescode==series.code,\
                        SalesRow.whsecode==curr_user.whse,\
                        SalesHeader.void==False)).all()
        if not sales:
            raise Exception("No record found!")
        sales_schema = SalesHeaderSchema(many=True, exclude=("date_created", "date_updated", "created_by", "updated_by", "salesrow"))
        result = sales_schema.dump(sales)
        return ResponseMessage(True, data=result).resp()
    except Exception as err:
        return ResponseMessage(False, message=f"{err}").resp()
    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        return ResponseMessage(False, message=f"{err}").resp()
    except:
        return ResponseMessage(False, message="Unknown error!").resp()

@sales.route('/api/sales/getdetails/<int:id>')
@token_required
def get_sales_details(curr_user, id):

    try:
        sales = SalesHeader.query.get(id)
        if not sales:
            raise Exception("Invalid sales id!")
        
        sales_schema = SalesHeaderSchema()
        result = sales_schema.dump(sales)
        return ResponseMessage(True, data=result).resp()
    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        return ResponseMessage(False, message=f"{err}").resp()
    except Exception as err:
        return ResponseMessage(False, message=f"{err}").resp()
    except:
        return ResponseMessage(False, message="Unknown error!").resp()

@sales.route('/api/sales/void/<int:id>', methods=['PUT'])
@token_required
def sales_void(curr_user, id):
    
    void = request.json['void']
    remarks = request.json['remarks']
    if not curr_user.can_void() or not curr_user.is_admin():
        return ResponseMessage(False, message="Unathorized user!").resp()

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
        db.session.commit()
        sales_schema = SalesHeaderSchema(exclude=("date_created", \
            "date_updated", "created_by", "updated_by", "salesrow"))
        result = sales_schema.dump(sales)
        return ResponseMessage(True, message="Void successfully", data=result).resp()
    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        return ResponseMessage(False, message=f"{err}").resp()
    except Exception as err:
        return ResponseMessage(False, message=f"{err}").resp()
    except:
        return ResponseMessage(False, message="Unknown error!").resp()






