from bakery_app import ma
from .models import PullOutRow, PullOutHeader, PullOutHeaderRequest, PullOutRowRequest


class PullOutHeaderRowSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = PullOutRow
        ordered = True
        include_fk = True


class PullOutHeaderSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = PullOutHeader
        ordered = True
        include_fk = True

    row = ma.Nested(PullOutHeaderRowSchema, many=True)


class PullOutHeaderRequestSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = PullOutHeaderRequest
        ordered = True
        include_fk = True

    price = ma.Number()
    sales_count = ma.Number()
    auditor_count = ma.Number()
    manager_count = ma.Number()
    final_count = ma.Number()
    variance = ma.Number()
    item_code = ma.String()

    def dump(self, *args, **kwargs):
        special = kwargs.pop('special', None)
        _partial = super(PullOutHeaderRequestSchema,
                         self).dump(*args, **kwargs)
        if special is not None and all(f in _partial for f in special):
            for field in special:
                _partial['_{}'.format(field)] = _partial.pop(field)
        return _partial


class PullOutHeaderRowRequestSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = PullOutRowRequest
        ordered = True
        include_fk = True
