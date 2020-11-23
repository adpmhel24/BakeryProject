from bakery_app import ma

from .models import PaymentType, PayTransRow, PayTransHeader, Deposit, CashTransaction


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


class DepositSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Deposit
        ordered = True
        include_fk = True


class CashTransactionSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = CashTransaction
        ordered = True
        include_fk = True
