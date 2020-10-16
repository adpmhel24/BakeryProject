from datetime import datetime
from sqlalchemy import event
from bakery_app import db, ma
from bakery_app.sales.models import SalesHeader, PaymentTransaction

class Customer(db.Model):
    __tablename__ = "tblcustomer"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(100), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    birthdate = db.Column(db.DateTime, default=datetime.now)
    cust_type = db.Column(db.Integer, db.ForeignKey('tblcusttype.id'), nullable=False)
    address = db.Column(db.String(250))
    contact = db.Column(db.String(100))
    whse = db.Column(db.String(100), db.ForeignKey('tblwhses.whsecode'))
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.now)
    date_updated = db.Column(db.DateTime, nullable=False, default=datetime.now)
    created_by = db.Column(db.DateTime, nullable=False)
    updated_by = db.Column(db.DateTime, nullable=False)
    balance = db.Column(db.Float, nullable=False, default=0.00)
    custtype = db.relationship('CustomerType', backref='custtype')

class CustomerType(db.Model):
    __tablename__ = "tblcusttype"

    # If Employee, Customers
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.now)
    date_updated = db.Column(db.DateTime, nullable=False, default=datetime.now)
    created_by = db.Column(db.Integer, nullable=False)
    updated_by = db.Column(db.Integer, nullable=False)
    

@event.listens_for(db.session, "after_flush")
def update_balance(*args):
    sess = args[0]
    
    for obj in sess.new:
        if isinstance(obj, SalesHeader):
            cust = Customer.query.filter_by(code=obj.cust_code).first()
            cust.balance += obj.doctotal
            db.session.add(cust)

        if isinstance(obj, PaymentTransaction):
            cust = Customer.query.filter_by(code=obj.cust_code).first()
            cust.balance -= (obj.cash + obj.ecash + obj.gc)
            db.session.add(customer)
        
        else:
            continue

class CustomerSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Customer
        ordered = True

class CustTypeSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = CustomerType
        ordered = True