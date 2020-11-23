from datetime import datetime
from sqlalchemy import event
from bakery_app._helpers import get_model_changes
from bakery_app.inventory.models import WhseInv, InvTransaction
from bakery_app import db


class PullOutHeaderRequest(db.Model):
    __tablename__ = "tblpulloutreq"

    id = db.Column(db.Integer, primary_key=True)
    series = db.Column(db.Integer, db.ForeignKey('tblseries.id', ondelete='NO ACTION',
                                                 onupdate='NO ACTION'))  # series id
    seriescode = db.Column(db.String(50), nullable=False)  # series code
    transnumber = db.Column(db.Integer, nullable=False)  # series next_num
    objtype = db.Column(db.Integer, db.ForeignKey('tblobjtype.objtype'), nullable=False)
    transdate = db.Column(db.DateTime, nullable=False)
    reference = db.Column(db.String(100), nullable=False)  # seriescode + number
    remarks = db.Column(db.String(250))
    user_type = db.Column(db.String(50))
    docstatus = db.Column(db.String(10), default='O', nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('tbluser.id'))
    updated_by = db.Column(db.Integer, db.ForeignKey('tbluser.id'))
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.now)
    date_updated = db.Column(db.DateTime, nullable=False, default=datetime.now)
    confirm = db.Column(db.Boolean, default=False)


class PullOutRowRequest(db.Model):
    __tablename__ = "tblpulloutreqrow"

    id = db.Column(db.Integer, primary_key=True)
    pulloutreq_id = db.Column(db.Integer, db.ForeignKey('tblpulloutreq.id', ondelete='CASCADE'),
                              nullable=False)
    whsecode = db.Column(db.String(100), db.ForeignKey('tblwhses.whsecode',
                                                       ondelete='CASCADE', onupdate='CASCADE'), nullable=False)
    item_code = db.Column(db.String(100), db.ForeignKey('tblitems.item_code'))
    objtype = db.Column(db.Integer, nullable=False)
    quantity = db.Column(db.Float, nullable=False, default=0.00)
    uom = db.Column(db.String(50), db.ForeignKey('tbluom.code'))
    created_by = db.Column(db.Integer, db.ForeignKey('tbluser.id'))
    updated_by = db.Column(db.Integer, db.ForeignKey('tbluser.id'))
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.now)
    date_updated = db.Column(db.DateTime, nullable=False, default=datetime.now)


class PullOutHeader(db.Model):
    __tablename__ = "tblpullout"

    id = db.Column(db.Integer, primary_key=True)
    series = db.Column(db.Integer, db.ForeignKey('tblseries.id', ondelete='NO ACTION',
                                                 onupdate='NO ACTION'))  # series id
    seriescode = db.Column(db.String(50), nullable=False)  # series code
    transnumber = db.Column(db.Integer, nullable=False)  # series next_num
    objtype = db.Column(db.Integer, db.ForeignKey('tblobjtype.objtype'), nullable=False)
    transdate = db.Column(db.DateTime, nullable=False)
    reference = db.Column(db.String(100), nullable=False)  # seriescode + number
    remarks = db.Column(db.String(250))
    docstatus = db.Column(db.String(10), default='O', nullable=False)
    sap_number = db.Column(db.Integer)
    created_by = db.Column(db.Integer, db.ForeignKey('tbluser.id'))
    updated_by = db.Column(db.Integer, db.ForeignKey('tbluser.id'))
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.now)
    date_updated = db.Column(db.DateTime, nullable=False, default=datetime.now)
    confirm = db.Column(db.Boolean, default=False)
    row = db.relationship("PullOutRow", backref="pulloutheader", lazy=True)


class PullOutRow(db.Model):
    __tablename__ = "tblpulloutrow"

    id = db.Column(db.Integer, primary_key=True)
    pullout_id = db.Column(db.Integer, db.ForeignKey('tblpullout.id', ondelete='CASCADE'),
                           nullable=False)
    whsecode = db.Column(db.String(100), db.ForeignKey('tblwhses.whsecode',
                                                       ondelete='CASCADE', onupdate='CASCADE'), nullable=False)
    to_whse = db.Column(db.String(100), db.ForeignKey('tblwhses.whsecode'), nullable=False)
    item_code = db.Column(db.String(100), db.ForeignKey('tblitems.item_code'))
    objtype = db.Column(db.Integer, nullable=False)
    quantity = db.Column(db.Float, nullable=False, default=0.00)
    uom = db.Column(db.String(50), db.ForeignKey('tbluom.code'))
    created_by = db.Column(db.Integer, db.ForeignKey('tbluser.id'))
    updated_by = db.Column(db.Integer, db.ForeignKey('tbluser.id'))
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.now)
    date_updated = db.Column(db.DateTime, nullable=False, default=datetime.now)
    sap_number = db.Column(db.Integer)
    # header = db.relationship("PullOutHeader", back_populates="row", lazy=True)


@event.listens_for(db.session, "before_flush")
def insert_update(*args):
    sess = args[0]
    for obj in sess.new:

        # Insert to InvTransaction and Update Whse Inv
        if isinstance(obj, PullOutRow):

            po_header = PullOutHeader.query.filter_by(id=obj.pullout_id).first()
            whseinv = WhseInv.query.filter_by(warehouse=obj.whsecode,
                                              item_code=obj.item_code).first()
            whseinv.quantity -= obj.quantity

            invtrans = InvTransaction(series_code=po_header.seriescode, trans_id=po_header.id,
                                      trans_num=po_header.transnumber, objtype=po_header.objtype,
                                      item_code=obj.item_code,
                                      outqty=obj.quantity, uom=obj.uom, warehouse=obj.whsecode, warehouse2=obj.to_whse,
                                      transdate=po_header.transdate, created_by=po_header.created_by,
                                      updated_by=po_header.updated_by, reference=po_header.reference,
                                      sap_number=obj.sap_number, reference2="PullOut")

            db.session.add_all([whseinv, invtrans])

        else:
            continue
