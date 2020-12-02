from datetime import datetime
from bakery_app import db


class ITHeader(db.Model):
    __tablename__ = 'tblsap_it_header'

    id = db.Column(db.Integer, primary_key=True)
    docentry = db.Column(db.Integer)
    docnum = db.Column(db.Integer)
    docdate = db.Column(db.DateTime, default=datetime.now)
    docduedate = db.Column(db.DateTime, default=datetime.now)
    cardcode = db.Column(db.String(100))
    cardname = db.Column(db.String(100))
    comments = db.Column(db.String(100))
    u_remarks = db.Column(db.String(200))
    docstatus = db.Column(db.String(10), default='O')
    date_created = db.Column(db.DateTime, default=datetime.now)


class ITRow(db.Model):
    __tablename__ = 'tblsap_it_row'

    id = db.Column(db.Integer, primary_key=True)
    it_id = db.Column(db.Integer, db.ForeignKey('tblsap_it_header.id', ondelete='CASCADE'))
    docentry = db.Column(db.Integer)
    docnum = db.Column(db.Integer)
    itemcode = db.Column(db.String(150))
    itemname = db.Column(db.String(150))
    dscription = db.Column(db.String(150))
    quantity = db.Column(db.Float)
    actual_rec = db.Column(db.Float)
    fromwhscod = db.Column(db.String(150))
    whscode = db.Column(db.String(150))
    unitmsr = db.Column(db.String(150))


class POHeader(db.Model):
    __tablename__ = 'tblsap_po_header'

    id = db.Column(db.Integer, primary_key=True)
    docentry = db.Column(db.Integer)
    docnum = db.Column(db.Integer)
    docdate = db.Column(db.DateTime)
    docduedate = db.Column(db.DateTime)
    cardcode = db.Column(db.String(100))
    cardname = db.Column(db.String(100))
    comments = db.Column(db.String(100))
    u_remarks = db.Column(db.String(200))
    docstatus = db.Column(db.String(10), default='O')
    date_created = db.Column(db.DateTime, default=datetime.now)


class PORow(db.Model):
    __tablename__ = 'tblsap_po_row'

    id = db.Column(db.Integer, primary_key=True)
    po_id = db.Column(db.Integer, db.ForeignKey('tblsap_po_header.id', ondelete='CASCADE'))
    docentry = db.Column(db.Integer)
    docnum = db.Column(db.Integer)
    itemcode = db.Column(db.String(150))
    itemname = db.Column(db.String(150))
    dscription = db.Column(db.String(150))
    quantity = db.Column(db.Float)
    actual_rec = db.Column(db.Float)
    fromwhscod = db.Column(db.String(150))
    whscode = db.Column(db.String(150))
    unitmsr = db.Column(db.String(150))