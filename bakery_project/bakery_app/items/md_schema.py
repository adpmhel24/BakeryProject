from bakery_app import ma
from .models import Items, ItemGroup, UnitOfMeasure, PriceListHeader, PriceListRow


class ItemsSchema(ma.SQLAlchemySchema):
    class Meta:
        model = Items
        ordered = True

    id = ma.auto_field()
    item_code = ma.auto_field()
    item_name = ma.auto_field()
    item_group = ma.auto_field()
    uom = ma.auto_field()
    min_stock = ma.auto_field()
    max_stock = ma.auto_field()
    date_created = ma.auto_field()
    date_updated = ma.auto_field()
    price = ma.Number()

    def dump(self, *args, **kwargs):
        special = kwargs.pop('special', None)
        _partial = super(ItemsSchema, self).dump(*args, **kwargs)
        if special is not None and all(f in _partial for f in special):
            for field in special:
                _partial['_{}'.format(field)] = _partial.pop(field)
        return _partial

class ItemGroupSchema(ma.SQLAlchemySchema):
    class Meta:
        model = ItemGroup
        ordered = True

    id = ma.auto_field()
    code = ma.auto_field()
    description = ma.auto_field()
    date_created = ma.auto_field()
    date_updated = ma.auto_field()


class UomSchema(ma.SQLAlchemySchema):
    class Meta:
        model = UnitOfMeasure
        ordered = True

    id = ma.auto_field()
    code = ma.auto_field()
    description = ma.auto_field()
    date_created = ma.auto_field()
    date_updated = ma.auto_field()
    created_by = ma.auto_field()
    updated_by = ma.auto_field()


class PriceListHeaderSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = PriceListHeader
        ordered = True
        include_fk = True


class PriceListRowSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = PriceListRow
        ordered = True
        include_fk = True

