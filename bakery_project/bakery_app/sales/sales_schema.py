from bakery_app import ma
from bakery_app.users.models import UserSchema
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
    created_user = ma.Nested(UserSchema, only=("username",))

    cashsales = ma.Number()
    arsales = ma.Number()
    agentsales = ma.Number()
    user = ma.String()

    def dump(self, *args, **kwargs):
        special = kwargs.pop('special', None)
        _partial = super(SalesHeaderSchema, self).dump(*args, **kwargs)
        if special is not None and all(f in _partial for f in special):
            for field in special:
                _partial['_{}'.format(field)] = _partial.pop(field)
        return _partial
