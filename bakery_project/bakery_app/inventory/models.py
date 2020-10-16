from datetime import datetime
from sqlalchemy import event
from bakery_app import db, ma
from bakery_app.branches.models import Warehouses
from sqlalchemy import cast, and_


class Items(db.Model):
    __tablename__ = "tblitems"

    id = db.Column(db.Integer, primary_key=True)
    item_code = db.Column(db.String(100), unique=True, nullable=False)
    item_name = db.Column(db.String(150), nullable=False)  
    item_group = db.Column(db.String(50), db.ForeignKey('tblitemgrp.code', ondelete='CASCADE', \
            onupdate='CASCADE'), nullable=False)
    uom = db.Column(db.String(50), db.ForeignKey('tbluom.code', ondelete='CASCADE', \
            onupdate='CASCADE'), nullable=False)
    min_stock = db.Column(db.Float, nullable=False, default=0.00)
    max_stock = db.Column(db.Float, nullable=False, default=0.00)
    price = db.Column(db.Float, nullable=False, default=0.00)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='NO ACTION'), \
            nullable=False)
    updated_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.now)
    date_updated = db.Column(db.DateTime, nullable=False, default=datetime.now)
    
    def __repr__(self):
        return f"Items('{self.item_code}', '{self.item_name}"


class ItemGroup(db.Model):
    __tablename__ = "tblitemgrp"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), nullable=False, unique=True)
    description = db.Column(db.String(100), nullable=False, unique=True)
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.now)
    date_updated = db.Column(db.DateTime, nullable=False, default=datetime.now)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='NO ACTION'), \
            nullable=False)
    updated_by = db.Column(db.Integer, db.ForeignKey('user.id'))

    items = db.relationship('Items', backref='itemgroup', lazy=True)

    def __repr__(self):
        return f"ItemGroup('{self.code}', '{self.description}')"


class UnitOfMeasure(db.Model):
    __tablename__ = "tbluom"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), nullable=False, unique=True)
    description = db.Column(db.String(100), nullable=False, unique=True)
    date_create = db.Column(db.DateTime, nullable=False, default=datetime.now)
    date_updated = db.Column(db.DateTime, nullable=False, default=datetime.now)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='NO ACTION'), \
            nullable=False)
    updated_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    items = db.relationship('Items', backref='unitofmeasure', lazy=True)

    def __repr__(self):
        return f"UnitOfMeasure('{self.code}', '{self.description}')"


class WhseInv(db.Model):
    __tablename__ = "tblwhseinv"

    id = db.Column(db.Integer, primary_key=True)
    item_code = db.Column(db.String(100), db.ForeignKey('tblitems.item_code', \
                ondelete='CASCADE', onupdate='CASCADE'), nullable=False)
    quantity = db.Column(db.Float, nullable=False, default=0.00)
    warehouse = db.Column(db.String(100), db.ForeignKey('tblwhses.whsecode', \
                ondelete='CASCADE', onupdate='CASCADE'), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id', \
                ondelete='NO ACTION'), nullable=False)
    updated_by = db.Column(db.Integer, db.ForeignKey('user.id'))

    def __repr__(self):
        return f"WhseInv('{self.item_code}', '{self.item_name}', '{self.quantity}')"


class InvTransaction(db.Model):
    __tablename__ = "tblwhstransaction"

    id = db.Column(db.Integer, primary_key=True)
    series_code = db.Column(db.String(50), nullable=False) # series code
    trans_id = db.Column(db.Integer, nullable=False)  # transaction id  
    trans_num = db.Column(db.Integer, nullable=False) # transaction number
    objtype = db.Column(db.Integer, nullable=False) # objtype
    item_code = db.Column(db.String(100), db.ForeignKey('tblitems.item_code',\
            ondelete='CASCADE'), nullable=False)
    inqty = db.Column(db.Float, nullable=False, default=0)
    outqty = db.Column(db.Float, nullable=False, default=0)
    uom = db.Column(db.String(50), db.ForeignKey('tbluom.code'), \
            nullable=False)
    warehouse = db.Column(db.String(100), nullable=False)
    warehouse2 = db.Column(db.String(100), nullable=False)
    transdate = db.Column(db.DateTime, nullable=False, default=datetime.now)
    reference = db.Column(db.String(100))
    reference2 = db.Column(db.String(100))
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.now)
    date_updated = db.Column(db.DateTime, nullable=False, default=datetime.now)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    updated_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    sap_number = db.Column(db.Integer, nullable=True, default=None)
    remarks = db.Column(db.String(150))



class TransferHeader(db.Model):
    __tablename__ = "tbltransfer"

    id = db.Column(db.Integer, primary_key=True)
    series = db.Column(db.Integer, db.ForeignKey('tblseries.id', ondelete='NO ACTION', \
            onupdate='NO ACTION')) # series id
    seriescode = db.Column(db.String(50), nullable=False) # series code
    transnumber = db.Column(db.Integer, nullable=False) # series next_num
    objtype = db.Column(db.Integer, nullable=False, default=1)
    sap_number = db.Column(db.Integer, nullable=True, default=None)
    docstatus = db.Column(db.String(10), nullable=False, default='O')
    transdate = db.Column(db.DateTime)
    reference = db.Column(db.String(100))
    reference2 = db.Column(db.String(100))
    remarks = db.Column(db.String(250), nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='NO ACTION'), \
            nullable=False)
    updated_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.now)
    date_updated = db.Column(db.DateTime, nullable=False, default=datetime.now)
    transrow = db.relationship("TransferRow", back_populates="transheader", lazy=True)


class TransferRow(db.Model):
    __tablename__ = "tbltransrow"

    id = db.Column(db.Integer, primary_key=True, unique=True)
    transfer_id = db.Column(db.Integer, db.ForeignKey('tbltransfer.id', ondelete='CASCADE'), nullable=False)
    transnumber = db.Column(db.Integer, nullable=False)
    objtype = db.Column(db.Integer, nullable=False, default=1)
    from_whse = db.Column(db.String(100), db.ForeignKey('tblwhses.whsecode', \
                ondelete='CASCADE', onupdate='CASCADE'), nullable=False)
    to_whse = db.Column(db.String(100), db.ForeignKey('tblwhses.whsecode'), nullable=False)
    item_code = db.Column(db.String(100), db.ForeignKey('tblitems.item_code', \
                ondelete='CASCADE', onupdate='CASCADE'), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    uom = db.Column(db.String(50), db.ForeignKey('tbluom.code'), nullable=False)
    sap_number = db.Column(db.Integer, nullable=True, default=None)
    confirm = db.Column(db.Boolean, nullable=False, default=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id', \
                ondelete='NO ACTION'), nullable=False)
    updated_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.now)
    date_updated = db.Column(db.DateTime, nullable=False, default=datetime.now)
    transheader = db.relationship("TransferHeader", back_populates="transrow", lazy=True)


class ReceiveHeader(db.Model):
    __tablename__ = "tblreceive"

    id = db.Column(db.Integer, primary_key=True)
    series = db.Column(db.Integer, db.ForeignKey('tblseries.id', ondelete='NO ACTION', \
            onupdate='NO ACTION')) # series id
    seriescode = db.Column(db.String(50), nullable=False) # series code
    transnumber = db.Column(db.Integer, nullable=False) # series next_num
    objtype = db.Column(db.Integer, nullable=False, default=2)
    sap_number = db.Column(db.Integer, nullable=True, default=None)
    docstatus = db.Column(db.String(10), nullable=False, default='O')
    transtype = db.Column(db.String(100))
    transdate = db.Column(db.DateTime)
    reference = db.Column(db.String(100))
    reference2 = db.Column(db.String(100))
    remarks = db.Column(db.String(250), nullable=True)
    base_id = db.Column(db.Integer)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='NO ACTION'), \
            nullable=False)
    updated_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.now)
    date_updated = db.Column(db.DateTime, nullable=False, default=datetime.now)
    recrow = db.relationship("ReceiveRow", back_populates="recheader", lazy=True)


class ReceiveRow(db.Model):
    __tablename__ = "tblrecrow"

    id = db.Column(db.Integer, primary_key=True, unique=True)
    receive_id = db.Column(db.Integer, db.ForeignKey('tblreceive.id', ondelete='CASCADE'), nullable=False)
    transnumber = db.Column(db.Integer, nullable=False)
    objtype = db.Column(db.Integer, nullable=False, default=2)
    from_whse = db.Column(db.String(100))
    to_whse = db.Column(db.String(100), db.ForeignKey('tblwhses.whsecode', \
                ondelete='CASCADE', onupdate='CASCADE'), nullable=False)
    item_code = db.Column(db.String(100), db.ForeignKey('tblitems.item_code', \
                ondelete='CASCADE', onupdate='CASCADE'), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    actualrec = db.Column(db.Float, nullable=False)
    uom = db.Column(db.String(50), db.ForeignKey('tbluom.code'), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id', \
                ondelete='NO ACTION'), nullable=False)
    updated_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.now)
    date_updated = db.Column(db.DateTime, nullable=False, default=datetime.now)
    sap_number = db.Column(db.Integer, nullable=True, default=None)
    recheader = db.relationship("ReceiveHeader", back_populates="recrow", lazy=True)   



class ItemRequest(db.Model):
    __tablename__ = "tblitemreq"

    id = db.Column(db.Integer, primary_key=True)
    series = db.Column(db.Integer, db.ForeignKey('tblseries.id', ondelete='NO ACTION', onupdate='NO ACTION'))
    transnumber = db.Column(db.Integer, nullable=False)
    transdate = db.Column(db.DateTime, nullable=False, default=datetime.now)
    duedate = db.Column(db.DateTime, nullable=False, default=datetime.now)
    from_whse = db.Column(db.String(100), db.ForeignKey('tblwhses.whsecode', onupdate='NO ACTION'), nullable=False)
    to_whse = db.Column(db.String(100), db.ForeignKey('tblwhses.whsecode', onupdate='NO ACTION'), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id', \
                ondelete='NO ACTION'), nullable=False)
    updated_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.now)
    date_updated = db.Column(db.DateTime, nullable=False, default=datetime.now)
    rows = db.relationship('ItemRequestRow', backref='rows', lazy=True)

class ItemRequestRow(db.Model):
    __tablename__ = "tblitemreqrow"

    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey('tblitemreq.id', ondelete='CASCADE'), nullable=False)
    from_whse = db.Column(db.String(100), db.ForeignKey('tblwhses.whsecode', \
                ondelete='CASCADE', onupdate='CASCADE'), nullable=False)
    to_whse = db.Column(db.String(100), db.ForeignKey('tblwhses.whsecode'), nullable=False)
    item_code = db.Column(db.String(100), db.ForeignKey('tblitems.item_code', \
                ondelete='CASCADE', onupdate='CASCADE'), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    uom = db.Column(db.String(50), db.ForeignKey('tbluom.code'), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id', \
                ondelete='NO ACTION'), nullable=False)
    updated_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.now)
    date_updated = db.Column(db.DateTime, nullable=False, default=datetime.now)
 
@event.listens_for(db.session, "before_flush")
def insert(*args):
    sess = args[0]
    for obj in sess.new:

        if isinstance(obj, Items):
            whses = Warehouses.query.all()
            for i in whses:
                whseinv = WhseInv(item_code=obj.item_code, warehouse=i.__dict__['whsecode'], \
                        created_by=obj.created_by, updated_by=obj.updated_by)
                db.session.add(whseinv)

        elif isinstance(obj, Warehouses):
            items = Items.query.all()
            for i in items:
                whseinv = WhseInv(item_code=i.__dict__['item_code'], warehouse=obj.whsecode,\
                    created_by=obj.created_by, updated_by=obj.updated_by)
                db.session.add(whseinv)

        elif isinstance(obj, TransferRow):

            t_h = TransferHeader.query.filter_by(id=obj.transfer_id).first()
            whseinv = WhseInv.query.filter_by(warehouse=obj.from_whse,\
                    item_code=obj.item_code).first()
            whseinv.quantity -= obj.quantity

            invtrans = InvTransaction(series_code=t_h.seriescode, trans_id = obj.transfer_id, \
                trans_num=obj.transnumber, objtype=t_h.objtype, item_code=obj.item_code, \
                outqty=obj.quantity, uom=obj.uom, warehouse=obj.from_whse, warehouse2=obj.to_whse, \
                transdate=t_h.transdate, created_by=t_h.created_by, updated_by=t_h.updated_by, \
                reference=t_h.reference, sap_number=obj.sap_number)
                
            db.session.add_all([whseinv, invtrans])

        elif isinstance(obj, ReceiveRow):
            r_h = ReceiveHeader.query.filter_by(id=obj.receive_id).first()
            
            # try:
            whseinv = WhseInv.query.filter_by(warehouse=obj.to_whse,\
                    item_code=obj.item_code).first()
            whseinv.quantity += obj.actualrec

            invtrans = InvTransaction(series_code=r_h.seriescode, trans_id = obj.receive_id, \
                trans_num=obj.transnumber, objtype=r_h.objtype, item_code=obj.item_code, \
                inqty=obj.actualrec, uom=obj.uom, warehouse=obj.to_whse, warehouse2=obj.from_whse, \
                transdate=r_h.transdate, created_by=r_h.created_by, updated_by=r_h.updated_by, \
                reference=r_h.reference, sap_number=obj.sap_number, reference2=r_h.reference2)

            db.session.add_all([whseinv, invtrans])   
            # except Exception as err:
            #     raise Exception(f"{err}")

        else:
            continue


class ItemsSchema(ma.SQLAlchemySchema):
    class Meta:
        model = Items
        ordered = True

    id = ma.auto_field()
    item_code = ma.auto_field()
    item_name = ma.auto_field()
    item_group = ma.auto_field()
    uom = ma.auto_field()
    min_stock = ma.auto_field()
    max_stock = ma.auto_field()
    price = ma.auto_field()
    date_created = ma.auto_field()
    date_updated = ma.auto_field()

class ItemGroupSchema(ma.SQLAlchemySchema):
    class Meta:
        model = ItemGroup
        ordered = True
    
    id = ma.auto_field()
    code = ma.auto_field()
    description = ma.auto_field()
    date_created = ma.auto_field()
    date_updated = ma.auto_field()

class UomSchema(ma.SQLAlchemySchema):
    class Meta:
        model = UnitOfMeasure
        ordered = True

    id = ma.auto_field()
    code = ma.auto_field()
    description = ma.auto_field()
    date_create = ma.auto_field()
    date_updated = ma.auto_field()
    created_by = ma.auto_field()
    updated_by = ma.auto_field()

class WhseInvSchema(ma.SQLAlchemySchema):
    class Meta:
        model = WhseInv
        ordered = True
    
    id = ma.auto_field()
    item_code = ma.auto_field()
    quantity = ma.auto_field()
    warehouse = ma.auto_field()
    created_by = ma.auto_field()
    updated_by = ma.auto_field()

class InvTransactionSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = InvTransaction
        ordered = True

class TransferRowSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = TransferRow
        ordered = True
        include_fk = True

class TransferHeaderSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = TransferHeader
        ordered = True
        load_instance = True

    transrow = ma.Nested(TransferRowSchema, many=True)

class ReceiveRowSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = ReceiveRow
        ordered = True
        include_fk = True

class ReceiveHeaderSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = ReceiveHeader
        ordered = True
        include_fk = True
    
    recrow = ma.Nested(ReceiveRowSchema, many=True)

