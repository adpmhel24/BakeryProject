from datetime import datetime
from sqlalchemy import event
from bakery_app import db, ma
from bakery_app.customers.models import Customer
from bakery_app.inventory.models import InvTransaction, WhseInv
from bakery_app._helpers import get_model_changes


class SalesHeader(db.Model):
    __tablename__ = "tblsales"

    id = db.Column(db.Integer, primary_key=True)
    series = db.Column(db.Integer, db.ForeignKey('tblseries.id',
                                                 ondelete='NO ACTION', onupdate='NO ACTION'))  # series id
    docstatus = db.Column(db.String(30), default='O')
    seriescode = db.Column(db.String(50), nullable=False)
    transnumber = db.Column(db.Integer, nullable=False)
    reference = db.Column(db.String(100))
    transdate = db.Column(db.DateTime, nullable=False, default=datetime.now)
    cust_code = db.Column(db.String(100), db.ForeignKey('tblcustomer.code',
                                                        ondelete='CASCADE', onupdate='CASCADE'), nullable=False)
    cust_name = db.Column(db.String(100), nullable=False)
    objtype = db.Column(db.Integer, db.ForeignKey('tblobjtype.objtype'),
                        nullable=False)
    remarks = db.Column(db.String(250))
    transtype = db.Column(db.String(50), db.ForeignKey('tblsalestype.code'),
                          nullable=False)
    delfee = db.Column(db.Float, default=0.00)
    disctype = db.Column(db.String(50), db.ForeignKey('tbldscnttype.code'))
    discprcnt = db.Column(db.Float, nullable=False, default=0.00)
    disc_amount = db.Column(db.Float, nullable=False, default=0.00)
    gross = db.Column(db.Float, nullable=False, default=0.00)
    gc_amount = db.Column(db.Float, nullable=False, default=0.00)
    doctotal = db.Column(db.Float, nullable=False, default=0.00)
    reference2 = db.Column(db.String(100))
    tenderamt = db.Column(db.Float, default=0.00)
    sap_number = db.Column(db.Integer)
    appliedamt = db.Column(db.Float, default=0.00)
    change = db.Column(db.Float, default=0.00)
    amount_due = db.Column(db.Float, default=0.00)
    row_discount = db.Column(db.Float, default=0.00)
    void = db.Column(db.Boolean, nullable=True, default=False)
    created_by = db.Column(db.Integer, db.ForeignKey('tbluser.id'), nullable=False)
    updated_by = db.Column(db.Integer, db.ForeignKey('tbluser.id'), nullable=False)
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.now)
    date_updated = db.Column(db.DateTime, nullable=False, default=datetime.now)
    confirm = db.Column(db.Boolean, default=False)
    date_confirm = db.Column(db.DateTime, default=datetime.now)
    confirm_by = db.Column(db.Integer)  # user id
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)

    created_user = db.relationship("User", backref="salesheader", foreign_keys=[created_by])

    salesrow = db.relationship("SalesRow", back_populates="salesheader", lazy=True)


class SalesRow(db.Model):
    __tablename__ = "tblsalesrow"

    id = db.Column(db.Integer, primary_key=True)
    sales_id = db.Column(db.Integer,
                         db.ForeignKey('tblsales.id', ondelete='NO ACTION', onupdate='CASCADE'))
    item_code = db.Column(db.String(100),
                          db.ForeignKey('tblitems.item_code', ondelete='NO ACTION', onupdate='NO ACTION'))
    quantity = db.Column(db.Float, nullable=False, default=0.00)
    whsecode = db.Column(db.String(100), db.ForeignKey('tblwhses.whsecode', onupdate='CASCADE'), nullable=False)
    uom = db.Column(db.String(50), db.ForeignKey('tbluom.code', onupdate='CASCADE'))
    unit_price = db.Column(db.Float, nullable=False)
    disc_amount = db.Column(db.Float, nullable=False, default=0.00)
    discprcnt = db.Column(db.Float, nullable=False, default=0.00)
    gross = db.Column(db.Float, nullable=False, default=0.00)
    linetotal = db.Column(db.Float, nullable=False, default=0.00)
    free = db.Column(db.Boolean, default=False)

    row_whse = db.relationship("Warehouses", backref="salesrow", foreign_keys=[whsecode])
    salesheader = db.relationship("SalesHeader", back_populates="salesrow", lazy=True)


class SalesType(db.Model):
    __tablename__ = "tblsalestype"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), nullable=False, unique=True)
    description = db.Column(db.String(100), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('tbluser.id'), nullable=False)
    updated_by = db.Column(db.Integer, db.ForeignKey('tbluser.id'), nullable=False)
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.now)
    date_updated = db.Column(db.DateTime, nullable=False, default=datetime.now)


class DiscountType(db.Model):
    __tablename__ = "tbldscnttype"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), nullable=False, unique=True)
    description = db.Column(db.String(100), nullable=False)
    discount = db.Column(db.Float, nullable=False, default=0.00)
    created_by = db.Column(db.Integer, db.ForeignKey('tbluser.id'), nullable=False)
    updated_by = db.Column(db.Integer, db.ForeignKey('tbluser.id'), nullable=False)
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.now)
    date_updated = db.Column(db.DateTime, nullable=False, default=datetime.now)


class DiscountedCustomer(db.Model):
    __tablename__ = "tbldisccust"

    id = db.Column(db.Integer, primary_key=True)
    senior_name = db.Column(db.String(100), nullable=False, unique=True)
    senior_id = db.Column(db.String(150), nullable=False)
    contact_number = db.Column(db.String(30))
    created_by = db.Column(db.Integer, db.ForeignKey('tbluser.id'), nullable=False)
    updated_by = db.Column(db.Integer, db.ForeignKey('tbluser.id'), nullable=False)
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.now)
    date_updated = db.Column(db.DateTime, nullable=False, default=datetime.now)


# Sales Insert events
@event.listens_for(db.session, "before_flush")
def sales_insert_event(*args):
    sess = args[0]

    for obj in sess.new:

        if isinstance(obj, SalesRow):
            sales = SalesHeader.query.get(obj.sales_id)
            cust = Customer.query.filter_by(code=sales.cust_code).first()

            cust.balance += sales.amount_due

            # insert to InvTransaction all sales transaction
            inv_trans = InvTransaction(trans_id=sales.id, trans_num=sales.transnumber,
                                       objtype=sales.objtype, item_code=obj.item_code,
                                       outqty=obj.quantity, uom=obj.uom,
                                       warehouse=obj.whsecode, warehouse2=obj.whsecode,
                                       transdate=sales.transdate, created_by=sales.created_by,
                                       reference=sales.reference, reference2=sales.reference2,
                                       remarks=sales.remarks, series_code=sales.seriescode,
                                       updated_by=sales.updated_by)

            # deduct the qty of whse inv
            whseinv = WhseInv.query.filter_by(warehouse=obj.whsecode, item_code=obj.item_code).first()
            whseinv.quantity -= obj.quantity

            db.session.add_all([inv_trans, whseinv, cust])

        else:
            continue


# Sales Update events
@event.listens_for(db.session, "before_flush")
def sales_update_event(*args):
    sess = args[0]

    for obj in sess.dirty:

        if isinstance(obj, SalesHeader):
            # get the changes
            changes = get_model_changes(obj)
            for i in changes:
                if i == 'void':
                    if changes[i][1]:
                        salesrow = SalesRow.query.filter(SalesRow.sales_id == obj.id).all()

                        # Update Customer Balance
                        cust = Customer.query.filter_by(code=obj.cust_code).first()
                        cust.balance -= obj.amount_due

                        # Loop all the items in salesrow if the header is void
                        # And Insert to Inv_transaction the voided items
                        for row in salesrow:
                            # add to inventory transaction the void transaction
                            inv_trans = InvTransaction(trans_id=obj.id, trans_num=obj.transnumber,
                                                       objtype=obj.objtype, item_code=row.item_code,
                                                       inqty=row.quantity, uom=row.uom,
                                                       warehouse=row.whsecode, warehouse2=row.whsecode,
                                                       transdate=obj.transdate, created_by=obj.created_by,
                                                       reference=obj.reference, reference2=obj.reference2,
                                                       remarks=obj.remarks, series_code=obj.seriescode,
                                                       updated_by=obj.updated_by)

                            # add back the void quantity
                            whseinv = WhseInv.query.filter_by(warehouse=row.whsecode,
                                                              item_code=row.item_code).first()
                            whseinv.quantity += row.quantity

                            # add to session
                            db.session.add_all([inv_trans, whseinv, cust])

        else:
            continue
