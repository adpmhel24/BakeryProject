from bakery_app import ma

from .models import PaymentType, PayTransRow, PayTransHeader, AdvancePayment


class PaymentTypeSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = PaymentType
        ordered = True


class PaymentRowSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = PayTransRow
        ordered = True
        include_fk = True


class PaymentHeaderSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = PayTransHeader
        ordered = True
        include_fk = True

    payrows = ma.Nested(PaymentRowSchema, many=True)


class AdvancePaymentSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = AdvancePayment
        ordered = True
        include_fk = True
