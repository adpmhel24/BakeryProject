from datetime import datetime
from sqlalchemy import event, cast, and_
from bakery_app import db, ma



class Items(db.Model):
    __tablename__ = "tblitems"

    id = db.Column(db.Integer, primary_key=True)
    item_code = db.Column(db.String(100), unique=True, nullable=False)
    item_name = db.Column(db.String(150), nullable=False)
    item_group = db.Column(db.String(50), db.ForeignKey('tblitemgrp.code', ondelete='CASCADE',
                                                        onupdate='CASCADE'), nullable=False)
    uom = db.Column(db.String(50), db.ForeignKey('tbluom.code', ondelete='CASCADE',
                                                 onupdate='CASCADE'), nullable=False)
    min_stock = db.Column(db.Float, nullable=False, default=0.00)
    max_stock = db.Column(db.Float, nullable=False, default=0.00)
    price = db.Column(db.Float, nullable=False, default=0.00)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='NO ACTION'),
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
    created_by = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='NO ACTION'),
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
    created_by = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='NO ACTION'),
                           nullable=False)
    updated_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    items = db.relationship('Items', backref='unitofmeasure', lazy=True)

    def __repr__(self):
        return f"UnitOfMeasure('{self.code}', '{self.description}')"


