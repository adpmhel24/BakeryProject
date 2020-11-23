from datetime import datetime

from bakery_app import db


class CountingInventoryHeader(db.Model):
    __tablename__ = "tblcounting_inv"

    id = db.Column(db.Integer, primary_key=True)
    series = db.Column(db.Integer, db.ForeignKey('tblseries.id', ondelete='NO ACTION',
                                                 onupdate='NO ACTION'))  # series id
    seriescode = db.Column(db.String(50), nullable=False)  # series code
    transnumber = db.Column(db.Integer, nullable=False)  # series next_num
    objtype = db.Column(db.Integer, db.ForeignKey('tblobjtype.objtype'), nullable=False)
    transdate = db.Column(db.DateTime, nullable=False)
    reference = db.Column(db.String(100), nullable=False)  # seriescode + number
    remarks = db.Column(db.String(250))
    docstatus = db.Column(db.String(10), default='C', nullable=False)
    user_type = db.Column(db.String(50))
    created_by = db.Column(db.Integer, db.ForeignKey('tbluser.id'))
    updated_by = db.Column(db.Integer, db.ForeignKey('tbluser.id'))
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.now)
    date_updated = db.Column(db.DateTime, nullable=False, default=datetime.now)
    confirm = db.Column(db.Boolean, default=False)


class CountingInventoryRow(db.Model):
    __tablename__ = "tblcounting_inv_row"

    id = db.Column(db.Integer, primary_key=True)
    counting_id = db.Column(db.Integer, db.ForeignKey('tblcounting_inv.id', ondelete='CASCADE'),
                            nullable=False)
    whsecode = db.Column(db.String(100), db.ForeignKey('tblwhses.whsecode',
                                                       ondelete='CASCADE', onupdate='CASCADE'), nullable=False)
    item_code = db.Column(db.String(100), db.ForeignKey('tblitems.item_code'))
    objtype = db.Column(db.Integer, nullable=False)
    quantity = db.Column(db.Float, nullable=False, default=0.00)
    actual_count = db.Column(db.Float, nullable=False, default=0.00)
    uom = db.Column(db.String(50), db.ForeignKey('tbluom.code'))
    created_by = db.Column(db.Integer, db.ForeignKey('tbluser.id'))
    updated_by = db.Column(db.Integer, db.ForeignKey('tbluser.id'))
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.now)
    date_updated = db.Column(db.DateTime, nullable=False, default=datetime.now)


class FinalInvCount(db.Model):
    __tablename__ = "tblfinalcount"

    id = db.Column(db.Integer, primary_key=True)
    series = db.Column(db.Integer, db.ForeignKey('tblseries.id', ondelete='NO ACTION',
                                                 onupdate='NO ACTION'))  # series id
    seriescode = db.Column(db.String(50), nullable=False)  # series code
    transnumber = db.Column(db.Integer, nullable=False)  # series next_num
    objtype = db.Column(db.Integer, db.ForeignKey('tblobjtype.objtype'), nullable=False)
    transdate = db.Column(db.DateTime, nullable=False)
    reference = db.Column(db.String(100), nullable=False)  # seriescode + number
    remarks = db.Column(db.String(250))
    docstatus = db.Column(db.String(10), default='C', nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('tbluser.id'))
    updated_by = db.Column(db.Integer, db.ForeignKey('tbluser.id'))
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.now)
    date_updated = db.Column(db.DateTime, nullable=False, default=datetime.now)
    sales_user = db.Column(db.String(100))
    auditor_user = db.Column(db.String(100))
    manager_user = db.Column(db.String(100))
    row = db.relationship("FinalInvCountRow", backref="finalinvcount", lazy=True)


class FinalInvCountRow(db.Model):
    __tablename__ = "tblfinalcountrow"

    id = db.Column(db.Integer, primary_key=True)
    finalcount_id = db.Column(db.Integer, db.ForeignKey('tblfinalcount.id', ondelete='CASCADE'),
                              nullable=False)
    whsecode = db.Column(db.String(100), db.ForeignKey('tblwhses.whsecode',
                                                       ondelete='CASCADE', onupdate='CASCADE'), nullable=False)
    item_code = db.Column(db.String(100), db.ForeignKey('tblitems.item_code'))
    quantity = db.Column(db.Float, nullable=False, default=0.00)
    ending_sales_count = db.Column(db.Float, nullable=False, default=0.00)
    ending_auditor_count = db.Column(db.Float, nullable=False, default=0.00)
    ending_manager_count = db.Column(db.Float, nullable=False, default=0.00)
    ending_final_count = db.Column(db.Float, nullable=False, default=0.00)
    po_sales_count = db.Column(db.Float, nullable=False, default=0.00)
    po_auditor_count = db.Column(db.Float, nullable=False, default=0.00)
    po_manager_count = db.Column(db.Float, nullable=False, default=0.00)
    po_final_count = db.Column(db.Float, nullable=False, default=0.00)
    variance = db.Column(db.Float, nullable=False, default=0.00)
    uom = db.Column(db.String(50), db.ForeignKey('tbluom.code'))

