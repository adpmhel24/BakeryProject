from datetime import datetime
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from bakery_app import db


class Items(db.Model):
    __tablename__ = "tblitems"

    id = db.Column(db.Integer, primary_key=True)
    item_code = db.Column(db.String(100), unique=True, nullable=False)
    item_name = db.Column(db.String(150), nullable=False)
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.now)
    date_updated = db.Column(db.DateTime, nullable=False, default=datetime.now)
    item_group = db.Column(db.String(50), db.ForeignKey('tblitemgrp.name', ondelete='CASCADE'), nullable=False)
    uom = db.Column(db.String(50), db.ForeignKey('tbluom.name', ondelete='CASCADE'), nullable=False)


class ItemGroup(db.Model):
    __tablename__ = "tblitemgrp"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    description = db.Column(db.String(100), nullable=False, unique=True)
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.now)
    date_updated = db.Column(db.DateTime, nullable=False, default=datetime.now)
    items = db.relationship('Items', backref='itemgroup', lazy=True)


class UnitOfMeasure(db.Model):
    __tablename__ = "tbluom"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    description = db.Column(db.String(100), nullable=False, unique=True)
    date_create = db.Column(db.DateTime, nullable=False, default=datetime.now)
    date_updated = db.Column(db.DateTime, nullable=False, default=datetime.now)
    items = db.relationship('Items', backref='tbluom', lazy=True)
