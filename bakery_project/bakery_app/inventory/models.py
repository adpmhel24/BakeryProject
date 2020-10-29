from datetime import datetime
from sqlalchemy import event
from bakery_app import db, ma
from sqlalchemy import cast, and_
from bakery_app.master_data.models import Items
from bakery_app.branches.models import Warehouses


class WhseInv(db.Model):
    __tablename__ = "tblwhseinv"

    id = db.Column(db.Integer, primary_key=True)
    item_code = db.Column(db.String(100), db.ForeignKey('tblitems.item_code',
                                                        ondelete='CASCADE', onupdate='CASCADE'), nullable=False)
    quantity = db.Column(db.Float, nullable=False, default=0.00)
    warehouse = db.Column(db.String(100), db.ForeignKey('tblwhses.whsecode',
                                                        ondelete='CASCADE', onupdate='CASCADE'), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id',
                                                     ondelete='NO ACTION'), nullable=False)
    updated_by = db.Column(db.Integer, db.ForeignKey('user.id'))

    item = db.relationship("Items", backref="whseinv", lazy=True)

    def __repr__(self):
        return f"WhseInv('{self.item_code}', '{self.item_name}', '{self.quantity}')"


class InvTransaction(db.Model):
    __tablename__ = "tblwhstransaction"

    id = db.Column(db.Integer, primary_key=True)
    series_code = db.Column(db.String(50), nullable=False)  # series code
    trans_id = db.Column(db.Integer, nullable=False)  # transaction id
    trans_num = db.Column(db.Integer, nullable=False)  # transaction number
    objtype = db.Column(db.Integer, nullable=False)  # objtype
    item_code = db.Column(db.String(100), db.ForeignKey('tblitems.item_code',
                                                        ondelete='CASCADE'), nullable=False)
    inqty = db.Column(db.Float, nullable=False, default=0)
    outqty = db.Column(db.Float, nullable=False, default=0)
    uom = db.Column(db.String(50), db.ForeignKey('tbluom.code'),
                    nullable=False)
    warehouse = db.Column(db.String(100), nullable=False)
    warehouse2 = db.Column(db.String(100), nullable=False)
    transdate = db.Column(db.DateTime, nullable=False, default=datetime.now)
    reference = db.Column(db.String(100))
    reference2 = db.Column(db.String(100))
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.now)
    date_updated = db.Column(db.DateTime, nullable=False, default=datetime.now)
    created_by = db.Column(
        db.Integer, db.ForeignKey('user.id'), nullable=False)
    updated_by = db.Column(
        db.Integer, db.ForeignKey('user.id'), nullable=False)
    sap_number = db.Column(db.Integer, nullable=True, default=None)
    remarks = db.Column(db.String(150))


class TransferHeader(db.Model):
    __tablename__ = "tbltransfer"

    id = db.Column(db.Integer, primary_key=True)
    series = db.Column(db.Integer, db.ForeignKey('tblseries.id', ondelete='NO ACTION',
                                                 onupdate='NO ACTION'))  # series id
    seriescode = db.Column(db.String(50), nullable=False)  # series code
    transnumber = db.Column(db.Integer, nullable=False)  # series next_num
    reference = db.Column(db.String(100))  # Objcode + Series Next Num
    objtype = db.Column(db.Integer, nullable=False, default=1)
    sap_number = db.Column(db.Integer, nullable=True, default=None)
    docstatus = db.Column(db.String(10), nullable=False, default='O')
    transdate = db.Column(db.DateTime)
    reference2 = db.Column(db.String(100))
    remarks = db.Column(db.String(250))
    created_by = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='NO ACTION'),
                           nullable=False)
    updated_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.now)
    date_updated = db.Column(db.DateTime, nullable=False, default=datetime.now)
    transrow = db.relationship(
        "TransferRow", back_populates="transheader", lazy=True)


class TransferRow(db.Model):
    __tablename__ = "tbltransrow"

    id = db.Column(db.Integer, primary_key=True, unique=True)
    transfer_id = db.Column(db.Integer, db.ForeignKey(
        'tbltransfer.id', ondelete='CASCADE'), nullable=False)
    transnumber = db.Column(db.Integer, nullable=False)
    objtype = db.Column(db.Integer, nullable=False, default=1)
    from_whse = db.Column(db.String(100), db.ForeignKey('tblwhses.whsecode',
                                                        ondelete='CASCADE', onupdate='CASCADE'), nullable=False)
    to_whse = db.Column(db.String(100), db.ForeignKey(
        'tblwhses.whsecode'), nullable=False)
    item_code = db.Column(db.String(100), db.ForeignKey('tblitems.item_code',
                                                        ondelete='CASCADE', onupdate='CASCADE'), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    uom = db.Column(db.String(50), db.ForeignKey(
        'tbluom.code'), nullable=False)
    sap_number = db.Column(db.Integer, nullable=True, default=None)
    confirm = db.Column(db.Boolean, nullable=False, default=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id',
                                                     ondelete='NO ACTION'), nullable=False)
    updated_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.now)
    date_updated = db.Column(db.DateTime, nullable=False, default=datetime.now)
    status = db.Column(db.Integer, default=1)  # 1 for not cancel, 2 for cancel
    transheader = db.relationship(
        "TransferHeader", back_populates="transrow", lazy=True)


class ReceiveHeader(db.Model):
    __tablename__ = "tblreceive"

    id = db.Column(db.Integer, primary_key=True)
    series = db.Column(db.Integer, db.ForeignKey('tblseries.id', ondelete='NO ACTION',
                                                 onupdate='NO ACTION'))  # series id
    seriescode = db.Column(db.String(50), nullable=False)  # series code
    transnumber = db.Column(db.Integer, nullable=False)  # series next_num
    base_id = db.Column(db.Integer)  # if from System Transfer
    objtype = db.Column(db.Integer, nullable=False, default=2)
    sap_number = db.Column(db.Integer, nullable=True, default=None)
    docstatus = db.Column(db.String(10), nullable=False, default='O')
    transtype = db.Column(db.String(100))
    transdate = db.Column(db.DateTime)
    reference = db.Column(db.String(100))
    reference2 = db.Column(db.String(100))
    remarks = db.Column(db.String(250), nullable=True)
    supplier = db.Column(db.String(150))
    created_by = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='NO ACTION'),
                           nullable=False)
    updated_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.now)
    date_updated = db.Column(db.DateTime, nullable=False, default=datetime.now)
    recrow = db.relationship(
        "ReceiveRow", back_populates="recheader", lazy=True)


class ReceiveRow(db.Model):
    __tablename__ = "tblrecrow"

    id = db.Column(db.Integer, primary_key=True, unique=True)
    receive_id = db.Column(db.Integer, db.ForeignKey(
        'tblreceive.id', ondelete='CASCADE'), nullable=False)
    transnumber = db.Column(db.Integer, nullable=False)
    objtype = db.Column(db.Integer, nullable=False, default=2)
    from_whse = db.Column(db.String(100))
    to_whse = db.Column(db.String(100), db.ForeignKey('tblwhses.whsecode',
                                                      ondelete='CASCADE', onupdate='CASCADE'), nullable=False)
    item_code = db.Column(db.String(100), db.ForeignKey('tblitems.item_code',
                                                        ondelete='CASCADE', onupdate='CASCADE'), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    actualrec = db.Column(db.Float, nullable=False)
    uom = db.Column(db.String(50), db.ForeignKey(
        'tbluom.code'), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id',
                                                     ondelete='NO ACTION'), nullable=False)
    updated_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.now)
    date_updated = db.Column(db.DateTime, nullable=False, default=datetime.now)
    sap_number = db.Column(db.Integer, nullable=True, default=None)
    # 1 = for not cancel, 2 = for cancel
    status = db.Column(db.Integer, default=1)
    recheader = db.relationship(
        "ReceiveHeader", back_populates="recrow", lazy=True)


class ItemRequest(db.Model):
    __tablename__ = "tblitemreq"

    id = db.Column(db.Integer, primary_key=True)
    series = db.Column(db.Integer, db.ForeignKey(
        'tblseries.id', ondelete='NO ACTION', onupdate='NO ACTION'))
    transnumber = db.Column(db.Integer, nullable=False)
    transdate = db.Column(db.DateTime, nullable=False, default=datetime.now)
    duedate = db.Column(db.DateTime, nullable=False, default=datetime.now)
    from_whse = db.Column(db.String(100), db.ForeignKey(
        'tblwhses.whsecode', onupdate='NO ACTION'), nullable=False)
    to_whse = db.Column(db.String(100), db.ForeignKey(
        'tblwhses.whsecode', onupdate='NO ACTION'), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id',
                                                     ondelete='NO ACTION'), nullable=False)
    updated_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.now)
    date_updated = db.Column(db.DateTime, nullable=False, default=datetime.now)
    rows = db.relationship('ItemRequestRow', backref='rows', lazy=True)


class ItemRequestRow(db.Model):
    __tablename__ = "tblitemreqrow"

    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey(
        'tblitemreq.id', ondelete='CASCADE'), nullable=False)
    from_whse = db.Column(db.String(100), db.ForeignKey('tblwhses.whsecode',
                                                        ondelete='CASCADE', onupdate='CASCADE'), nullable=False)
    to_whse = db.Column(db.String(100), db.ForeignKey(
        'tblwhses.whsecode'), nullable=False)
    item_code = db.Column(db.String(100), db.ForeignKey('tblitems.item_code',
                                                        ondelete='CASCADE', onupdate='CASCADE'), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    uom = db.Column(db.String(50), db.ForeignKey(
        'tbluom.code'), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id',
                                                     ondelete='NO ACTION'), nullable=False)
    updated_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.now)
    date_updated = db.Column(db.DateTime, nullable=False, default=datetime.now)


@event.listens_for(db.session, "before_flush")
def insert_update(*args):
    sess = args[0]
    for obj in sess.new:

        # Insert Item to WhseInv
        if isinstance(obj, Items):
            whses = Warehouses.query.all()
            for i in whses:
                whseinv = WhseInv(item_code=obj.item_code, warehouse=i.whsecode,
                                  created_by=obj.created_by, updated_by=obj.updated_by)
                db.session.add(whseinv)

        # Insert Warehouse to WhseInv
        elif isinstance(obj, Warehouses):
            items = Items.query.all()
            for i in items:
                whseinv = WhseInv(item_code=i.item_code, warehouse=obj.whsecode,
                                  created_by=obj.created_by, updated_by=obj.updated_by)
                db.session.add(whseinv)

        # Insert to InvTransaction and Update Whse Inv
        elif isinstance(obj, TransferRow):

            t_h = TransferHeader.query.filter_by(id=obj.transfer_id).first()
            whseinv = WhseInv.query.filter_by(warehouse=obj.from_whse,
                                              item_code=obj.item_code).first()
            whseinv.quantity -= obj.quantity

            invtrans = InvTransaction(series_code=t_h.seriescode, trans_id=obj.transfer_id,
                                      trans_num=obj.transnumber, objtype=t_h.objtype, item_code=obj.item_code,
                                      outqty=obj.quantity, uom=obj.uom, warehouse=obj.from_whse, warehouse2=obj.to_whse,
                                      transdate=t_h.transdate, created_by=t_h.created_by, updated_by=t_h.updated_by,
                                      reference=t_h.reference, sap_number=obj.sap_number)

            db.session.add_all([whseinv, invtrans])

        # Receive Transaction
        # Insert to InvTransaction
        # Update the qty of WhseInv
        elif isinstance(obj, ReceiveRow):
            r_h = ReceiveHeader.query.filter_by(id=obj.receive_id).first()

            whseinv = WhseInv.query.filter_by(warehouse=obj.to_whse,
                                              item_code=obj.item_code).first()
            whseinv.quantity += obj.actualrec

            invtrans = InvTransaction(series_code=r_h.seriescode, trans_id=obj.receive_id,
                                      trans_num=obj.transnumber, objtype=r_h.objtype, item_code=obj.item_code,
                                      inqty=obj.actualrec, uom=obj.uom, warehouse=obj.to_whse, warehouse2=obj.from_whse,
                                      transdate=r_h.transdate, created_by=r_h.created_by, updated_by=r_h.updated_by,
                                      reference=r_h.reference, sap_number=obj.sap_number, reference2=r_h.reference2)

            db.session.add_all([whseinv, invtrans])
        else:
            continue

    # Update When Receive Transaction Canceled
    for obj in sess.dirty:
        if isinstance(obj, ReceiveHeader):
            receive_header = ReceiveHeader.query.get(obj.id)
            # check if the update is cancel and The header is not cancel
            if obj.docstatus == 'N' and receive_header.docstatus != 'N':
                rec_row = ReceiveRow.query.filter_by(receive_id=obj.id).all()

                for row in rec_row:
                    # add to inventory transaction the void transaction
                    inv_trans = InvTransaction(trans_id=obj.id, trans_num=obj.transnumber,
                                               objtype=obj.objtype, item_code=row.item_code,
                                               outqty=row.actualrec, uom=row.uom,
                                               warehouse=row.to_whse, warehouse2=row.from_whse,
                                               transdate=obj.transdate, created_by=obj.created_by,
                                               reference=obj.reference, reference2=obj.reference2,
                                               remarks=obj.remarks, series_code=obj.seriescode,
                                               updated_by=obj.updated_by)

                    # deduct the canceled qty to whse
                    whseinv = WhseInv.query.filter_by(warehouse=obj.to_whse,
                                                      item_code=obj.item_code).first()
                    whseinv.quantity -= obj.actualrec

                    row.status = 2

                    db.session.add_all([inv_trans, whseinv, row])

        if isinstance(obj, TransferHeader):
            if obj.docstatus == 'N':
                trans_row = TransferHeader.query.filter_by(
                    transfer_id=obj.id).all()

                for row in trans_row:
                    # add to inventory transaction the void transaction
                    inv_trans = InvTransaction(trans_id=obj.id, trans_num=obj.transnumber,
                                               objtype=obj.objtype, item_code=row.item_code,
                                               inqty=row.actualrec, uom=row.uom,
                                               warehouse=row.from_whse, warehouse2=row.to_whse,
                                               transdate=obj.transdate, created_by=obj.created_by,
                                               reference=obj.reference, reference2=obj.reference2,
                                               remarks=obj.remarks, series_code=obj.seriescode,
                                               updated_by=obj.updated_by)

                    # deduct the canceled qty to whse
                    whseinv = WhseInv.query.filter_by(warehouse=obj.from_whse,
                                                      item_code=obj.item_code).first()
                    whseinv.quantity += obj.actualrec

                    row.status = 2

                    db.session.add_all([inv_trans, whseinv, row])

        else:
            continue
