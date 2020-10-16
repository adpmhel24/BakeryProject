# from bakery_app.inventory.models import (Items, ItemGroup, UnitOfMeasure,
#     ItemPrice)

# from bakery_app.branches.models import Warehouses


# class Check():

#     def __init__(self, **kwargs):
#         for k, v in kwargs.items():
#             setattr(self, k, v)

#     def itemcode_exist(self):
#         if Items.query.filter_by(item_code=self.item_code).first():
#             return True
#         return False

#     def itemname_exist(self):
#         if Items.query.filter_by(item_name=self.item_name).first():
#             return True
#         return False
    
#     def uom_exist(self):
#         if UnitOfMeasure.query.filter_by(name=self.uom).first():
#             return True
#         return False
    
#     def itemgroup_exist(self):
#         if ItemGroup.query.filter_by(name=self.group_name).first():
#             return True
#         return False

#     def fromwhse_exist(self):
#         if Warehouses.query.filter_by(whsecode=self.from_whse).first():
#             return True
#         return False

#     def towhse_exist(self):
#         if Warehouses.query.filter_by(whsecode=self.to_whse).first():
#             return True
#         return False

#     def whsecode_exist(self):
#         if Warehouses.query.filter_by(whsecode=self.whsecode).first():
#             return True
#         return False


