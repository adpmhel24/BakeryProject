from datetime import datetime
from bakery_app import db
from sqlalchemy import event
from bakery_app.inventory.models import WhseInv
import bakery_app.branches as branch


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
    price = db.Column(db.Float, default=0.00)
    created_by = db.Column(db.Integer, db.ForeignKey('tbluser.id', ondelete='NO ACTION'),
                           nullable=False)
    updated_by = db.Column(db.Integer, db.ForeignKey('tbluser.id'))
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
    created_by = db.Column(db.Integer, db.ForeignKey('tbluser.id', ondelete='NO ACTION'),
                           nullable=False)
    updated_by = db.Column(db.Integer, db.ForeignKey('tbluser.id'))

    items = db.relationship('Items', backref='itemgroup', lazy=True)

    def __repr__(self):
        return f"ItemGroup('{self.code}', '{self.description}')"


class UnitOfMeasure(db.Model):
    __tablename__ = "tbluom"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), nullable=False, unique=True)
    description = db.Column(db.String(100), nullable=False, unique=True)
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.now)
    date_updated = db.Column(db.DateTime, nullable=False, default=datetime.now)
    created_by = db.Column(db.Integer, db.ForeignKey('tbluser.id', ondelete='NO ACTION'),
                           nullable=False)
    updated_by = db.Column(db.Integer, db.ForeignKey('tbluser.id'))
    items = db.relationship('Items', backref='unitofmeasure', lazy=True)

    def __repr__(self):
        return f"UnitOfMeasure('{self.code}', '{self.description}')"


class PriceListHeader(db.Model):
    __tablename__ = "tblpricelist"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), nullable=False, unique=True)
    description = db.Column(db.String(100), nullable=False)
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.now)
    date_updated = db.Column(db.DateTime, nullable=False, default=datetime.now)
    created_by = db.Column(db.Integer, db.ForeignKey('tbluser.id', ondelete='NO ACTION'),
                           nullable=False)
    updated_by = db.Column(db.Integer, db.ForeignKey('tbluser.id'))


class PriceListRow(db.Model):
    __tablename__ = "tblpricelistrow"

    id = db.Column(db.Integer, primary_key=True)
    pricelist_id = db.Column(db.Integer, db.ForeignKey('tblpricelist.id', ondelete='CASCADE'), nullable=False)
    item_code = db.Column(db.String(100), db.ForeignKey('tblitems.item_code', ondelete='NO ACTION'), nullable=False)
    price = db.Column(db.Float, nullable=False, default=0.00)
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.now)
    date_updated = db.Column(db.DateTime, nullable=False, default=datetime.now)
    created_by = db.Column(db.Integer, db.ForeignKey('tbluser.id', ondelete='NO ACTION'),
                           nullable=False)
    updated_by = db.Column(db.Integer, db.ForeignKey('tbluser.id'))


@event.listens_for(db.session, "after_flush")
def create_price_list(*args):
    sess = args[0]
    for obj in sess.new:
        if isinstance(obj, PriceListHeader):
            items = Items.query.all()
            for item in items:
                price_list_row = PriceListRow(pricelist_id=obj.id, item_code=item.item_code,
                                        created_by=obj.created_by, updated_by=obj.updated_by)
                db.session.add(price_list_row)

        elif isinstance(obj, Items):
            price_lists = PriceListHeader.query.all()
            for price_list in price_lists:
                price_list_row = PriceListRow(pricelist_id=price_list.id, item_code=obj.item_code,
                                        created_by=obj.created_by, updated_by=obj.updated_by)
                db.session.add(price_list_row)

        else: 
            continue


@event.listens_for(db.session, "before_flush")
def insert_update(*args):
    sess = args[0]
    for obj in sess.new:

        # Insert Item to WhseInv
        if isinstance(obj, Items):
            whses = branch.Warehouses.query.all()
            for i in whses:
                whseinv = WhseInv(item_code=obj.item_code, warehouse=i.whsecode,
                                  created_by=obj.created_by, updated_by=obj.updated_by)
                db.session.add(whseinv)
