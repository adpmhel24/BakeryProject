from datetime import datetime
from bakery_app import db


class Branch(db.Model):
    __tablename__ = 'tblbranch'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), nullable=False, unique=True)
    name = db.Column(db.String(100), nullable=False)
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.now)
    date_updated = db.Column(db.DateTime, nullable=False, default=datetime.now)
    created_by = db.Column(
        db.Integer, db.ForeignKey('user.id'), nullable=False)
    updated_by = db.Column(
        db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f"Branch('{self.code}', '{self.name}'"


class Warehouses(db.Model):
    __tablename__ = "tblwhses"

    id = db.Column(db.Integer, primary_key=True)
    whsecode = db.Column(db.String(100), unique=True, nullable=False)
    whsename = db.Column(db.String(150), nullable=False)
    branch = db.Column(db.String(50), db.ForeignKey('tblbranch.code',
                                                    ondelete='NO ACTION', onupdate='NO ACTION'), nullable=False)
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.now)
    date_updated = db.Column(db.DateTime, nullable=False, default=datetime.now)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id',
                                                     ondelete='CASCADE'), nullable=False)
    updated_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    sales = db.Column(db.Boolean, nullable=False, default=False)

    def is_sales(self):
        return self.sales

    def __repr__(self):
        return f"Warehouses('{self.whsecode}', '{self.whsename}'"


class ObjectType(db.Model):
    __tablename__ = "tblobjtype"

    id = db.Column(db.Integer, primary_key=True, unique=True)
    code = db.Column(db.String(50), nullable=False, unique=True)
    objtype = db.Column(db.Integer, unique=True,
                        nullable=False)  # must be integer
    description = db.Column(db.String(100), nullable=False, unique=True)
    table = db.Column(db.String(100), nullable=False,
                      unique=True)  # what table
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.now)
    date_updated = db.Column(db.DateTime, nullable=False, default=datetime.now)
    updated_by = db.Column(db.DateTime, nullable=False, default=datetime.now)
    created_by = db.Column(
        db.Integer, db.ForeignKey('user.id'), nullable=False)


class Series(db.Model):
    __tablename__ = "tblseries"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), nullable=False)  # series code
    name = db.Column(db.String(100), nullable=False)  # series name
    whsecode = db.Column(db.String(100), db.ForeignKey('tblwhses.whsecode', ondelete='NO ACTION',
                                                       onupdate='CASCADE'), nullable=False)
    objtype = db.Column(db.Integer, db.ForeignKey(
        'tblobjtype.objtype'), nullable=False)
    start_num = db.Column(db.Integer, nullable=False)
    next_num = db.Column(db.Integer, nullable=False)
    end_num = db.Column(db.Integer, nullable=False)
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.now)
    date_updated = db.Column(db.DateTime, nullable=False, default=datetime.now)
    updated_by = db.Column(db.DateTime, nullable=False, default=datetime.now)
    created_by = db.Column(
        db.Integer, db.ForeignKey('user.id'), nullable=False)
    obj_code = db.relationship("ObjectType", backref="series", lazy=True)

    def __repr__(self):
        return f"Series('{self.code}', '{self.name}', '{self.objtype}', \
            '{self.start_num}', '{self.next_num}', '{self.end_num}'"
