from bakery_app import ma
from .models import (WhseInv, InvTransaction, TransferRow, TransferHeader,
                     ReceiveRow, ReceiveHeader)


class WhseInvSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = WhseInv
        ordered = True
        include_fk = True

    price = ma.Number()
    uom = ma.String()

    def dump(self, *args, **kwargs):
        special = kwargs.pop('special', None)
        _partial = super(WhseInvSchema, self).dump(*args, **kwargs)
        if special is not None and all(f in _partial for f in special):
            for field in special:
                _partial['_{}'.format(field)] = _partial.pop(field)
        return _partial


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

