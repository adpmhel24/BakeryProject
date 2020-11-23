from datetime import datetime
from bakery_app import db


class ItemRequest(db.Model):
    __tablename__ = "tblitemreq"

    id = db.Column(db.Integer, primary_key=True)
    series = db.Column(db.Integer, db.ForeignKey('tblseries.id', ondelete='NO ACTION',
                                                 onupdate='NO ACTION'))  # series id
    seriescode = db.Column(db.String(50), nullable=False)  # series code
    transnumber = db.Column(db.Integer, nullable=False)
    docstatus = db.Column(db.String(10), default='O', nullable=False)
    reference = db.Column(db.String(100))
    transdate = db.Column(db.DateTime, nullable=False, default=datetime.now)
    duedate = db.Column(db.DateTime, nullable=False, default=datetime.now)
    reference2 = db.Column(db.String(100))
    remarks = db.Column(db.String(250))
    objtype = db.Column(db.Integer, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('tbluser.id',
                                                     ondelete='NO ACTION'), nullable=False)
    updated_by = db.Column(db.Integer, db.ForeignKey('tbluser.id'))
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.now)
    date_updated = db.Column(db.DateTime, nullable=False, default=datetime.now)
    confirm = db.Column(db.Boolean)
    sap_number = db.Column(db.Integer)

    request_rows = db.relationship(
        'ItemRequestRow', back_populates="request_header", lazy=True)


class ItemRequestRow(db.Model):
    __tablename__ = "tblitemreqrow"

    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey('tblitemreq.id', ondelete='CASCADE'), nullable=False)
    objtype = db.Column(db.Integer, nullable=False)
    from_whse = db.Column(db.String(100), db.ForeignKey('tblwhses.whsecode',
                                                        ondelete='CASCADE', onupdate='CASCADE'), nullable=False)
    to_whse = db.Column(db.String(100), db.ForeignKey(
        'tblwhses.whsecode'), nullable=False)
    item_code = db.Column(db.String(100), db.ForeignKey('tblitems.item_code',
                                                        ondelete='CASCADE', onupdate='CASCADE'), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    deliverqty = db.Column(db.Float, nullable=False, default=0.00)
    uom = db.Column(db.String(50), db.ForeignKey(
        'tbluom.code'), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('tbluser.id',
                                                     ondelete='NO ACTION'), nullable=False)
    updated_by = db.Column(db.Integer, db.ForeignKey('tbluser.id'))
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.now)
    date_updated = db.Column(db.DateTime, nullable=False, default=datetime.now)

    request_header = db.relationship(
        "ItemRequest", back_populates="request_rows", lazy=True)