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
from bakery_app.pullout.models import PullOutHeader

from .sap_num_schema import ForSAPIPSchema


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


# Get and Update Payments for SAP IP number
@sap_num.route('/api/sap_num/payment/update', methods=['PUT', 'GET'])
@token_required
def update_payment_sap_num(curr_user):
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
            elif 'search' == k and v:
                payment_filts.append(('cust_code', 'like', f'%{v}%'))

        sales_filter = BaseQuery.create_query_filter(SalesHeader, filters={"and": sales_filts})
        payment_filter = BaseQuery.create_query_filter(PayTransHeader, filters={"and": payment_filts})
        user_filter = BaseQuery.create_query_filter(User, filters={"and": user_filts})
        payment_row_filter = BaseQuery.create_query_filter(PayTransRow, filters={"and": payment_row_filts})
        
        
        if transdate:
            query = db.session.query(
                PayTransHeader.reference,
                PayTransHeader.cust_code,
                PayTransRow.payment_type,
                PayTransRow.amount,
                PayTransRow.reference2
                ).select_from(PayTransRow). \
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
            query = db.session.query(
                PayTransHeader.reference,
                PayTransHeader.cust_code,
                PayTransRow.payment_type,
                PayTransRow.amount,
                PayTransRow.reference2).select_from(PayTransRow). \
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
            row_schema = ForSAPIPSchema(many=True)
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


# Pull Out For SAP Number
@sap_num.route('/api/sap_num/pullout/update', methods=['PUT'])
@token_required
def update_pullout_sap_num(curr_user):
    if not curr_user.is_can_add_sap() and not curr_user.is_manager() and not curr_user.is_admin():
        return ResponseMessage(False, message="Unauthorized user!").resp(), 401

    try:
        sap_num = request.json['sap_number']
        ids = json.loads(request.args.get('ids'))
        pullout = PullOutHeader.query.filter(PullOutHeader.id.in_(ids)).all()
        print(pullout)

        for i in pullout:
            if i.sap_number:
                raise Exception(f'{i.reference} already have sap number!')
            i.sap_number = sap_num
            i.docstatus = 'C'
            i.remarks = request.json['remarks'] if request.json['remarks'] else None
            i.updated_by = curr_user.id
            i.date_updated = datetime.now()

        db.session.commit()
        return ResponseMessage(True, message="Successfully updated!").resp()
    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        return ResponseMessage(False, message=f'{err}').resp(), 500
    except Exception as err:
        return ResponseMessage(False, message=f'{err}').resp(), 500
    finally:
        db.session.close()
