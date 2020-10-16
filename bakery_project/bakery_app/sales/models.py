from datetime import datetime
from bakery_app import db, ma
from bakery_app.inventory.models import InvTransaction, WhseInv
from sqlalchemy import event


class SalesHeader(db.Model):
    __tablename__ = "tblsales"

    id = db.Column(db.Integer, primary_key=True)
    docstatus = db.Column(db.String(30), default='Open')
    seriescode = db.Column(db.String(50), nullable=False)
    transnumber = db.Column(db.Integer, nullable=False) 
    transdate = db.Column(db.DateTime, nullable=False, default=datetime.now)
    cust_code = db.Column(db.String(100), db.ForeignKey('tblcustomer.code', \
            ondelete='CASCADE', onupdate='CASCADE'), nullable=False)
    cust_name = db.Column(db.String(100), nullable=False)
    objtype = db.Column(db.Integer, db.ForeignKey('tblobjtype.objtype'),\
            nullable=False)
    remarks = db.Column(db.String(250))
    transtype = db.Column(db.String(50), db.ForeignKey('tblsalestype.code'),nullable=False) # if cash, pickup, delivery, ar
    delfee = db.Column(db.Float, default=0.00)
    discprcnt = db.Column(db.Float, nullable=False, default=0.00)
    disc_amount = db.Column(db.Float, nullable=False, default=0.00)
    gross = db.Column(db.Float, nullable=False, default=0.00)
    gc_amount = db.Column(db.Float, nullable=False, default=0.00)
    doctotal = db.Column(db.Float, nullable=False, default=0.00)
    reference = db.Column(db.String(100))
    reference2 = db.Column(db.String(100))
    tenderamt = db.Column(db.Float, default=0.00)
    sap_number = db.Column(db.Integer)
    appliedamt = db.Column(db.Float, default=0.00)
    change = db.Column(db.Float, default=0.00)
    amount_due = db.Column(db.Float, default=0.00)
    void = db.Column(db.Boolean, nullable=True, default=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    updated_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.now)
    date_updated = db.Column(db.DateTime, nullable=False, default=datetime.now)

    salesrow = db.relationship("SalesRow", back_populates="salesheader", lazy=True)


class SalesRow(db.Model):
    __tablename__ = "tblsalesrow"

    id = db.Column(db.Integer, primary_key=True)
    sales_id = db.Column(db.Integer, db.ForeignKey('tblsales.id', ondelete='NO ACTION',\
            onupdate='CASCADE'))
    item_code = db.Column(db.String(100), db.ForeignKey('tblitems.item_code',\
            ondelete='NO ACTION', onupdate='NO ACTION'))
    quantity = db.Column(db.Float, nullable=False, default=0.00)
    whsecode = db.Column(db.String(100), db.ForeignKey('tblwhses.whsecode',\
            onupdate='CASCADE'), nullable=False)
    uom = db.Column(db.String(50), db.ForeignKey('tbluom.code', onupdate='CASCADE'))
    unit_price = db.Column(db.Float, nullable=False)
    disc_amount = db.Column(db.Float, nullable=False, default=0.00) 
    discprcnt = db.Column(db.Float, nullable=False, default=0.00)
    gross = db.Column(db.Float, nullable=False, default=0.00)
    linetotal = db.Column(db.Float, nullable=False, default=0.00)
    free = db.Column(db.Boolean, default=False)

    salesheader = db.relationship("SalesHeader", back_populates="salesrow", lazy=True)


class PaymentType(db.Model):
    __tablename__ = "tblpaymenttype"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), nullable=False, unique=True)
    description = db.Column(db.String(100), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    updated_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.now)
    date_updated = db.Column(db.DateTime, nullable=False, default=datetime.now)

class SalesType(db.Model):
    __tablename__ = "tblsalestype"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), nullable=False, unique=True)
    description = db.Column(db.String(100), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    updated_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.now)
    date_updated = db.Column(db.DateTime, nullable=False, default=datetime.now)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    updated_by = db.Column(db.Integer, db.ForeignKey('user.id'))

class DiscountType(db.Model):
    __tablename__ = "tbldscnttype"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), nullable=False, unique=True)
    description = db.Column(db.String(100), nullable=False)
    discount = db.Column(db.Float, nullable=False, default=0.00)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    updated_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.now)
    date_updated = db.Column(db.DateTime, nullable=False, default=datetime.now)

class DiscountedCustomer(db.Model):
    __tablename__ = "tbldisccust"

    id = db.Column(db.Integer, primary_key=True)
    senior_name = db.Column(db.String(100), nullable=False, unique=True)
    senior_id = db.Column(db.String(150), nullable=False)
    contact_number = db.Column(db.String(30))
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    updated_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.now)
    date_updated = db.Column(db.DateTime, nullable=False, default=datetime.now)

class PaymentTransaction(db.Model):
    __tablename__ = "tblpaymenttrans"

    id = db.Column(db.Integer, primary_key=True)
    baseid = db.Column(db.Integer, db.ForeignKey('tblsales.id',\
            ondelete='NO ACTION'))
    basenum = db.Column(db.Integer)
    cust_code = db.Column(db.String(100), nullable=False)
    payment_type = db.Column(db.String(50), db.ForeignKey('tblpaymenttype.code', \
            onupdate='CASCADE'), nullable=False)
    cash = db.Column(db.Float, nullable=False, default=0.00)
    gc = db.Column(db.Float, nullable=False, default=0.00)
    ecash = db.Column(db.Float, nullable=False, default=0.00)


class PaymentTypeSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = PaymentType
        ordered = True

class SalesTypeSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = SalesType
        ordered = True
        
class DiscountTypeSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = DiscountType
        ordered = True
    
class SalesRowSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = SalesRow
        ordered = True
        include_fk = True

class SalesHeaderSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = SalesHeader
        ordered = True
        include_fk = True
        load_instance = True

    salesrow = ma.Nested(SalesRowSchema, many=True)


    
@event.listens_for(db.session, "before_flush")
def order_amnts(*args):
    sess = args[0]
    
    for obj in sess.new:

        if isinstance(obj, SalesRow):
            sales = SalesHeader.query.filter_by(id=obj.sales_id).first()
            sales.gross += obj.linetotal
            sales.disc_amount = sales.gross * (sales.discprcnt / 100)
            sales.doctotal = sales.delfee + sales.gross - sales.disc_amount - sales.gc_amount
            sales.amount_due = sales.doctotal

            if sales.tenderamt >= sales.amount_due:
                sales.change = sales.tenderamt - sales.amount_due
                if sales.amount_due - sales.tenderamt < 0:
                    sales.amount_due =  0
                else:
                    sales.amount_due -= sales.tenderamt

            elif sales.tenderamt < sales.amount_due and sales.transtype != 'AR Sales':
                raise Exception("Tender amount is less than amount due!")

            inv_trans = InvTransaction(trans_id = sales.id, trans_num=sales.transnumber, \
                    objtype=sales.objtype, item_code=obj.item_code,\
                    outqty=obj.quantity, uom=obj.uom,\
                    warehouse=obj.whsecode, warehouse2=obj.whsecode,\
                    transdate=sales.transdate, created_by=sales.created_by,\
                    reference=sales.reference, reference2=sales.reference2,\
                    remarks=sales.remarks, series_code=sales.seriescode,\
                    updated_by=sales.updated_by)
            
            whseinv = WhseInv.query.filter_by(warehouse=obj.whsecode,\
                    item_code=obj.item_code).first()
            whseinv.quantity -= obj.quantity
            
            db.session.add_all([sales, inv_trans, whseinv])

        else:
            continue


@event.listens_for(db.session, "before_flush")
def update_whse_inv(*args):
    sess = args[0]

    for obj in sess.dirty:

        if isinstance(obj, SalesHeader):
            if obj.void == True:
                salesrow = SalesRow.query.filter(SalesRow.sales_id==obj.id).all()
                for row in salesrow:

                    # add to inventory transaction the void transaction
                    inv_trans = InvTransaction(trans_id = obj.id, trans_num=obj.transnumber, \
                        objtype=obj.objtype, item_code=row.item_code,\
                        inqty=row.quantity, uom=row.uom,\
                        warehouse=row.whsecode, warehouse2=row.whsecode,\
                        transdate=obj.transdate, created_by=obj.created_by,\
                        reference=obj.reference, reference2=obj.reference2,\
                        remarks=obj.remarks, series_code=obj.seriescode,\
                        updated_by=obj.updated_by)
                    
                    # add back the void quantity
                    whseinv = WhseInv.query.filter_by(warehouse=row.whsecode,\
                        item_code=row.item_code).first()
                    whseinv.quantity += row.quantity

                    # add to session
                    db.session.add_all([inv_trans, whseinv])
