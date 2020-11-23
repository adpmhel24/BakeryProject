from bakery_app import ma
from .models import ItemRequest, ItemRequestRow


class ItemRequestRowSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = ItemRequestRow
        ordered = True
        include_fk = True


class ItemRequestSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = ItemRequest
        ordered = True
        include_fk = True

    request_rows = ma.Nested(ItemRequestRowSchema, many=True)