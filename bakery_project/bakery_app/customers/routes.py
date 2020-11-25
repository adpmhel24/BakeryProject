import pyodbc
from datetime import datetime
from sqlalchemy import exc
from flask import Blueprint, request, jsonify
from bakery_app import db, auth
from bakery_app._helpers import BaseQuery
from bakery_app._utils import ResponseMessage
from bakery_app.users.routes import token_required

from .models import Customer, CustomerType
from .customers_schema import CustomerSchema, CustTypeSchema

customers = Blueprint('customers', __name__)


@customers.route('/api/customer/new', methods=['POST'])
@token_required
def create_customer(curr_user):
    if not curr_user.is_admin():
        return jsonify({"success": "false", "message": "You're not authorized!"}), 400

    data = request.get_json()
    data['created_by'] = curr_user.id
    data['updated_by'] = curr_user.id
    if Customer.query.filter_by(code=data['code']).first() or \
            Customer.query.filter_by(code=data['code'], whse=data['whse']).first():
        return ResponseMessage(False, message="Customer code already exist!").resp(), 400

    try:
        cust = Customer(**data)
        db.session.add(cust)
        db.session.commit()
        cust_schema = CustomerSchema()
        result = cust_schema.dump(cust)
        return ResponseMessage(True, message="Successfully added!", data=result).resp()
    except Exception as err:
        db.session.rollback()
        return ResponseMessage(False, message=f"{err}").resp(), 500
    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        db.session.rollback()
        return ResponseMessage(False, message=f"{err}").resp(), 500
    finally:
        db.session.close()


@customers.route('/api/customer/get_all')
@token_required
def get_all_customer(curr_user):
    try:
        data = request.args.to_dict()
        if 'transtype' in data:
            if data['transtype'].upper() == 'SALES':
                filt = []
                filt_cust_type = []
                # add to filter list if the user is allow to cash sales
                if curr_user.is_sales() and curr_user.is_cash_sales() and not curr_user.is_ar_sales():
                    filt.append(('whse', '==', curr_user.whse))
                    filt_cust_type.append(3) # Customer Type Cash Sales
                    
                # add to filter list if the user is allow to agent sales
                if curr_user.is_sales() and curr_user.is_agent_sales() and not curr_user.is_ar_sales():
                    filt.append(('whse', '==', curr_user.whse))
                    filt_cust_type.append(4) # Customer Type Agent AR Sales

                # add to filter list if the user is allow to ar sales
                if curr_user.is_sales() and curr_user.is_ar_sales():
                    filt_cust_type.append(1) # Customer Type Customers
                
                if filt_cust_type:
                    filt.append(('cust_type', 'in', filt_cust_type))

                cust_filter = BaseQuery.create_query_filter(Customer, filters={'and': filt})
                customers = db.session.query(Customer).filter(*cust_filter).all()
        else:
            customers = db.session.query(Customer).all()
        cust_schema = CustomerSchema(many=True)
        result = cust_schema.dump(customers)
        return ResponseMessage(True, count=len(result), data=result).resp()

    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500
    except Exception as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500


# Create Customer Type
@customers.route('/api/custtype/new', methods=['POST'])
@token_required
def create_custtype(curr_user):
    if not curr_user.is_admin():
        return ResponseMessage(False, message="Unauthorized user!"), 401

    data = request.get_json()
    data['created_by'] = curr_user.id
    data['updated_by'] = curr_user.id

    if CustomerType.query.filter_by(code=data['code']).first():
        return ResponseMessage(False, message="Code already exist!").resp(), 401

    try:
        custtype = CustomerType(**data)
        db.session.add(custtype)
        db.session.commit()

        custype_schema = CustTypeSchema()
        result = custype_schema.dump(custtype)
        return ResponseMessage(True, message="Successfully added!", data=result).resp()

    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        db.session.rollback()
        return ResponseMessage(False, message=f"{err}").resp(), 500
    except Exception as err:
        db.session.rollback()
        return ResponseMessage(False, message=f"{err}").resp(), 500
    finally:
        db.session.close()


# Get All Customer Type
@customers.route('/api/custtype/get_all')
@token_required
def get_all_custtype(curr_user):
    try:
        cust_type = CustomerType.query.all()
        custtype_schema = CustTypeSchema(many=True)
        result = custtype_schema.dump(cust_type)
        return ResponseMessage(True, data=result).resp()
    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500
    except Exception as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500
