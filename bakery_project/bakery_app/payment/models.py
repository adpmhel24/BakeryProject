from datetime import datetime
from sqlalchemy import event
from bakery_app import db, ma
from bakery_app.customers.models import Customer
from bakery_app.sales.models import SalesHeader
from bakery_app.inventory.models import InvTransaction, WhseInv
from bakery_app._helpers import get_model_changes


class PayTransHeader(db.Model):
    __tablename__ = "tblpayment"

    id = db.Column(db.Integer, primary_key=True)
    series = db.Column(db.Integer, db.ForeignKey('tblseries.id', ondelete='NO ACTION',
                                                 onupdate='NO ACTION'))  # series id
    seriescode = db.Column(db.String(50), nullable=False)  # series code
    transnumber = db.Column(db.Integer, nullable=False)  # series next_num
    objtype = db.Column(db.Integer, db.ForeignKey(
        'tblobjtype.objtype'), nullable=False)
    # seriescode + number
    reference = db.Column(db.String(100), nullable=False)
    transdate = db.Column(db.DateTime, nullable=False)
    base_id = db.Column(db.Integer, db.ForeignKey(
        'tblsales.id', ondelete='CASCADE'))  # sales id
    base_num = db.Column(db.Integer)  # sales transnum
    # C for Close, N for Cancel
    docstatus = db.Column(db.String(10), default='C')
    cust_code = db.Column(db.String(100), nullable=False)
    total_due = db.Column(db.Float, nullable=False, default=0.00)
    total_paid = db.Column(db.Float, nullable=False, default=0.00)
    remarks = db.Column(db.String(250))
    reference2 = db.Column(db.String(250))
    sap_number = db.Column(db.Integer)
    created_by = db.Column(
        db.Integer, db.ForeignKey('tbluser.id'), nullable=False)
    updated_by = db.Column(
        db.Integer, db.ForeignKey('tbluser.id'), nullable=False)
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.now)
    date_updated = db.Column(db.DateTime, nullable=False, default=datetime.now)

    payrows = db.relationship(
        'PayTransRow', back_populates='payheader', lazy=True)


class PayTransRow(db.Model):
    __tablename__ = "tblpaymentrow"

    id = db.Column(db.Integer, primary_key=True)
    payment_id = db.Column(db.Integer, db.ForeignKey(
        'tblpayment.id', ondelete='NO ACTION'), nullable=False)
    payment_type = db.Column(db.String(50), db.ForeignKey(
        'tblpaymenttype.code', onupdate='CASCADE'), nullable=False)
    deposit_id = db.Column(db.Integer)
    amount = db.Column(db.Float, nullable=False)
    created_by = db.Column(
        db.Integer, db.ForeignKey('tbluser.id'), nullable=False)
    updated_by = db.Column(
        db.Integer, db.ForeignKey('tbluser.id'), nullable=False)
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.now)
    date_updated = db.Column(db.DateTime, nullable=False, default=datetime.now)
    status = db.Column(db.Integer, default=1)  # 1 if not cancel, 2 if canceled
    reference2 = db.Column(db.String(100))
    sap_number = db.Column(db.Integer)
    payheader = db.relationship(
        'PayTransHeader', back_populates='payrows', lazy=True)


class PaymentType(db.Model):
    __tablename__ = "tblpaymenttype"
    """if cash, deposit, ecash, etc"""
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), nullable=False, unique=True)
    description = db.Column(db.String(100), nullable=False)
    created_by = db.Column(
        db.Integer, db.ForeignKey('tbluser.id'), nullable=False)
    updated_by = db.Column(
        db.Integer, db.ForeignKey('tbluser.id'), nullable=False)
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.now)
    date_updated = db.Column(db.DateTime, nullable=False, default=datetime.now)


class Deposit(db.Model):
    __tablename__ = "tbldeposit"

    id = db.Column(db.Integer, primary_key=True)
    series = db.Column(db.Integer, db.ForeignKey('tblseries.id', ondelete='NO ACTION',
                                                 onupdate='NO ACTION'))  # series id
    seriescode = db.Column(db.String(50), nullable=False)  # series code
    transnumber = db.Column(db.Integer, nullable=False)  # series next_num
    objtype = db.Column(db.Integer, db.ForeignKey(
        'tblobjtype.objtype'), nullable=False)
    # seriescode + number
    reference = db.Column(db.String(100), nullable=False)
    transdate = db.Column(db.DateTime, nullable=False)
    # O for Open, C for Close, N for Cancel
    status = db.Column(db.String(10), default='O')
    cust_code = db.Column(db.String(100), db.ForeignKey(
        'tblcustomer.code', onupdate='CASCADE'), nullable=False)
    amount = db.Column(db.Float, nullable=False, default=0.00)
    balance = db.Column(db.Float, nullable=False, default=0.00)
    remarks = db.Column(db.String(250))
    reference2 = db.Column(db.String(100))
    sap_number = db.Column(db.Integer)
    created_by = db.Column(
        db.Integer, db.ForeignKey('tbluser.id'), nullable=False)
    updated_by = db.Column(
        db.Integer, db.ForeignKey('tbluser.id'), nullable=False)
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.now)
    date_updated = db.Column(db.DateTime, nullable=False, default=datetime.now)


class CashOut(db.Model):
    __tablename__ = "tblcashout"

    id = db.Column(db.Integer, primary_key=True)
    seriescode = db.Column(db.String(50), nullable=False)  # series code
    transnumber = db.Column(db.Integer, nullable=False)  # series next_num
    objtype = db.Column(db.Integer, db.ForeignKey(
        'tblobjtype.objtype'), nullable=False)
    # seriescode + number
    reference = db.Column(db.String(100), nullable=False)
    transdate = db.Column(db.DateTime, nullable=False)
    amount = db.Column(db.Float, nullable=False, default=0.00)
    remarks = db.Column(db.String(250))
    # C for Close and N for Cancel
    status = db.Column(db.String(10), default='C')
    created_by = db.Column(
        db.Integer, db.ForeignKey('tbluser.id'), nullable=False)
    updated_by = db.Column(
        db.Integer, db.ForeignKey('tbluser.id'), nullable=False)
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.now)
    date_updated = db.Column(db.DateTime, nullable=False, default=datetime.now)


class CashTransaction(db.Model):
    __tablename__ = "tblcashtrans"

    id = db.Column(db.Integer, primary_key=True)
    trans_id = db.Column(db.Integer, nullable=False)
    trans_num = db.Column(db.Integer, nullable=False)
    transdate = db.Column(db.DateTime, nullable=False)
    objtype = db.Column(db.Integer, db.ForeignKey(
        'tblobjtype.objtype'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    transtype = db.Column(db.String(50))
    reference = db.Column(db.String(100))
    created_by = db.Column(
        db.Integer, db.ForeignKey('tbluser.id'), nullable=False)
    updated_by = db.Column(
        db.Integer, db.ForeignKey('tbluser.id'), nullable=False)
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.now)
    date_updated = db.Column(db.DateTime, nullable=False, default=datetime.now)


# Payment Before Flush Event
@event.listens_for(db.session, "before_flush")
def payment_before_flush(*args):
    sess = args[0]
    for obj in sess.new:

        if isinstance(obj, PayTransRow):
            pay_header = PayTransHeader.query.filter_by(
                id=obj.payment_id).first()
            cust = Customer.query.filter_by(code=pay_header.cust_code).first()
            sales = SalesHeader.query.filter_by(id=pay_header.base_id).first()

            # Update Sales Amount Due and Sales Applied Amount
            sales.amount_due -= obj.amount
            sales.appliedamt += obj.amount
            # Update Customer Balance
            cust.balance -= pay_header.total_paid

            if obj.payment_type in ['FDEPS']:
                # query the deposit
                dep = Deposit.query.get(obj.deposit_id)
                # minus the row amount to deposit balance
                dep.balance -= obj.amount
                # update the customer deposit balance
                customer = Customer.query.filter_by(code=dep.cust_code).first()
                customer.dep_balance -= obj.amount

                # if the deposit balance is 0 then close the status
                if dep.balance == 0:
                    dep.status = 'C'

                db.session.add_all([dep, customer])

            if sales.amount_due == 0:
                sales.docstatus = 'C'

            sales.confirm = True

            # Add to Cash Transaction
            cash_trans = CashTransaction(trans_id=pay_header.id,
                                         trans_num=pay_header.transnumber,
                                         transdate=pay_header.transdate,
                                         objtype=pay_header.objtype,
                                         amount=obj.amount,
                                         reference=pay_header.reference,
                                         transtype=obj.payment_type,
                                         created_by=pay_header.created_by,
                                         updated_by=pay_header.updated_by)

            db.session.add_all([cust, sales, cash_trans])


        elif isinstance(obj, Deposit):
            customer = Customer.query.filter_by(code=obj.cust_code).first()
            customer.dep_balance += obj.amount
            db.session.add(customer)

        else:
            continue

    # If Update
    for obj in sess.dirty:
        if isinstance(obj, PayTransHeader):
            # query the changes
            changes = get_model_changes(obj)
            for i in changes:
                if i == 'status':
                    # get the pay_header
                    pay_header = PayTransHeader.query.get(obj.id)
                    cust = Customer.query.filter_by(code=pay_header.cust_code).first()
                    sales = SalesHeader.query.filter_by(id=pay_header.base_id).first()

                    # check if the update is for canceled
                    # check if the header is still open then proceed.
                    if changes[i][1] == 'N':
                        # open the sales document
                        sales.docstatus = 'O'
                        # get the payment rows
                        payment_rows = PayTransRow.query.filter_by(
                            payment_id=obj.id).all()

                        # loop the payment rows
                        for row in payment_rows:
                            # check if the payment row as deposit
                            # if has deposit, update deposit
                            if row.payment_type in ['FDEPS']:
                                # query the deposit
                                dep = Deposit.query.get(row.deposit_id)
                                # update the customer deposit balance also
                                customer = Customer.query.filter_by(code=dep.cust_code).first()
                                customer.dep_balance += obj.amount
                                # check if the status is close then open it
                                if dep.status != 'O':
                                    dep.status = 'O'
                                # add the row amount to deposit balance
                                dep.balance += row.amount
                                db.session.add_all([dep, customer])

                            # Update Sales Amount Due and Sales Applied Amount
                            sales.amount_due += obj.amount
                            sales.appliedamt -= obj.amount

                            # Update Customer Balance
                            cust.balance += pay_header.total_paid

                            # Add to Cash Transaction
                            cash_trans = CashTransaction(trans_id=pay_header.id,
                                                         trans_num=pay_header.transnumber,
                                                         transdate=pay_header.transdate,
                                                         objtype=pay_header.objtype,
                                                         reference=pay_header.reference,
                                                         amount=-row.amount,
                                                         transtype=row.payment_type,
                                                         created_by=pay_header.created_by,
                                                         updated_by=pay_header.updated_by)

                            db.session.add_all([cust, sales, cash_trans])

        # Add to cash transaction
        elif isinstance(obj, Deposit):
            changes = get_model_changes(obj)

            for i in changes:
                if i == 'status':
                    if changes[i][1] == 'N':
                        customer = Customer.query.filter_by(code=obj.cust_code).first()
                        customer.dep_balance -= obj.amount
                        cash_trans = CashTransaction(trans_id=obj.id,
                                                     trans_num=obj.transnumber,
                                                     transdate=obj.transdate,
                                                     objtype=obj.objtype,
                                                     amount=-obj.amount,
                                                     reference=obj.reference,
                                                     transtype='DEPS',
                                                     created_by=obj.created_by,
                                                     updated_by=obj.updated_by)
                        db.session.add_all([cash_trans, customer])

        # Add to cash transaction
        elif isinstance(obj, CashOut):
            changes = get_model_changes(obj)

            for i in changes:
                if i == 'status':
                    if changes[i][1] == 'N':
                        cash_trans = CashTransaction(trans_id=obj.id,
                                                     trans_num=obj.transnumber,
                                                     transdate=obj.transdate,
                                                     objtype=obj.objtype,
                                                     reference=obj.reference,
                                                     amount=-obj.amount,
                                                     transtype='CASHOUT',
                                                     created_by=obj.created_by,
                                                     updated_by=obj.updated_by)
                        db.session.add(cash_trans)
        else:
            continue


@event.listens_for(db.session, "after_flush")
def after_flush_event(*args):
    sess = args[0]
    for obj in sess.new:

        # Add to cash transaction
        if isinstance(obj, Deposit):
            cash_trans = CashTransaction(trans_id=obj.id,
                                         trans_num=obj.transnumber,
                                         transdate=obj.transdate,
                                         objtype=obj.objtype,
                                         amount=obj.amount,
                                         reference=obj.reference,
                                         transtype='DEPS',
                                         created_by=obj.created_by,
                                         updated_by=obj.updated_by)
            db.session.add(cash_trans)


        # Add to cash transaction
        elif isinstance(obj, CashOut):
            cash_trans = CashTransaction(trans_id=obj.id,
                                         trans_num=obj.transnumber,
                                         transdate=obj.transdate,
                                         objtype=obj.objtype,
                                         reference=obj.reference,
                                         amount=obj.amount,
                                         transtype='CASHOUT',
                                         created_by=obj.created_by,
                                         updated_by=obj.updated_by)
            db.session.add(cash_trans)

        else:
            continue
