from datetime import datetime
from bakery_app import db
from bakery_app.inventory.models import WhseInv, InvTransaction
from sqlalchemy import event


class ItemAdjustmentIn(db.Model):
    __tablename__ = "tblitem_adj_in"

    id = db.Column(db.Integer, primary_key=True)
    series = db.Column(db.Integer, db.ForeignKey('tblseries.id', ondelete='NO ACTION',
                                                 onupdate='NO ACTION'))  # series id
    seriescode = db.Column(db.String(50), nullable=False)  # series code
    transnumber = db.Column(db.Integer, nullable=False)  # series next_num
    transdate = db.Column(db.DateTime, nullable=False)
    reference = db.Column(db.String(100), nullable=False)  # seriescode + number
    objtype = db.Column(db.Integer, db.ForeignKey('tblobjtype.objtype'), nullable=False)
    docstatus = db.Column(db.String(10), default='C', nullable=False)
    sap_number = db.Column(db.Integer)
    remarks = db.Column(db.String(250))
    created_by = db.Column(db.Integer, db.ForeignKey('tbluser.id'))
    updated_by = db.Column(db.Integer, db.ForeignKey('tbluser.id'))
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.now)
    date_updated = db.Column(db.DateTime, nullable=False, default=datetime.now)


class ItemAdjustmentInRow(db.Model):
    __tablename__ = "tblitemadjinrow"

    id = db.Column(db.Integer, primary_key=True)
    adjustin_id = db.Column(db.Integer, db.ForeignKey('tblitem_adj_in.id', ondelete='CASCADE'), nullable=False)
    objtype = db.Column(db.Integer, nullable=False)
    item_code = db.Column(db.String(100), db.ForeignKey(
        'tblitems.item_code'), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    whsecode = db.Column(db.String(100), db.ForeignKey(
        'tblwhses.whsecode'), nullable=False)
    uom = db.Column(db.String(50), db.ForeignKey(
        'tbluom.code'), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('tbluser.id'))
    updated_by = db.Column(db.Integer, db.ForeignKey('tbluser.id'))
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.now)
    date_updated = db.Column(db.DateTime, nullable=False, default=datetime.now)


class ItemAdjustmentOut(db.Model):
    __tablename__ = "tblitem_adj_out"

    id = db.Column(db.Integer, primary_key=True)
    series = db.Column(db.Integer, db.ForeignKey('tblseries.id', ondelete='NO ACTION',
                                                 onupdate='NO ACTION'))  # series id
    seriescode = db.Column(db.String(50), nullable=False)  # series code
    transnumber = db.Column(db.Integer, nullable=False)  # series next_num
    transdate = db.Column(db.DateTime, nullable=False)
    # seriescode + number
    reference = db.Column(db.String(100), nullable=False)
    objtype = db.Column(db.Integer, db.ForeignKey(
        'tblobjtype.objtype'), nullable=False)
    docstatus = db.Column(db.String(10), default='O', nullable=False)
    sap_number = db.Column(db.Integer)
    remarks = db.Column(db.String(250))
    created_by = db.Column(db.Integer, db.ForeignKey('tbluser.id'))
    updated_by = db.Column(db.Integer, db.ForeignKey('tbluser.id'))
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.now)
    date_updated = db.Column(db.DateTime, nullable=False, default=datetime.now)


class ItemAdjustmentOutRow(db.Model):
    __tablename__ = "tblitemadjoutrow"

    id = db.Column(db.Integer, primary_key=True)
    adjustout_id = db.Column(db.Integer, db.ForeignKey('tblitem_adj_out.id', ondelete='CASCADE'), nullable=False)
    objtype = db.Column(db.Integer, nullable=False)
    item_code = db.Column(db.String(100), db.ForeignKey(
        'tblitems.item_code'), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    whsecode = db.Column(db.String(100), db.ForeignKey(
        'tblwhses.whsecode'), nullable=False)
    uom = db.Column(db.String(50), db.ForeignKey(
        'tbluom.code'), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('tbluser.id'))
    updated_by = db.Column(db.Integer, db.ForeignKey('tbluser.id'))
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.now)
    date_updated = db.Column(db.DateTime, nullable=False, default=datetime.now)


@event.listens_for(db.session, "before_flush")
def insert_update(*args):
    sess = args[0]
    for obj in sess.new:

        # Insert to InvTransaction and Update Whse Inv if Adjustment In transaction
        if isinstance(obj, ItemAdjustmentInRow):
            header = ItemAdjustmentIn.query.filter_by(
                id=obj.adjustin_id).first()
            whseinv = WhseInv.query.filter_by(warehouse=obj.whsecode,
                                              item_code=obj.item_code).first()
            whseinv.quantity += obj.quantity

            invtrans = InvTransaction(series_code=header.seriescode, trans_id=obj.adjustin_id,
                                      trans_num=header.transnumber, objtype=header.objtype, item_code=obj.item_code,
                                      inqty=obj.quantity, uom=obj.uom, warehouse=obj.whsecode, warehouse2=obj.whsecode,
                                      transdate=header.transdate, created_by=header.created_by,
                                      updated_by=header.updated_by,
                                      reference=header.reference, sap_number=header.sap_number)

            db.session.add_all([whseinv, invtrans])

        else:
            continue
