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
                whse_inv = db.session.query(WhseInv.item_code,
                                            WhseInv.item_code,
                                            WhseInv.quantity,
                                            Items.uom
                                            ).filter(WhseInv.warehouse == curr_user.whse
                                                     ).outerjoin(
                    Items, Items.item_code == WhseInv.item_code
                ).order_by(WhseInv.quantity.desc(), WhseInv.item_code
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


# # Confirm Actual Pullout
# @pullout.route('/api/pulloutreq/confirm', methods=['GET', 'PUT'])
# @token_required
# def po_count_confirm(curr_user):
#     if (not curr_user.is_manager() or not curr_user.is_admin()) and not curr_user.is_allow_pullout():
#         return ResponseMessage(False, message="Unauthorized user!").resp(), 401

#     whse = Warehouses.query.filter_by(whsecode=curr_user.whse).first()
#     # if whse.is_cutoff():
#     #     return ResponseMessage(False, message="Cutoff is enable, please disable it!").resp(), 401
#     if not whse.is_cutoff():
#         return ResponseMessage(False, message="Cutoff is disable").resp(), 401

#     date = request.args.get('transdate')

#     po_req_header = PullOutHeaderRequest
#     po_req_row = PullOutRowRequest

#     # sales case
#     sales_case = case(
#         [(po_req_header.user_type == 'sales', po_req_row.quantity)])

#     # auditor case
#     auditor_case = case(
#         [(po_req_header.user_type == 'auditor', po_req_row.quantity)])

#     # manager case
#     manager_case = case(
#         [(po_req_header.user_type == 'manager', po_req_row.quantity)])

#     # final case
#     final_case = case([
#         (None != func.sum(manager_case), func.sum(manager_case)),
#         (and_(None == func.sum(manager_case), None != func.sum(auditor_case)), func.sum(auditor_case))
#     ], else_=(func.sum(sales_case)))

#     # query the po count
#     po_req = db.session.query(
#         po_req_row.item_code,
#         func.sum(sales_case).label('sales_count'),
#         func.sum(auditor_case).label('auditor_count'),
#         func.sum(manager_case).label('manager_count'),
#         final_case.label('final_count'),
#         po_req_row.uom
#     ).outerjoin(Items, po_req_row.item_code == Items.item_code
#                 ).filter(
#         and_(
#             cast(po_req_header.transdate, DATE) == date,
#             po_req_header.confirm == False,
#             po_req_header.id == po_req_row.pulloutreq_id
#         )
#     ).group_by(po_req_row.item_code, po_req_row.uom
#                ).all()

#     # query if there's inventory count to confirm
#     po_req_count = po_req_header.query.filter(
#         and_(po_req_header.confirm == False, cast(po_req_header.transdate, DATE) == date)).first()
#     # if none return error message
#     if not po_req_count:
#         return ResponseMessage(False, message="No pullout request to confirm").resp(), 401

#     if request.method == 'GET':

#         try:

#             po_req_schema = PullOutHeaderRequestSchema(many=True)
#             result = po_req_schema.dump(po_req)
#             return ResponseMessage(True, data=result).resp()

#         except (pyodbc.IntegrityError, exc.IntegrityError) as err:
#             return ResponseMessage(False, message=f"{err}").resp(), 500
#         except Exception as err:
#             return ResponseMessage(False, message=f"{err}").resp(), 500
#         finally:
#             db.session.close()

#     if request.method == 'PUT':
#         data = request.get_json()
#         try:
#             if not data['confirm']:
#                 return ResponseMessage(False, message="Invalid confirm value").resp(), 401
#         except TypeError as err:
#             return ResponseMessage(False, message=f"{err}").resp(), 401

#         try:

#             # get the obj type of adjustment in
#             obj = ObjectType.query.filter_by(code='POUT').first()
#             # Check if has objtype
#             if not obj:
#                 return ResponseMessage(False, message="Object type not found!").resp(), 401

#             # query the series
#             series = Series.query.filter_by(
#                 whsecode=curr_user.whse, objtype=obj.objtype).first()
#             if not series:
#                 return ResponseMessage(False, message="Series not found!").resp(), 401
#             # check if next num is not greater done end num
#             if series.next_num + 1 > series.end_num:
#                 return ResponseMessage(False, message="Series number is greater than next num!").resp(), 401
#             # construct reference
#             reference = f"{series.code}-{obj.code}-{series.next_num}"

#             # check if next num is not greater done end num
#             # add to header
#             header = {'series': series.id, 'objtype': obj.objtype, 'seriescode': series.code,
#                       'transnumber': series.next_num, 'reference': reference, 'created_by': curr_user.id,
#                       'updated_by': curr_user.id, 'transdate': datetime.strptime(date, '%m/%d/%Y'),
#                       'sap_number': data['sap_number'] if 'sap_number' in data else None}

#             po_header = PullOutHeader(**header)

#             # add 1 to next series
#             series.next_num += 1

#             db.session.add_all([series, po_header])
#             db.session.flush()

#             for item in po_req:
#                 # get first then whse inv
#                 item_bal = WhseInv.query.filter_by(
#                     item_code=item.item_code, warehouse=curr_user.whse).first()
#                 # check if final count is greater than whse bal
#                 if item.final_count > item_bal.quantity:
#                     return ResponseMessage(False, message=f"{item.item_code.title()} is below quantity.").resp(), 500

#                 row = {'objtype': po_header.objtype, 'item_code': item.item_code,
#                        'quantity': item.final_count, 'uom': item.uom, 'whsecode': curr_user.whse,
#                        'created_by': po_header.created_by, 'updated_by': po_header.updated_by}

#                 po_row = PullOutRow(**row)
#                 po_row.pullout_id = po_header.id

#                 db.session.add(po_row)

#             db.session.query(po_req_header).filter(
#                 and_(po_req_header.confirm == False,
#                      cast(po_req_header.transdate, DATE) == date,
#                      po_req_header.docstatus == 'O')
#             ).update({'confirm': True, 'docstatus': 'C'}, synchronize_session=False)

#             db.session.commit()
#             return ResponseMessage(True, message="Confirm successfully!").resp()
#         except (pyodbc.IntegrityError, exc.IntegrityError) as err:
#             print(str(err))
#             db.session.rollback()
#             return ResponseMessage(False, message=f"{err}").resp(), 500
#         except Exception as err:
#             print(str(err))
#             db.session.rollback()
#             return ResponseMessage(False, message=f"{err}").resp(), 500
#         finally:
#             db.session.close()


# # Confirm Actual PullOut
# def po_count_confirm(curr_user, data, fo_po):
#     to_whse = data['po_whse']
#     sap_number = data['po_sap']
#     # get the obj type of adjustment in
#     obj = ObjectType.query.filter_by(code='POUT').first()
#     # Check if has objtype
#     if not obj:
#         raise Exception("Object type not found!")

#     # query the series
#     series = Series.query.filter_by(
#         whsecode=curr_user.whse, objtype=obj.objtype).first()
#     if not series:
#         raise Exception("Series not found!")

#     # check if next num is not greater done end num
#     if series.next_num + 1 > series.end_num:
#         raise Exception("Series number is greater than next num!")

#     # construct reference
#     reference = f"{series.code}-{obj.code}-{series.next_num}"

#     # check if next num is not greater done end num
#     # add to header
#     header = {'series': series.id, 'objtype': obj.objtype, 'seriescode': series.code,
#             'transnumber': series.next_num, 'reference': reference, 'created_by': curr_user.id,
#             'updated_by': curr_user.id, 'transdate': datetime.strptime(date, '%m/%d/%Y'),
#             'sap_number': sap_number if sap_number in data else None}

#     po_header = PullOutHeader(**header)

#     # add 1 to next series
#     series.next_num += 1

#     db.session.add_all([series, po_header])
#     db.session.flush()

#     for item in for_po:
#         # get first then whse inv
#         item_bal = WhseInv.query.filter_by(
#             item_code=item.item_code, warehouse=curr_user.whse).first()

#         # check if final count is greater than whse bal
#         if item.po_final_count > item_bal.quantity:
#             raise Exception(f"{item.item_code.title()} is below quantity.")

#         row = {'objtype': po_header.objtype, 'item_code': item.item_code,
#             'quantity': item.final_count, 'uom': item.uom, 'whsecode': curr_user.whse,
#             'created_by': po_header.created_by, 'updated_by': po_header.updated_by,
#             'to_whse': to_whse}

#         po_row = PullOutRow(**row)
#         po_row.pullout_id = po_header.id

#         db.session.add(po_row)

#     db.session.query(po_req_header).filter(
#         and_(po_req_header.confirm == False,
#             cast(po_req_header.transdate, DATE) == date,
#             po_req_header.docstatus == 'O')
#     ).update({'confirm': True, 'docstatus': 'C'}, synchronize_session=False)