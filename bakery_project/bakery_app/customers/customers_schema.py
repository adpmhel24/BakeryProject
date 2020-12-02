from bakery_app import ma
from .models import Customer, CustomerType


class CustomerSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Customer
        ordered = True
        include_fk = True


class CustTypeSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = CustomerType
        ordered = True
