from bakery_app import ma
from .models import Branch, Warehouses, ObjectType, Series


class BranchSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Branch
        ordered = True
        include_fk = True


class WarehouseSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Warehouses
        ordered = True
        include_fk = True


class ObjectTypeSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = ObjectType
        ordered = True
        include_fk = True


class SeriesSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Series
        ordered = True
        include_fk = True
