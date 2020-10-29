from datetime import datetime
from sqlalchemy import event
from bakery_app import db, ma
from bakery_app.customers.models import Customer
from bakery_app.sales.models import SalesHeader
from bakery_app.inventory.models import InvTransaction, WhseInv


class PayTransHeader(db.Model):
    __tablename__ = "tblpayment"

    id = db.Column(db.Integer, primary_key=True)
    seriescode = db.Column(db.String(50), nullable=False)  # series code
    transnumber = db.Column(db.Integer, nullable=False)  # series next_num
    transdate = db.Column(db.DateTime, nullable=False)
    reference = db.Column(db.String(100), nullable=False)  # seriescode + number
    base_id = db.Column(db.Integer, db.ForeignKey('tblsales.id', ondelete='NO ACTION'))  # sales id
    base_num = db.Column(db.Integer)  # sales transnum
    objtype = db.Column(db.Integer, db.ForeignKey('tblobjtype.objtype'), nullable=False)
    docstatus = db.Column(db.String(10), default='C')
    cust_code = db.Column(db.String(100), nullable=False)
    total_due = db.Column(db.Float, nullable=False, default=0.00)
    total_paid = db.Column(db.Float, nullable=False, default=0.00)
    remarks = db.Column(db.String(250))
    reference2 = db.Column(db.String(250))
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    updated_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.now)
    date_updated = db.Column(db.DateTime, nullable=False, default=datetime.now)

    payrows = db.relationship('PayTransRow', back_populates='payheader', lazy=True)


class PayTransRow(db.Model):
    __tablename__ = "tblpaymentrow"

    id = db.Column(db.Integer, primary_key=True)
    payment_id = db.Column(db.Integer, db.ForeignKey('tblpayment.id', ondelete='NO ACTION'), nullable=False)
    payment_type = db.Column(db.String(50), db.ForeignKey('tblpaymenttype.code', onupdate='CASCADE'), nullable=False)
    advanced_id = db.Column(db.Integer)
    amount = db.Column(db.Float, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    updated_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.now)
    date_updated = db.Column(db.DateTime, nullable=False, default=datetime.now)
    status = db.Column(db.Integer, default=1)  # 1 if not cancel, 2 if canceled
    reference = db.Column(db.String(100))
    payheader = db.relationship('PayTransHeader', back_populates='payrows', lazy=True)


class PaymentType(db.Model):
    __tablename__ = "tblpaymenttype"
    """if cash, advance, ecash, etc"""
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), nullable=False, unique=True)
    description = db.Column(db.String(100), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    updated_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.now)
    date_updated = db.Column(db.DateTime, nullable=False, default=datetime.now)


class AdvancePayment(db.Model):
    __tablename__ = "tbladvncepay"

    id = db.Column(db.Integer, primary_key=True)
    transdate = db.Column(db.DateTime, nullable=False)
    cust_code = db.Column(db.String(100), db.ForeignKey('tblcustomer.code', onupdate='CASCADE'), nullable=False)
    amount = db.Column(db.Float, nullable=False, default=0.00)
    balance = db.Column(db.Float, nullable=False, default=0.00)
    remarks = db.Column(db.String(250))
    reference = db.Column(db.String(100))
    status = db.Column(db.String(10), default='O')
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    updated_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.now)
    date_updated = db.Column(db.DateTime, nullable=False, default=datetime.now)


# Payment Before Flush Event
@event.listens_for(db.session, "before_flush")
def payment_before_flush(*args):
    sess = args[0]
    for obj in sess.new:

        if isinstance(obj, PayTransRow):
            pay_header = PayTransHeader.query.filter_by(id=obj.payment_id).first()
            cust = Customer.query.filter_by(code=pay_header.cust_code).first()
            sales = SalesHeader.query.filter_by(id=pay_header.base_id).first()

            # update the Payment Header
            pay_header.total_paid += obj.amount
            # Update Sales Amount Due and Sales Applied Amount
            sales.amount_due -= obj.amount
            sales.appliedamt += obj.amount
            # Update Customer Balance
            cust.balance -= pay_header.total_paid

            if pay_header.total_paid > pay_header.total_due:
                raise Exception("Total amount paid is greater than total amount due!")

            if sales.amount_due == 0:
                sales.docstatus = 'C'

            db.session.add_all([pay_header, cust, sales])

        else:
            continue

    for obj in sess.dirty:
        if isinstance(obj, PayTransHeader):
            # get the pay_header
            pay_header = PayTransHeader.query.get(obj.id)
            cust = Customer.query.filter_by(code=pay_header.cust_code).first()
            sales = SalesHeader.query.filter_by(id=pay_header.base_id).first()

            # check if the update is for canceled
            # check if the header is still open then proceed.
            if obj.docstatus == 'N' and pay_header.docstatus != 'N':

                # open the sales document
                sales.docstatus = 'O'
                # get the payment rows
                payment_rows = PayTransRow.query.filter_by(payment_id=obj.id).all()

                # loop the payment rows
                for row in payment_rows:
                    # check if the payment row as advance payment
                    # if has advance payment update advance payment
                    if row.payment_type in ['ADV']:
                        # query the advance payment
                        adv = AdvancePayment.query.get(row.advanced_id)
                        # check if the status is close then open it
                        if adv.status != 'O':
                            adv.status = 'O'
                        # add the row amount to advance balance
                        adv.balance += row.amount
                        db.session.add(adv)

                    # Update Sales Amount Due and Sales Applied Amount
                    sales.amount_due += obj.amount
                    sales.appliedamt -= obj.amount

                    # Update Customer Balance
                    cust.balance += pay_header.total_paid

                    db.session.add_all([cust, sales])
        else:
            continue
