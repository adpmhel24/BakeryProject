from datetime import datetime
from sqlalchemy import event, and_
from bakery_app import db
from bakery_app._helpers import get_model_changes
from bakery_app.sapb1.models import ITRow, ITHeader, PORow, POHeader


class WhseInv(db.Model):
    __tablename__ = "tblwhseinv"

    id = db.Column(db.Integer, primary_key=True)
    item_code = db.Column(db.String(100), db.ForeignKey('tblitems.item_code',
                                                        ondelete='CASCADE', onupdate='CASCADE'), nullable=False)
    quantity = db.Column(db.Float, nullable=False, default=0.00)
    warehouse = db.Column(db.String(100), db.ForeignKey('tblwhses.whsecode',
                                                        ondelete='CASCADE', onupdate='CASCADE'), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('tbluser.id',
                                                     ondelete='NO ACTION'), nullable=False)
    updated_by = db.Column(db.Integer, db.ForeignKey('tbluser.id'))

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
        db.Integer, db.ForeignKey('tbluser.id'), nullable=False)
    updated_by = db.Column(
        db.Integer, db.ForeignKey('tbluser.id'), nullable=False)
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
    objtype = db.Column(db.Integer, nullable=False)
    sap_number = db.Column(db.Integer, nullable=True, default=None)
    docstatus = db.Column(db.String(10), nullable=False, default='O')
    transdate = db.Column(db.DateTime)
    reference2 = db.Column(db.String(100))
    remarks = db.Column(db.String(250))
    created_by = db.Column(db.Integer, db.ForeignKey('tbluser.id', ondelete='NO ACTION'),
                           nullable=False)
    updated_by = db.Column(db.Integer, db.ForeignKey('tbluser.id'))
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
    objtype = db.Column(db.Integer, nullable=False)
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
    created_by = db.Column(db.Integer, db.ForeignKey('tbluser.id',
                                                     ondelete='NO ACTION'), nullable=False)
    updated_by = db.Column(db.Integer, db.ForeignKey('tbluser.id'))
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
    objtype = db.Column(db.Integer, nullable=False)
    sap_number = db.Column(db.Integer, nullable=True, default=None)
    docstatus = db.Column(db.String(10), nullable=False, default='O')
    transtype = db.Column(db.String(100))
    transdate = db.Column(db.DateTime)
    reference = db.Column(db.String(100))
    reference2 = db.Column(db.String(100))
    remarks = db.Column(db.String(250), nullable=True)
    supplier = db.Column(db.String(150))
    type2 = db.Column(db.String(100))
    created_by = db.Column(db.Integer, db.ForeignKey('tbluser.id', ondelete='NO ACTION'),
                           nullable=False)
    updated_by = db.Column(db.Integer, db.ForeignKey('tbluser.id'))
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
    objtype = db.Column(db.Integer, nullable=False)
    from_whse = db.Column(db.String(100))
    to_whse = db.Column(db.String(100), db.ForeignKey('tblwhses.whsecode',
                                                      ondelete='CASCADE', onupdate='CASCADE'), nullable=False)
    item_code = db.Column(db.String(100), db.ForeignKey('tblitems.item_code',
                                                        ondelete='CASCADE', onupdate='CASCADE'), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    actualrec = db.Column(db.Float, nullable=False)
    uom = db.Column(db.String(50), db.ForeignKey(
        'tbluom.code'), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('tbluser.id',
                                                     ondelete='NO ACTION'), nullable=False)
    updated_by = db.Column(db.Integer, db.ForeignKey('tbluser.id'))
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.now)
    date_updated = db.Column(db.DateTime, nullable=False, default=datetime.now)
    sap_number = db.Column(db.Integer, nullable=True, default=None)
    # 1 = for not cancel, 2 = for cancel
    status = db.Column(db.Integer, default=1)
    recheader = db.relationship("ReceiveHeader", back_populates="recrow", lazy=True)


@event.listens_for(db.session, "before_flush")
def insert_update(*args):
    sess = args[0]
    for obj in sess.new:

        # Transfer Transaction 
        # Insert to InvTransaction and Update Whse Inv
        if isinstance(obj, TransferRow):

            t_h = TransferHeader.query.filter_by(id=obj.transfer_id).first()
            whseinv = WhseInv.query.filter_by(warehouse=obj.from_whse,
                                              item_code=obj.item_code).first()
            whseinv.quantity -= obj.quantity

            invtrans = InvTransaction(series_code=t_h.seriescode, trans_id=obj.transfer_id,
                                      trans_num=t_h.transnumber, objtype=t_h.objtype, item_code=obj.item_code,
                                      outqty=obj.quantity, uom=obj.uom, warehouse=obj.from_whse, warehouse2=obj.to_whse,
                                      transdate=t_h.transdate, created_by=t_h.created_by, updated_by=t_h.updated_by,
                                      reference=t_h.reference, sap_number=obj.sap_number)

            db.session.add_all([invtrans])

        # Receive Transaction
        # Insert to InvTransaction
        # Update the qty of WhseInv
        elif isinstance(obj, ReceiveRow):
            r_h = ReceiveHeader.query.filter_by(id=obj.receive_id).first()

            whseinv = WhseInv.query.filter_by(warehouse=obj.to_whse,
                                              item_code=obj.item_code).first()
            if not whseinv:
                raise Exception("No warehouse inv item/whse.")

            # if from transfer quantity will be add to whse inv and inv transaction
            whseinv.quantity += obj.quantity if r_h.transtype == 'TRFR' else obj.actualrec

            invtrans = InvTransaction(series_code=r_h.seriescode, trans_id=obj.receive_id,
                                      trans_num=r_h.transnumber, objtype=r_h.objtype, item_code=obj.item_code,
                                      inqty=obj.quantity if r_h.transtype == 'TRFR' else obj.actualrec, uom=obj.uom,
                                      warehouse=obj.to_whse, warehouse2=obj.from_whse, transdate=r_h.transdate,
                                      created_by=r_h.created_by, updated_by=r_h.updated_by, reference=r_h.reference,
                                      sap_number=obj.sap_number, reference2=r_h.reference2)
            
            # Check if the transtype is SAPIT then update the table of SAPIT
            if r_h.transtype == 'SAPIT':
                it_row = ITRow.query.filter(and_(ITRow.itemcode == obj.item_code, ITRow.docnum == obj.sap_number)).first()
                if it_row.actual_rec:
                    continue
                it_row.actual_rec = obj.actualrec

            # Check if the transtype is SAPO then update the table of SAPPO
            if r_h.transtype == 'SAPPO':
                po_row = PORow.query.filter(and_(PORow.itemcode == obj.item_code, PORow.docnum == obj.sap_number)).first()
                if po_row.actual_rec:
                    continue
                po_row.actual_rec = obj.actualrec
                
            db.session.add_all([invtrans])
        else:
            continue

    
    for obj in sess.dirty:
        # Update When Receive Transaction Canceled
        if isinstance(obj, ReceiveHeader):
            # check if the update is cancel and The header is not cancel
            changes = get_model_changes(obj)
            for i in changes:
                if i == 'docstatus':
                    if changes[i][1] == 'N':
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
                            whseinv = WhseInv.query.filter_by(warehouse=row.to_whse,
                                                              item_code=row.item_code).first()
                            whseinv.quantity -= row.actualrec

                            row.status = 2

                            db.session.add(inv_trans)
                        
                        # Update the SAP IT Table When Cancel
                        if obj.transtype == 'SAPIT':
                            it_header = ITHeader.query.filter(ITHeader.docnum == obj.sap_number).first()
                            it_header.docstatus = 'O'
                            it_row = ITRow.query.filter(ITRow.docnum == obj.sap_number).all()
                            for i in it_row:
                                i.actual_rec = None

                        # Update the SAP PO Table When Cancel
                        if obj.transtype == 'SAPPO':
                            po_header = POHeader.query.filter(POHeader.docnum == obj.sap_number).first()
                            po_header.docstatus = 'O'
                            po_row = PORow.query.filter(PORow.docnum == obj.sap_number).all()
                            for i in po_row:
                                i.actual_rec = None
                            
        
        # Update if the Transfer is Canceled
        if isinstance(obj, TransferHeader):
            changes = get_model_changes(obj)
            for i in changes:
                if i == 'docstatus':
                    if changes[i][1] == 'N':
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
                            whseinv = WhseInv.query.filter_by(warehouse=row.from_whse,
                                                              item_code=row.item_code).first()
                            whseinv.quantity += row.actualrec

                            row.status = 2

                            db.session.add(inv_trans)

        else:
            continue
