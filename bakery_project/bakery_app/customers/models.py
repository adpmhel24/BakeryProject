from datetime import datetime
from sqlalchemy import event
from bakery_app import db, ma


# from bakery_app.sales.models import SalesHeader

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
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    updated_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    balance = db.Column(db.Float, nullable=False, default=0.00)
    custtype = db.relationship('CustomerType', backref='custtype', lazy=True)


class CustomerType(db.Model):
    __tablename__ = "tblcusttype"

    # If Employee, Customers
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.now)
    date_updated = db.Column(db.DateTime, nullable=False, default=datetime.now)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    updated_by = db.Column(db.Integer, db.ForeignKey('user.id'))
