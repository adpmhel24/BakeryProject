import pyodbc

from datetime import datetime
from flask import Blueprint, request
from sqlalchemy import exc, and_, cast, DATE, func, case
from bakery_app import db
from bakery_app._utils import Check, ResponseMessage
from bakery_app._helpers import BaseQuery
from bakery_app.users.routes import token_required
from bakery_app.branches.models import ObjectType, Series
from bakery_app.items.models import Items
from bakery_app.inventory.models import WhseInv
from bakery_app.inventory.inv_schema import WhseInvSchema
from bakery_app.branches.models import Warehouses

from .models import PullOutHeader, PullOutRow, PullOutHeaderRequest, PullOutRowRequest
from .po_schema import (PullOutHeaderRowSchema, PullOutHeaderSchema,
                        PullOutHeaderRowRequestSchema, PullOutHeaderRequestSchema)

pullout = Blueprint('pullout', __name__)


# Create Pullout Count
@pullout.route('/api/pulloutreq/create', methods=['POST', 'GET'])
@token_required
def create_po_req(curr_user):
    if not curr_user.is_admin() and not curr_user.is_allow_pullout():
        return ResponseMessage(False, message="Unauthorized user!").resp(), 401

    whse = Warehouses.query.filter_by(whsecode=curr_user.whse).first()
    # if whse.is_cutoff():
    #     return ResponseMessage(False, message="Cutoff is enable, please disable it!").resp(), 401
    if not whse.is_cutoff():
        return ResponseMessage(False, message="Cutoff is disable").resp(), 401

    date = request.args.get('date')

    if request.method == 'GET':
        try:
            if not curr_user.is_manager():
                whse_inv_case = case([(WhseInv.quantity != 0, 1)], else_=0)
                whse_inv = db.session.query(WhseInv.item_code,
                                            WhseInv.item_code,
                                            WhseInv.quantity,
                                            Items.uom
                                            ).filter(WhseInv.warehouse == curr_user.whse
                                                     ).outerjoin(
                    Items, Items.item_code == WhseInv.item_code
                ).order_by(whse_inv_case.desc(), WhseInv.item_code
                           ).all()
                whseinv_schema = WhseInvSchema(many=True)
                result = whseinv_schema.dump(whse_inv)
                return ResponseMessage(True, data=result).resp()
            elif curr_user.is_manager():
                po_req_header = PullOutHeaderRequest
                po_req_row = PullOutRowRequest
                sales_case = case([(po_req_header.user_type == 'sales', po_req_row.quantity)])
                auditor_case = case([(po_req_header.user_type == 'auditor', po_req_row.quantity)])
                pull_out = db.session.query(
                        po_req_row.item_code,
                        func.sum(func.isnull(sales_case, 0)
                                 ).label('sales_count'),
                        func.sum(func.isnull(auditor_case, 0)
                                 ).label('auditor_count'),
                        func.sum(func.isnull(sales_case, 0) -
                                 func.isnull(auditor_case, 0)).label('variance'),
                        po_req_row.uom
                    ).filter(
                        and_(cast(po_req_header.transdate, DATE) == date,
                             po_req_row.whsecode == curr_user.whse,
                             po_req_header.id == po_req_row.pulloutreq_id,
                             False == po_req_header.confirm
                             )
                    ).group_by(po_req_row.item_code, po_req_row.uom
                               ).having(func.sum(func.isnull(sales_case, 0) - func.isnull(auditor_case, 0)) != 0
                                        ).all()

                po_req_schema = PullOutHeaderRequestSchema(many=True)
                result = po_req_schema.dump(pull_out)
                return ResponseMessage(True, data=result).resp()
        except (pyodbc.IntegrityError, exc.IntegrityError) as err:
            return ResponseMessage(False, message=f"{err}").resp(), 500
        except Exception as err:
            return ResponseMessage(False, message=f"{err}").resp(), 500
        finally:
            db.session.close()

    elif request.method == 'POST':
        try:
            # query the whse and check if the cutoff is true
            data = request.get_json()
            header = data['header']
            rows = data['rows']

            # add to headers
            header['created_by'] = curr_user.id
            header['updated_by'] = curr_user.id
            if curr_user.is_manager():
                header['user_type'] = 'manager'
            elif curr_user.is_auditor():
                header['user_type'] = 'auditor'
            elif curr_user.is_sales() and not curr_user.is_manager():
                header['user_type'] = 'sales'

            pending_req_po = PullOutHeaderRequest.query.filter(
                and_(PullOutHeaderRequest.user_type == header['user_type'],
                     func.cast(PullOutHeaderRequest.transdate,
                               DATE) == header['transdate'],
                     PullOutHeaderRequest.docstatus == 'O',
                     PullOutHeaderRequest.confirm == False)).first()

            if pending_req_po:
                return ResponseMessage(False, message=f"You have an entry that still pending!").resp(), 401

            # query the object type
            obj = ObjectType.query.filter_by(code='PORQ').first()

            # Check if has objtype
            if not obj:
                return ResponseMessage(False, message="Object type not found!").resp(), 401

            # query the series
            series = Series.query.filter_by(
                whsecode=curr_user.whse, objtype=obj.objtype).first()

            # check if has series
            if not series:
                return ResponseMessage(False, message="Series not found!").resp(), 401

            # check if next num is not greater done end num
            if series.next_num + 1 > series.end_num:
                return ResponseMessage(False, message="Series number is greater than next num!").resp(), 401

            # construct reference
            reference = f"{series.code}-{obj.code}-{series.next_num}"

            # add to header
            header['series'] = series.id
            header['objtype'] = obj.objtype
            header['seriescode'] = series.code
            header['transnumber'] = series.next_num
            header['reference'] = reference

            # add 1 to next series
            series.next_num += 1

            po_req_header = PullOutHeaderRequest(**header)
            db.session.add_all([series, po_req_header])
            db.session.flush()

            for row in rows:
                # query the stock inventory
                whse_inv = WhseInv.query.filter_by(
                    warehouse=curr_user.whse, item_code=row['item_code']).first()
                # check if the whse inv is less than the quantity to pullout
                # if true then raise an error.
                if whse_inv.quantity < row['quantity']:
                    raise Exception(
                        f"{row['item_code'].title()} below stock level!")

                # add to row
                row['whsecode'] = curr_user.whse
                row['objtype'] = po_req_header.objtype
                row['created_by'] = po_req_header.created_by
                row['updated_by'] = po_req_header.updated_by
                check = Check(**row)
                # check if valid
                if not check.itemcode_exist():
                    raise Exception("Invalid item code!")
                if not check.uom_exist():
                    raise Exception("Invalid uom!")

                po_req_row = PullOutRowRequest(
                    pulloutreq_id=po_req_header.id, **row)

                db.session.add(po_req_row)

            db.session.commit()

            return ResponseMessage(True, message="Successfully added!").resp()

        except (pyodbc.IntegrityError, exc.IntegrityError) as err:
            db.session.rollback()
            return ResponseMessage(False, message=f"{err}").resp(), 500
        except Exception as err:
            db.session.rollback()
            return ResponseMessage(False, message=f"{err}").resp(), 500
        finally:
            db.session.close()


# Get All Pullout
@pullout.route('/api/pullout/get_all', methods=['GET'])
@token_required
def get_all_po(curr_user):
    try:
        data = request.args.to_dict()

        transdate  = ''
        whse_filt = []
        header_filt = []

        for k,v in data.items():
            if k == 'transdate' and v:
                transdate = v
            elif k == 'branch' and v:
                whse_filt.append((k, "==", v))
            elif k == 'whsecode' and v:
                whse_filt.append((k, "==", v))
            else:
                if v:
                    header_filt.append((k, "==", v))

        whse_filters = BaseQuery.create_query_filter(Warehouses, filters={"and": whse_filt})
        po_filters = BaseQuery.create_query_filter(PullOutHeader, filters={"and": header_filt})

        if transdate:
            po_filters.append((cast(PullOutHeader.transdate, DATE) == transdate))

        pullout = db.session.query(PullOutHeader).\
            select_from(PullOutHeader).\
            join(PullOutRow, PullOutRow.pullout_id == PullOutHeader.id).\
            join(Warehouses, Warehouses.whsecode == PullOutRow.whsecode).\
            filter(*whse_filters, *po_filters)
        po_schema = PullOutHeaderSchema(many=True, exclude=("row",))
        result = po_schema.dump(pullout)
        return ResponseMessage(True, count=len(result), data=result).resp()
    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
            return ResponseMessage(False, message=f"{err}").resp(), 500
    except Exception as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500
    finally:
        db.session.close()


# Get Pullout Details
@pullout.route('/api/pullout/details/<int:id>')
@token_required
def get_po_details(curr_user, id):
    try:
        pullout = PullOutHeader.query.get(id)
        po_schema = PullOutHeaderSchema(only=("id","series", "seriescode", "transnumber",
                                                "objtype", "transdate", "reference", "remarks",
                                                "docstatus", "sap_number", "created_by", "updated_by",
                                                "date_created", "date_updated", "confirm", "row",))
        result = po_schema.dump(pullout)
        return ResponseMessage(True, data=result).resp()
    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
            return ResponseMessage(False, message=f"{err}").resp(), 500
    except Exception as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500
    finally:
        db.session.close()


