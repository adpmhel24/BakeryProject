from bakery_app import ma
from .models import (WhseInv, InvTransaction, TransferRow,
                     TransferHeader, ReceiveRow, ReceiveHeader)
from bakery_app.master_data.md_schema import ItemsSchema


class WhseInvSchema(ma.SQLAlchemySchema):
    class Meta:
        model = WhseInv
        ordered = True

    id = ma.auto_field()
    item_code = ma.auto_field()
    quantity = ma.auto_field()
    warehouse = ma.auto_field()
    created_by = ma.auto_field()
    updated_by = ma.auto_field()
    item = ma.Nested(ItemsSchema(only=("price", "uom")))


class InvTransactionSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = InvTransaction
        ordered = True


class TransferRowSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = TransferRow
        ordered = True
        include_fk = True


class TransferHeaderSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = TransferHeader
        ordered = True
        load_instance = True

    transrow = ma.Nested(TransferRowSchema, many=True)


class ReceiveRowSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = ReceiveRow
        ordered = True
        include_fk = True


class ReceiveHeaderSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = ReceiveHeader
        ordered = True
        include_fk = True

    recrow = ma.Nested(ReceiveRowSchema, many=True)
