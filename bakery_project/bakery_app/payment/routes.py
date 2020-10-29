import json
import pyodbc
from datetime import datetime
from sqlalchemy import exc, and_, or_, func
from flask import Blueprint, request, jsonify

from bakery_app import db
from bakery_app._helpers import BaseQuery
from bakery_app.sales.models import (SalesHeader, SalesRow)
from bakery_app.sales.sales_schema import SalesHeaderSchema, SalesRowSchema
from bakery_app.branches.models import Series, ObjectType, Warehouses
from bakery_app.users.routes import token_required
from bakery_app._utils import Check, ResponseMessage

from .models import (PaymentType, PayTransHeader, PayTransRow, AdvancePayment)
from .payment_schema import (PaymentHeaderSchema, PaymentRowSchema, PaymentTypeSchema, AdvancePaymentSchema)

payment = Blueprint('payment', __name__)


# Create New Payment Type
@payment.route('/api/payment/type/new', methods=['POST'])
@token_required
def payment_type_new(curr_user):
    if not curr_user.is_admin():
        raise Exception("Unauthorized user!")

    data = request.get_json()

    try:
        ptype = PaymentType(**data)
        ptype.created_by = curr_user.id
        ptype.updated_by = curr_user.id
        db.session.add(ptype)
        db.session.commit()
        ptype_schema = PaymentTypeSchema()
        result = ptype_schema.dump(ptype)
        return ResponseMessage(True, message="Successfully added!", data=result).resp()
    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        db.session.rollback()
        return ResponseMessage(False, message=f"{err}"), 500
    except Exception as err:
        db.session.rollback()
        return ResponseMessage(False, message=f"{err}"), 500
    finally:
        db.session.close()


# Get All Payment Type
@payment.route('/api/payment/type/get_all')
@token_required
def get_all_payment_type(curr_user):
    try:
        q = request.args.get('q')
        if q:
            search = f"%{q}%"
            ptype = db.session.query(PaymentTypeSchema). \
                filter(or_(PaymentType.code.like(search), PaymentType.description.like(search))).all()
        else:
            ptype = db.session.query(PaymentType).all()

        ptype_schema = PaymentTypeSchema(many=True)
        result = ptype_schema.dump(ptype)
        return ResponseMessage(True, data=result).resp()
    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        return ResponseMessage(False, message=f"{err}").resp()
    except Exception as err:
        return ResponseMessage(False, message=f"{err}").resp()


# Get Payment Type Details
@payment.route('/api/payment/type/details/<int:id>')
@token_required
def get_payment_type_details(curr_user, id):
    try:
        ptype = PaymentType.query.get(id)
        ptype_schema = PaymentTypeSchema()
        result = ptype_schema.dump(ptype)
        return ResponseMessage(True, data=result).resp()
    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        return ResponseMessage(False, message=f"{err}").resp()
    except Exception as err:
        return ResponseMessage(False, message=f"{err}").resp()


# Update Payment Type
@payment.route('/api/payment/type/update/<int:id>', methods=['PUT'])
@token_required
def update_payment_type(curr_user, id):
    if not curr_user.is_admin():
        raise Exception("Unauthorized user!")
    try:
        data = request.get_json()
        ptype = PaymentType.query.get(id)
        if data['code']:
            ptype.code = data['code']
        if data['description']:
            ptype.code = data['description']
        ptype.updated_by = curr_user.id
        ptype.date_updated = datetime.now()

        db.session.commit()
        ptype_schema = PaymentTypeSchema()
        result = ptype_schema.dump(ptype)
        return ResponseMessage(True, data=result).resp()
    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500
    except Exception as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500


# Delete Payment Type
@payment.route('/api/payment/type/delete/<int:id>', methods=['DELETE'])
@token_required
def delete_payment_type(curr_user, id):
    if not curr_user.is_admin():
        return ResponseMessage(False, message="Unauthorized user!").resp(), 401
    try:
        ptype = PaymentType.query.get(id)
        db.session.delete(ptype)
        db.session.commit()
    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500
    except Exception as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500


# Add Advance Payment
@payment.route('/api/adv_payment/new', methods=["POST"])
@token_required
def new_advance_payment(curr_user):
    if not curr_user.is_admin() and not curr_user.is_manager():
        return ResponseMessage(False, message="Unauthorized user!").resp(), 401

    data = request.get_json()
    data['created_by'] = curr_user.id
    data['updated_by'] = curr_user.id
    try:
        adv = AdvancePayment(**data)
        adv.balance = adv.amount
        db.session.add(adv)
        db.session.commit()
        adv_schema = AdvancePaymentSchema(exclude=("date_created", "date_updated", "created_by", "updated_by"))
        result = adv_schema.dump(adv)
        return ResponseMessage(True, message="Successfully added!", data=result).resp()
    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        db.session.rollback()
        return ResponseMessage(False, message=f"{err}").resp(), 500
    except Exception as err:
        db.session.rollback()
        return ResponseMessage(False, message=f"{err}").resp(), 500
    finally:
        db.session.close()


# Get All Advance Payment
@payment.route('/api/adv_payment/get_all')
@token_required
def get_all_advance_payment(curr_user):
    cust = request.args.get('customer')
    status = request.args.get('status')
    filt = []

    if cust:
        filt.append(('cust_code', 'like', f'%{cust}%'))
    if status:
        filt.append(('status', '==', status))

    try:
        # generate obj for query
        adv_filter = BaseQuery.create_query_filter(AdvancePayment, filters={'and': filt})

        adv = db.session.query(AdvancePayment).filter(*adv_filter).all()
        adv_schema = AdvancePaymentSchema(many=True,
                                          exclude=("date_created", "date_updated", "created_by", "updated_by"))
        result = adv_schema.dump(adv)
        return ResponseMessage(True, count=len(result), data=result).resp()
    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500
    except Exception as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500


# Get Advance Payment Details
@payment.route('/api/adv_payment/details/<int:id>')
@token_required
def get_adv_payment_details(curr_user, id):
    try:
        adv = AdvancePayment.query.get(id)
        adv_schema = AdvancePaymentSchema()
        result = adv_schema.dump(adv)
        return ResponseMessage(True, data=result).resp()
    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500
    except Exception as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500


# Update Advance Payment
@payment.route('/api/adv_payment/update/<int:id>', methods=['PUT'])
@token_required
def update_adv_payment(curr_user, id):
    if not curr_user.is_admin() and not curr_user.is_manager():
        return ResponseMessage(False, message="Unauthorized user!").resp(), 401

    data = request.get_json()

    try:
        adv = AdvancePayment.query.get(id)
        adv.remarks = data['remarks'] if data['remarks'] else adv.remarks
        adv.reference = data['reference'] if data['reference'] else adv.reference
        adv.updated_by = curr_user.id
        adv.date_updated = datetime.now()

        db.session.commit()

        adv_schema = AdvancePaymentSchema()
        result = adv_schema.dump(adv)
        return ResponseMessage(True, data=result).resp()
    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500
    except Exception as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500


# Cancel Advance Payment
@payment.route('/api/adv_payment/cancel/<int:id>', methods=['PUT'])
@token_required
def cancel_adv_payment(curr_user, id):
    if not curr_user.is_admin() and not curr_user.is_manager():
        return ResponseMessage(False, message="Unauthorized user!").resp(), 401

    try:
        adv = AdvancePayment.query.get(id)
        if adv.status != 'O':
            raise Exception("Advance payment is already closed")
        adv.status = 'N'
        db.session.commit()
    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500
    except Exception as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500


# New Payment
@payment.route('/api/payment/new', methods=['POST', 'GET'])
@token_required
def payment_new(curr_user):
    if not curr_user.is_cashier() and not curr_user.is_admin():
        return ResponseMessage(False, message="Unauthorized user!").resp(), 401

    if request.method == 'GET':
        try:
            filt = []

            transnum = request.args.get('transnum')
            user_id = request.args.get('user_id')

            if transnum:
                filt.append(('transnumber', 'like', f'%{transnum}%'))

            if user_id:
                filt.append(('created_by', '==', user_id))
            filt.append(('docstatus', '==', 'O'))

            sales_filter = BaseQuery.create_query_filter(SalesHeader, filters={'and': filt})

            sales = db.session.query(SalesHeader).join(SalesRow). \
                join(Warehouses, Warehouses.whsecode == SalesRow.whsecode). \
                filter(and_(Warehouses.branch == curr_user.branch, *sales_filter)).all()

            if not sales:
                raise Exception(f"No sales record found!")

            sales_schema = SalesHeaderSchema(many=True, only=("id", "docstatus", "seriescode",
                                                              "transnumber", "reference", "transdate", "cust_code",
                                                              "cust_name", "objtype", "remarks", "transtype", "delfee",
                                                              "disctype", "discprcnt", "disc_amount", "gross",
                                                              "gc_amount", "doctotal", "reference2", "tenderamt",
                                                              "sap_number", "appliedamt", "amount_due", "void"))
            result = sales_schema.dump(sales)
            return ResponseMessage(True, count=len(result), data=result).resp()

        except (pyodbc.IntegrityError, exc.IntegrityError) as err:
            return ResponseMessage(False, message=f"{err}").resp(), 500
        except Exception as err:
            return ResponseMessage(False, message=f"{err}").resp(), 500

    elif request.method == 'POST':
        datas = request.get_json()
        try:
            for data in datas:
                details = data['rows']

                obj = ObjectType.query.filter_by(code='PMNT').first()
                if not obj:
                    return ResponseMessage(False, message="No object type!").resp(), 401

                # query the series
                series = Series.query.filter_by(whsecode=curr_user.whse, objtype=obj.objtype).first()
                # check if has an series
                if not series:
                    return ResponseMessage(False, message="No series found!").resp(), 401

                # add to the header
                data['header']['seriescode'] = series.code
                data['header']['transnumber'] = series.next_num
                data['header']['reference'] = series.code + str(series.next_num)
                data['header']['objtype'] = obj.objtype

                # check if has transdate and convert to datetime object
                if data['header']['transdate']:
                    data['header']['transdate'] = datetime.strptime(data['header']['transdate'], '%Y/%m/%d %H:%M')

                # unpack to the class PayTransHeader
                payment = PayTransHeader(**data['header'])

                # get the amount due of sales
                sales = SalesHeader.query.filter_by(id=data['header']['base_id']).first()
                if sales.docstatus != 'O':
                    raise Exception("Sales already closed!")

                payment.total_due = sales.amount_due
                payment.created_by = curr_user.id
                payment.updated_by = curr_user.id
                series.next_num += 1
                db.session.add_all([series, payment])
                db.session.flush()

                # payment details
                for row in details:
                    pay_row = PayTransRow(payment_id=payment.id, **row)

                    # check if is advance payment
                    if row['payment_type'] in ['ADV']:
                        # get advance payment by advance id
                        adv = AdvancePayment.query.filter_by(id=row['advanced_id']).first()
                        if not adv:
                            raise Exception('Advance payment not found!')
                        # check if the advance payment is not open.
                        if adv.status != 'O':
                            raise Exception('Advance payment already closed!')
                    pay_row.created_by = curr_user.id
                    pay_row.updated_by = curr_user.id
                    db.session.add(pay_row)

                db.session.commit()
                payment_schema = PaymentHeaderSchema()
                result = payment_schema.dump(payment)
                return ResponseMessage(True, message="Successfully added!", data=result).resp()
        except (pyodbc.IntegrityError, exc.IntegrityError) as err:
            db.session.rollback()
            return ResponseMessage(False, message=f"{err}").resp(), 500
        except Exception as err:
            db.session.rollback()
            return ResponseMessage(False, message=f"{err}").resp(), 500
        finally:
            db.session.close()


# Void Payment
@payment.route('/api/cancel/void/<int:id>', methods=['PUT'])
@token_required
def void_payment(curr_user, id):
    if not curr_user.is_admin() and not curr_user.is_manager():
        return ResponseMessage(False, message="Unauthorized user!").resp(), 401

    try:
        payment = PayTransHeader.query.get(id)
        # check if payment is not equal to close
        if payment.docstatus != 'C':
            # if not close then raise exception
            raise Exception("Payment is already canceled!")
        payment.docstatus = 'N'
        db.session.commit()

        pay_schema = PaymentHeaderSchema()
        result = pay_schema.dump(payment)
        return ResponseMessage(True, message="Successfully canceled!", data=result).resp()

    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500
    except Exception as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500


# Get Total of Selected Sales
# parameter sales ids
@payment.route('/api/sales/for_payment')
@token_required
def get_sales_for_payment(curr_user):
    if not curr_user.is_cashier():
        return ResponseMessage(False, message="Unauthorized user!").resp(), 401
    try:
        ids = request.args.get('ids').rstrip(']').lstrip('[')
        ids = list(ids.split(','))
        filt_sales_h = [('id', 'in', ids)]
        filt_sales_row = [('sales_id', 'in', ids)]
        sales_h_filter = BaseQuery.create_query_filter(SalesHeader, filters={'and': filt_sales_h})
        sales_r_filter = BaseQuery.create_query_filter(SalesRow, filters={'and': filt_sales_row})

        # sales header query
        sales_h_query = db.session.query(
            func.sum(SalesHeader.delfee).label('delfee'),
            func.sum(SalesHeader.disc_amount).label('disc_amount'),
            func.sum(SalesHeader.gross).label('gross'),
            func.sum(SalesHeader.gc_amount).label('gc_amount'),
            func.sum(SalesHeader.doctotal).label('doctotal'),
            func.sum(SalesHeader.tenderamt).label('tenderamt'),
            func.sum(SalesHeader.appliedamt).label('appliedamt'),
            func.sum(SalesHeader.change).label('change'),
            func.sum(SalesHeader.amount_due).label('amount_due')) \
            .filter(*sales_h_filter) \
            .first()

        # sales row query
        sales_r_query = db.session.query(
            SalesRow.item_code,
            SalesRow.unit_price,
            SalesRow.discprcnt,
            SalesRow.free,
            func.sum(SalesRow.quantity).label('quantity'),
            func.sum(SalesRow.disc_amount).label('disc_amount'),
            func.sum(SalesRow.gross).label('gross'),
            func.sum(SalesRow.linetotal).label('linetotal')) \
            .filter(*sales_r_filter) \
            .group_by(SalesRow.item_code, SalesRow.unit_price, SalesRow.discprcnt, SalesRow.free) \
            .all()

        sales_h_schema = SalesHeaderSchema()
        sales_r_schema = SalesRowSchema(many=True)
        result_header = sales_h_schema.dump(sales_h_query)
        result_row = sales_r_schema.dump(sales_r_query)

        return ResponseMessage(True, data={"header": result_header, "row": result_row}).resp()
    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500
    except Exception as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500
