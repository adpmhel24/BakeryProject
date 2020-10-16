import pyodbc
from datetime import datetime
from sqlalchemy import exc
from flask import Blueprint, request, jsonify
from bakery_app import db, auth
from bakery_app.customers.models import (Customer, CustomerType, CustomerSchema, CustTypeSchema)
from bakery_app._utils import status_response, ResponseMessage
from bakery_app.users.routes import token_required

customers = Blueprint('customers', __name__)


@customers.route('/api/customer/new', methods=['POST'])
@token_required
def create_customer(curr_user):
    if not curr_user.is_admin():
        return jsonify({"success": "false", "message": "You're not authorized!"})
    
    data = request.get_json()
    data['created_by'] = curr_user.id
    data['updated_by'] = curr_user.id
    if Customer.query.filter_by(code=data['code']).first() or \
        Customer.query.filter_by(code=data['code'], whse=data['whse']).first():
        return ResponseMessage(False, message="Customer code already exist!").resp()

    try:
        cust = Customer(**data)
        db.session.add(cust)
        db.session.commit()
        cust_schema = CustomerSchema(exclude=("date_created", "date_updated",\
                "created_by", "updated_by"))
        result = cust_schema.dump(cust)
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


@customers.route('/api/custype/new', methods=['POST'])
@token_required
def create_custtype(curr_user):
    if not curr_user.is_admin():
        return jsonify({"success": "false", "message": "You're not authorized!"})

    data = request.get_json()
    data['created_by'] = curr_user.id
    data['updated_by'] = curr_user.id

    if CustomerType.query.filter_by(code=data['code']).first():
        return ResponseMessage(False, message="Code already exist!").resp()

    try:
        custtype = CustomerType(**data)
        db.session.add(custtype)
        db.session.commit()

        custype_schema = CustTypeSchema(exclude=("date_created", "date_updated",\
                "created_by", "updated_by"))
        result = custype_schema.dump(custtype)
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