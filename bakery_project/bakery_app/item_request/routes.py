import pyodbc

from datetime import datetime
from flask import Blueprint, request
from sqlalchemy import exc, and_, or_, DATE, func
from bakery_app import db
from bakery_app._utils import Check, ResponseMessage
from bakery_app._helpers import BaseQuery
from bakery_app.branches.models import Series, ObjectType, Warehouses
from bakery_app.users.routes import token_required

from .models import ItemRequestRow, ItemRequest
from .item_req_schema import ItemRequestRowSchema, ItemRequestSchema

item_request = Blueprint('item_request', __name__, url_prefix='/api/inv/item_request/')

# Create New Item Request
@item_request.route('/new', methods=['POST'])
@token_required
def create_item_request(curr_user):
    try:
        data = request.get_json()
        header = data['header']
        details = data['rows']
        obj = ObjectType.query.filter_by(code='REQT').first()
        series = Series.query.filter_by(
            whsecode=curr_user.whse, objtype=obj.objtype).first()
        if series.next_num + 1 > series.end_num:
            raise Exception("Series number already in max!")
        if not series:
            raise Exception("Invalid Series")

        reference = f"{series.code}-{obj.code}-{series.next_num}"
        req_header = ItemRequest(series=series.id, seriescode=series.code,
                                 transnumber=series.next_num, reference=reference,
                                 objtype=obj.objtype, **header)
        req_header.created_by = curr_user.id
        req_header.updated_by = curr_user.id

        # add 1 to next num series
        series.next_num += 1

        db.session.add_all([req_header, series])
        db.session.flush()

        for row in details:
            # add user whse to row
            row['to_whse'] = curr_user.whse

            check = Check(**row)
            # check if valid
            if not check.itemcode_exist():
                raise Exception("Invalid item code!")
            elif not check.uom_exist():
                raise Exception("Invalid uom!")
            elif not check.fromwhse_exist():
                raise Exception("Invalid from whse code!")
            elif not check.towhse_exist():
                raise Exception("Invalid to whse code!")

            req_row = ItemRequestRow(request_id=req_header.id, objtype=req_header.objtype,
                                     created_by=req_header.created_by,
                                     updated_by=req_header.updated_by,
                                     **row)
            db.session.add(req_row)

        db.session.commit()

        request_schema = ItemRequestSchema()
        result = request_schema.dump(req_header)
        return ResponseMessage(True, message="Successfully added!", data=result).resp()

    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500
    except Exception as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500


# Get All Item Request
@item_request.route('/get_all')
@token_required
def get_all_item_request(curr_user):
    try:
        data = request.args.to_dict()
        header_filt = []
        row_filt = []
        duedate = ''

        for k, v in data.items():
            if k in ['from_whse', 'to_whse'] and v:
                row_filt.append((k, "==", v))
            elif k == 'sap_number':
                if v:
                    header_filt.append((k, "==", v))
                else:
                    header_filt.append((k, "==", None))
            elif k == 'confirm':
                if not v:
                    header_filt.append((k, "==", None))
                else:
                    header_filt.append((k, "==", int(v)))
            elif 'duedate' == '':
                if v:
                    duedate = v
            else:
                if v:
                    header_filt.append((k, "==", v))

        # print(header_filt, row_filt)
        req_header_filter = BaseQuery.create_query_filter(ItemRequest, filters={'and': header_filt})
        req_row_filter = BaseQuery.create_query_filter(ItemRequestRow, filters={'and': row_filt})
        if duedate:
            item_req = db.session.query(ItemRequest). \
                filter(and_(cast(ItemRequest.transdate, DATE) == duedate,
                            *req_header_filter, 
                            *req_row_filter)).all()
        else:
            item_req = db.session.query(ItemRequest). \
                filter(and_(*req_header_filter, 
                            *req_row_filter)).all()

        request_schema = ItemRequestSchema(many=True,
                                           exclude=("date_created", "date_updated", "created_by", "updated_by"))
        result = request_schema.dump(item_req)
        return ResponseMessage(True, data=result).resp()

    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500
    except Exception as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500


# Get Item Request Details
@item_request.route('/details/<int:id>')
@token_required
def get_item_request_details(curr_user, id):
    try:
        item_req = ItemRequest.query.get(id)
        request_schema = ItemRequestSchema()
        result = request_schema.dump(item_req)
        return ResponseMessage(True, message="Successfully added!", data=result).resp()
    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500
    except Exception as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500


# Confirm Item Request
@item_request.route('/confirm/<int:id>', methods=['PUT'])
@token_required
def confirm_item_request(curr_user, id):
    if not curr_user.is_admin() and not curr_user.is_manager():
        return ResponseMessage(False, message="Unauthorized user!").resp(), 401

    try:
        data = request.get_json()
        confirm = data['confirm']
        remarks = data['remarks'] if 'remarks' in data else ''

        item_req = ItemRequest.query.get(id)
        if not item_req:
            raise Exception("Invalid id")
        if item_req.confirm:
            raise Exception("Already confirmed!")
        
        item_req.confirm = confirm
        item_req.remarks = remarks
        item_req.date_updated = datetime.now()
        item_req.updated_by = curr_user.id

        db.session.commit()
        return ResponseMessage(True, message='Successfully confirm').resp()
    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500
    except Exception as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500
    finally:
        db.session.close()



# Update SAP Number
@item_request.route('/sap_update/<int:id>', methods=['PUT'])
@token_required
def item_req_sap_update(curr_user, id):
    if not curr_user.is_admin() and not curr_user.is_can_add_sap():
        return ResponseMessage(False, message="Unauthorized user!").resp(), 401


    try:
        data = request.get_json()
        sap_number = data['sap_number']
        remarks = data['remarks'] if 'remarks' in data else ''
        
        item_req = ItemRequest.query.get(id)
        if not item_req.confirm:
            raise Exception("Please confirm it first!")
        
        item_req.sap_number = sap_number
        item_req.remarks = remarks
        item_req.docstatus = 'C'
        item_req.date_updated = datetime.now()
        item_req.updated_by = curr_user.id

        db.session.commit()
        return ResponseMessage(True, message='Successfully confirm').resp()
    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500
    except Exception as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500
    finally:
        db.session.close()



# Cancel Item Request
@item_request.route('/cancel/<int:id>', methods=['PUT'])
@token_required
def cancel_item_request(curr_user, id):
    try:
        data = request.get_json()
        item_req = ItemRequest.query.get(id)
        if not item_req:
            raise Exception("Invalid item request id!")
        if item_req.docstatus != 'O':
            raise Exception("Item request already closed!")
        item_req.remarks = data['remarks'] if 'remarks' in data else ''
        item_req.docstatus = 'N'
        db.session.commit()
        return ResponseMessage(True, message="Successfully canceled!").resp()
    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500
    except Exception as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500
