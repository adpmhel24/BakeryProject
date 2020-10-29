from bakery_app import ma
from .models import SalesHeader, SalesRow, SalesType, DiscountType


class SalesTypeSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = SalesType
        ordered = True


class DiscountTypeSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = DiscountType
        ordered = True


class SalesRowSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = SalesRow
        ordered = True
        include_fk = True


class SalesHeaderSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = SalesHeader
        ordered = True
        include_fk = True
        load_instance = True

    salesrow = ma.Nested(SalesRowSchema, many=True)
