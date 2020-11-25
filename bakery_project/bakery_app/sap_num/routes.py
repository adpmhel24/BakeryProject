from datetime import datetime

import pyodbc
from flask import Blueprint, request, json
from sqlalchemy import exc, and_, func, DATE, cast
from bakery_app import db
from bakery_app._utils import ResponseMessage
from bakery_app.users.routes import token_required

from bakery_app.sales.models import SalesHeader, SalesRow
from bakery_app._helpers import BaseQuery
from bakery_app.sales.sales_schema import SalesHeaderSchema, SalesRowSchema
from bakery_app.branches.models import Warehouses
from bakery_app.users.models import User
from bakery_app.payment.models import PayTransHeader, Deposit, PayTransRow
from bakery_app.payment.payment_schema import PaymentHeaderSchema, PaymentRowSchema


sap_num = Blueprint('sap_num', __name__)


# GET All Sales for SAP Number Update
@sap_num.route('/api/sales/for_sap/get_all')
@token_required
def sales_update_sap(curr_user):
    if not curr_user.is_can_add_sap() and not curr_user.is_manager() and not curr_user.is_admin():
        return ResponseMessage(False, message="Unauthorized user!").resp(), 401

    try:
        filt = []
        date = ''
        branch = ''
        data = request.args.to_dict()
        for k, v in data.items():
            if k == 'date':
                date = v
                continue
            if k == 'branch':
                branch = v
                continue
            if k == 'cust_code':
                filt.append((k, 'like', f'%{v}%'))
            elif v:
                filt.append((k, '==', v))

        sales_filt = BaseQuery.create_query_filter(SalesHeader, filters={'and': filt})
        sales = db.session.query(SalesHeader).filter(and_(
                func.cast(SalesHeader.date_created, DATE) == date,
                SalesHeader.confirm == True,
                SalesHeader.sap_number == None,
                SalesHeader.docstatus != 'N',
                Warehouses.branch == branch,
                *sales_filt)
            ).outerjoin(
                SalesRow, SalesHeader.id == SalesRow.sales_id
            ).outerjoin(
                Warehouses, SalesRow.whsecode == Warehouses.whsecode
            ).all()

        sales_schema = SalesHeaderSchema(many=True, only=("id", "docstatus", "seriescode",
                                                            "transnumber", "reference", "transdate", "cust_code",
                                                            "cust_name", "objtype", "remarks", "transtype", "delfee",
                                                            "disctype", "discprcnt", "disc_amount", "gross",
                                                            "gc_amount", "doctotal", "reference2", "tenderamt",
                                                            "sap_number", "appliedamt", "amount_due", "void"))                                                
        result = sales_schema.dump(sales)
        return ResponseMessage(True, count=len(result), data=result).resp()
    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        return ResponseMessage(False, message=f'{err}').resp(), 500
    except Exception as err:
        return ResponseMessage(False, message=f'{err}').resp(), 500


# Update SAP Number in SALES Transaction
@sap_num.route('/api/sales/for_sap/update', methods=['PUT'])
@token_required
def update_sales_sap_num(curr_user):
    try:
        data = request.get_json()
        sap_number = data['sap_number']
        remarks = data['remarks']
        ids = data['ids']
        filt_sales_h = [('id', 'in', ids)]
        sales_filt = BaseQuery.create_query_filter(SalesHeader, filters={'and': filt_sales_h})
        sales = SalesHeader.query.filter(*sales_filt).all()
        count = 0
        for sale in sales:
            sale.sap_number = sap_number
            sale.remarks = sap_number
            count += 1
            db.session.commit()
        return ResponseMessage(True, message=f"{count} sales transaction updated!").resp()
    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        return ResponseMessage(False, message=f'{err}').resp(), 500
    except Exception as err:
        return ResponseMessage(False, message=f'{err}').resp(), 500


# Get The total quantity for SAP Number
# @sap_num.route('/api/sales/for_sap/get_total')
# @token_required
# def get_sales_total_for_sap(curr_user):
#     try:
#         ids = request.args.get('ids').rstrip(']').lstrip('[')
#         ids = list(ids.split(','))
#         filt_sales_h = [('sales_id', 'in', ids)]
#         sales_filt = BaseQuery.create_query_filter(SalesRow, filters={'and': filt_sales_h})
#         sales_row = db.session.query(
#                 SalesRow.item_code, 
#                 func.sum(SalesRow.quantity).label('quantity')
#             ).filter(*sales_filt
#             ).group_by(SalesRow.item_code
#             ).all()
#         row_schema = SalesRowSchema(many=True)
#         result = row_schema.dump(sales_row)
#         return ResponseMessage(True, count=len(result), data=result).resp()
#     except (pyodbc.IntegrityError, exc.IntegrityError) as err:
#             return ResponseMessage(False, message=f'{err}').resp(), 500
#     except Exception as err:
#         return ResponseMessage(False, message=f'{err}').resp(), 500


# Get and Update Payments for SAP IP number
@sap_num.route('/api/sap_num/payment/update', methods=['PUT', 'GET'])
@token_required
def get_payment_for_sap(curr_user):
    if not curr_user.is_can_add_sap() and not curr_user.is_manager() and not curr_user.is_admin():
        return ResponseMessage(False, message="Unauthorized user!").resp(), 401

    try:
        data = request.args.to_dict()
        transdate = ''
        sales_filts = []
        payment_filts = []
        payment_row_filts = [("sap_number", "==", None)]
        user_filts = []
        for k, v in data.items():
            if 'sales_type' == k and v:
                sales_filts.append(('transtype', "==", v))
            elif 'payment_type' == k and v:
                payment_row_filts.append((k, "==", v))
            elif 'transdate' == k and v:
                transdate = v
            elif 'branch' == k and v:
                user_filts.append((k, "==", v))
            elif 'whse' == k and v:
                user_filts.append((k, "==", v))
            elif 'ids' == k and v:
                payment_row_filts.append(('id', 'in', json.loads(request.args.get('ids'))))

        sales_filter = BaseQuery.create_query_filter(SalesHeader, filters={"and": sales_filts})
        payment_filter = BaseQuery.create_query_filter(PayTransHeader, filters={"and": payment_filts})
        user_filter = BaseQuery.create_query_filter(User, filters={"and": user_filts})
        payment_row_filter = BaseQuery.create_query_filter(PayTransRow, filters={"and": payment_row_filts})
        
        
        if transdate:
            query = db.session.query(PayTransRow).select_from(PayTransRow). \
                join(PayTransHeader, PayTransHeader.id == PayTransRow.payment_id). \
                join(SalesHeader, SalesHeader.id == PayTransHeader.base_id). \
                outerjoin(User, User.id == SalesHeader.created_by). \
                filter(and_(
                    cast(PayTransHeader.transdate, DATE) == transdate,
                    *sales_filter,
                    *payment_filter,
                    *user_filter,
                    *payment_row_filter
                ))
        else:
            query = db.session.query(PayTransRow).select_from(PayTransRow). \
                join(PayTransHeader, PayTransHeader.id == PayTransRow.payment_id). \
                join(SalesHeader, SalesHeader.id == PayTransHeader.base_id). \
                outerjoin(User, User.id == SalesHeader.created_by). \
                filter(and_(
                    *sales_filter,
                    *payment_filter,
                    *user_filter,
                    *payment_row_filter,
                ))
    
    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        return ResponseMessage(False, message=f'{err}').resp(), 500
    except Exception as err:
        return ResponseMessage(False, message=f'{err}').resp(), 500

    if request.method == 'GET':
        try:
            row_schema = PaymentRowSchema(many=True)
            result = row_schema.dump(query)
            return ResponseMessage(True, count=len(result), data=result).resp()

            
        except (pyodbc.IntegrityError, exc.IntegrityError) as err:
            return ResponseMessage(False, message=f'{err}').resp(), 500
        except Exception as err:
            return ResponseMessage(False, message=f'{err}').resp(), 500
        finally:
            db.session.close()

    elif request.method == 'PUT':
        
        try:
            data = request.get_json()
            for row in query:
                row.sap_number = data['sap_number']
                row.updated_by = curr_user.id
            db.session.commit()
            return ResponseMessage(True, message="Successfully updated!").resp()
        except (pyodbc.IntegrityError, exc.IntegrityError) as err:
            return ResponseMessage(False, message=f'{err}').resp(), 500
        except Exception as err:
            return ResponseMessage(False, message=f'{err}').resp(), 500
        finally:
            db.session.close()