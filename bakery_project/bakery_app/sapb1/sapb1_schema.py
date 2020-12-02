from bakery_app import ma
from .models import ITRow, ITHeader, PORow, POHeader

class ITheaderSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = ITHeader
        ordered = True
        include_fk = True

class ITRowSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = ITRow
        ordered = True
        include_fk = True

class POheaderSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = POHeader
        ordered = True
        include_fk = True

class PORowSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = PORow
        ordered = True
        include_fk = True