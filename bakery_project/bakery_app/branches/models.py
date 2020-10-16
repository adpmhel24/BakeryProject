from datetime import datetime
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from bakery_app import db, ma
from bakery_app.users.models import User

class Branch(db.Model):
    __tablename__ = 'tblbranch'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), nullable=False, unique=True)
    name = db.Column(db.String(100), nullable=False)
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.now)
    date_updated = db.Column(db.DateTime, nullable=False, default=datetime.now)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    updated_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f"Branch('{self.code}', '{self.name}'"

class BranchSchema(ma.SQLAlchemySchema):
    class Meta:
        model = Branch
        ordered = True

    id = ma.auto_field()
    code = ma.auto_field()
    name = ma.auto_field()
    date_created = ma.auto_field()
    date_updated = ma.auto_field()
    created_by = ma.auto_field()
    updated_by = ma.auto_field()
    

class Warehouses(db.Model):
    __tablename__ = "tblwhses"

    id = db.Column(db.Integer, primary_key=True)
    whsecode = db.Column(db.String(100), unique=True, nullable=False)
    whsename = db.Column(db.String(150), nullable=False)
    branch = db.Column(db.String(50), db.ForeignKey('tblbranch.code', \
            ondelete='NO ACTION', onupdate='NO ACTION'), nullable=False)
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.now)
    date_updated = db.Column(db.DateTime, nullable=False, default=datetime.now)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id', \
                ondelete='CASCADE'), nullable=False)
    updated_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    sales = db.Column(db.Boolean, nullable=False, default=False)


    def is_sales(self):
        return self.sales

    def __repr__(self):
        return f"Warehouses('{self.whsecode}', '{self.whsename}'"

class WarehouseSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Warehouses
        ordered = True
        include_fk = True
        
class ObjectType(db.Model):
    __tablename__ = "tblobjtype"
    
    id = db.Column(db.Integer, primary_key=True, unique=True)
    code = db.Column(db.String(50), nullable=False, unique=True)
    objtype = db.Column(db.Integer, unique=True, nullable=False) # must be integer
    description = db.Column(db.String(100), nullable=False, unique=True)
    table = db.Column(db.String(100), nullable=False, unique=True) # what table
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.now)
    date_updated = db.Column(db.DateTime, nullable=False, default=datetime.now)
    updated_by = db.Column(db.DateTime, nullable=False, default=datetime.now)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class ObjectTypeSchema(ma.SQLAlchemySchema):
    class Meta:
        model = ObjectType
        ordered = True
        include_fk = True

    id = ma.auto_field()
    code = ma.auto_field()
    objtype = ma.auto_field()
    description = ma.auto_field()
    table = ma.auto_field()
    created_by = ma.auto_field()
    updated_by = ma.auto_field()
    date_updated = ma.auto_field()
    date_created = ma.auto_field()

class Series(db.Model):
    __tablename__ = "tblseries"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), nullable=False) # series code
    name = db.Column(db.String(100), nullable=False) # series name
    whsecode = db.Column(db.String(100), db.ForeignKey('tblwhses.whsecode', ondelete='NO ACTION',\
        onupdate='CASCADE'), nullable=False)
    objtype = db.Column(db.Integer, db.ForeignKey('tblobjtype.objtype'), nullable=False)
    start_num = db.Column(db.Integer, nullable=False)
    next_num = db.Column(db.Integer, nullable=False) 
    end_num = db.Column(db.Integer, nullable=False)
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.now)
    date_updated = db.Column(db.DateTime, nullable=False, default=datetime.now)
    updated_by = db.Column(db.DateTime, nullable=False, default=datetime.now)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    obj_code = db.relationship("ObjectType", backref="series", lazy=True)

    def __repr__(self):
        return f"Series('{self.code}', '{self.name}', '{self.objtype}', \
            '{self.start_num}', '{self.next_num}', '{self.end_num}'"

class SeriesSchema(ma.SQLAlchemySchema):
    class Meta:
        model = Series
        ordered = True
        include_fk = True

    id = ma.auto_field()
    code = ma.auto_field()
    name = ma.auto_field()
    whsecode = ma.auto_field()
    objtype = ma.auto_field()
    start_num = ma.auto_field()
    next_num = ma.auto_field()
    end_num = ma.auto_field()
    created_by = ma.auto_field()
    updated_by = ma.auto_field()
    date_updated = ma.auto_field()
    date_created = ma.auto_field()





