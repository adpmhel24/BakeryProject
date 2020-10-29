# from bakery_app.inventory.models import TransferHeader, TransferRow

# class SeriesNumber:
#     """ Generate series number requirements branch of user and transaction type"""

#     def __init__(self, objtype, transtype):
#         self.objtype = objtype
#         self.transtype = transtype

#     def transfer_series(self, min, max):
#         if self.objtype == 1:
#             transfer_last_num = TransferHeader.query.filter(TransferHeader.transnumber.\
#                 contains(f'{self.branch}')).order_by(TransferHeader.id.desc()).first()
#         if not transfer_last_num:
#             return f'{self.branch}{min}'
#         trans_num = transfer_last_num.transnumber
#         transfer_int = int(trans_num.split(f'{self.branch}')[-1])
#         width = 8
#         new_transfer_int = transfer_int + 1
#         if new_transfer_int == max:
#             raise Exception("Sorry your series number met the max limit!")
#         formatted = (width - len(str(new_transfer_int))) * "0" + str(
#             new_transfer_int)
#         new_trans_num = f'{self.branch}' + str(formatted)
#         return new_trans_num