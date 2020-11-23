from bakery_app import ma
from .models import CountingInventoryHeader, CountingInventoryRow, FinalInvCountRow, FinalInvCount


class CountingInventoryRowSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = CountingInventoryRow
        ordered = True
        include_fk = True

    sales_count = ma.Number()
    auditor_count = ma.Number()
    manager_count = ma.Number()
    final_count = ma.Number()
    variance = ma.Number()
    ending_sales_count = ma.Number()
    ending_auditor_count = ma.Number()
    ending_manager_count = ma.Number()
    ending_final_count = ma.Number()
    po_sales_count = ma.Number()
    po_auditor_count = ma.Number()
    po_manager_count = ma.Number()
    po_final_count = ma.Number()
    uom = ma.String()
    sales_user = ma.String()
    auditor_user = ma.String()
    manager_user = ma.String()

    def dump(self, *args, **kwargs):
        special = kwargs.pop('special', None)
        _partial = super(CountingInventoryRowSchema, self).dump(*args, **kwargs)
        if special is not None and all(f in _partial for f in special):
            for field in special:
                _partial['_{}'.format(field)] = _partial.pop(field)
        return _partial


class CountingInventoryHeaderSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = CountingInventoryHeader
        ordered = True
        include_fk = True


class FinalCountRowSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = FinalInvCountRow
        ordered = True
        include_fk = True


class FinalCountSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = FinalInvCount
        ordered = True
        include_fk = True

    row = ma.Nested(FinalCountRowSchema, many=True)
