import json
import pyodbc
from sqlalchemy import exc
from datetime import datetime, date
from sqlalchemy import and_
from flask import Blueprint, request, jsonify, json
from flask_login import current_user
from bakery_app import db, auth
from bakery_app.users.routes import token_required
from bakery_app._utils import Check, ResponseMessage
from bakery_app._helpers import BaseQuery
from bakery_app.items.models import Items
from bakery_app.inventory.models import ReceiveHeader, ReceiveRow

from .models import ITHeader, ITRow, POHeader, PORow
from .sapb1_schema import ITheaderSchema, ITRowSchema, POheaderSchema, PORowSchema

sapb1 = Blueprint('sapb1', __name__)




# POST SAP IT
@sapb1.route('/api/sapb1/it/new', methods=["POST"])
@token_required
def add_sap_it(curr_user):
    if not curr_user.is_can_add_sap():
        return ResponseMessage(False, message="Unauthorized user!").resp(), 401

    try:
        datas = request.get_json()
        for data in datas:
            header = data['header']
            row = data['row']

            it_header = ITHeader(**header)
            db.session.add(it_header)
            db.session.flush()

            # Query the Receive Header table and check if there's a same sap number
            receive = ReceiveHeader.query.filter(and_(ReceiveHeader.sap_number == it_header.docnum,
                                                        ReceiveHeader.type2 == 'SAPIT')).first()
            
            for i in row:
                it_row = ITRow(it_id=it_header.id, **i)

                # if has receive
                # check the item code if the same item code to be insert in IT Row table
                # if same get the actual receive then insert it to actual receive in IT Row Table
                if receive:
                    rec_row = ReceiveRow.query.filter(and_(ReceiveRow.receive_id == receive.id,
                                                            ReceiveRow.item_code == it_row.itemcode)).first()
                    if rec_row:
                        it_row.actual_rec = rec_row.actualrec
                db.session.add(it_row)

            db.session.commit()
        return ResponseMessage(True, message="Successfully added").resp()
    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        db.session.rollback()
        return ResponseMessage(True, message=f"{err}").resp(), 500
    except Exception as err:
        db.session.rollback()
        return ResponseMessage(True, message=f"{err}").resp(), 500
    finally:
        db.session.close()



# POST SAP PO
@sapb1.route('/api/sapb1/po/new', methods=["POST"])
@token_required
def add_sap_po(curr_user):
    if not curr_user.is_can_add_sap():
        return ResponseMessage(False, message="Unauthorized user!").resp(), 401

    try:
        datas = request.get_json()
        for data in datas:
            header = data['header']
            row = data['row']

            po_header = ITHeader(**header)
            db.session.add(po_header)
            db.session.flush()

            # Query the Receive Header table and check if there's a same sap number
            receive = ReceiveHeader.query.filter(and_(ReceiveHeader.sap_number == po_header.docnum,
                                                        ReceiveHeader.type2 == 'SAPPO')).first()
         
            for i in row:
                po_row = PORow(po_id=po_header.id, **i)

                # if has receive
                # check the item code if the same item code to be insert in PO Row table
                # if same get the actual receive then insert it to actual receive in PO Row Table
                if receive:
                    rec_row = ReceiveRow.query.filter(and_(ReceiveRow.receive_id == receive.id,
                                                            ReceiveRow.item_code == po_row.itemcode)).first()
                    if rec_row:
                        po_row.actual_rec = rec_row.actualrec

                db.session.add(po_row)

            db.session.commit()
        return ResponseMessage(True, message="Successfully added").resp()
    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        db.session.rollback()
        return ResponseMessage(True, message=f"{err}").resp(), 500
    except Exception as err:
        db.session.rollback()
        return ResponseMessage(True, message=f"{err}").resp(), 500
    finally:
        db.session.close()



# Get All IT
@sapb1.route('/api/sapb1/getit')
@token_required
def get_all_it(curr_user):
    try:
        data = request.args.to_dict()
        filt = []
        for k, v in data.items():
            if v:
                filt.append((k, '==', v))

        filters = BaseQuery.create_query_filter(ITHeader, filters={"and": filt})
        sap_it = db.session.query(ITHeader).\
                filter(and_(*filters, ITRow.whscode == curr_user.whse, 
                            ITHeader.docstatus == 'O'))

        header_schema = ITheaderSchema(many=True)
        result = header_schema.dump(sap_it)
        return ResponseMessage(True, count=len(result), data=result).resp()
    
    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        return ResponseMessage(True, message=f"{err}").resp(), 500
    except Exception as err:
        return ResponseMessage(True, message=f"{err}").resp(), 500



# Get SAP IT Details
@sapb1.route('/api/sapb1/itdetails/<int:docentry>')
@token_required
def get_it_details(curr_user, docentry):
    try:
        sap_it = ITRow.query.filter(and_(ITRow.docentry==docentry,
                                        ITRow.actual_rec==None)).all()
        header_schema = ITRowSchema(many=True)
        result = header_schema.dump(sap_it)
        return ResponseMessage(True, count=len(result), data=result).resp()
    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        return ResponseMessage(True, message=f"{err}").resp(), 500
    except Exception as err:
        return ResponseMessage(True, message=f"{err}").resp(), 500



# Get All PO
@sapb1.route('/api/sapb1/getpo')
@token_required
def get_all_po(curr_user):
    try:
        data = request.args.to_dict()
        filt = []
        for k, v in data.items():
            if v:
                filt.append((k, '==', v))

        filters = BaseQuery.create_query_filter(POHeader, filters={"and": filt})
        sap_po = db.session.query(POHeader).\
                filter(and_(*filters, PORow.whscode == curr_user.whse, 
                            POHeader.docstatus == 'O'))

        header_schema = POheaderSchema(many=True)
        result = header_schema.dump(sap_po)
        return ResponseMessage(True, count=len(result), data=result).resp()
    
    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        return ResponseMessage(True, message=f"{err}").resp(), 500
    except Exception as err:
        return ResponseMessage(True, message=f"{err}").resp(), 500



# Get SAP PO Details
@sapb1.route('/api/sapb1/podetails/<int:docentry>')
@token_required
def get_po_details(curr_user, docentry):
    try:
        sap_po = PORow.query.filter(and_(PORow.docentry==docentry,
                                        PORow.actual_rec==None)).all()
        header_schema = PORowSchema(many=True)
        result = header_schema.dump(sap_po)
        return ResponseMessage(True, count=len(result), data=result).resp()
    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        return ResponseMessage(True, message=f"{err}").resp(), 500
    except Exception as err:
        return ResponseMessage(True, message=f"{err}").resp(), 500


# # Get All IT
# @sapb1.route('/api/sapb1/getit')
# @token_required
# def get_all_it(curr_user):
#     docnum = request.args.get('docnum')
#     whse = f"'{curr_user.whse}'"
#     try:
#         if docnum:
#             transfer = db.engine.execute(
#                 "SELECT* FROM vSAP_IT_Header a1 WHERE a1.whsCode = {} and a1.DocNum = {}".format(whse, docnum))
#         else:
#             transfer = db.engine.execute("SELECT* FROM vSAP_IT_Header a1 WHERE a1.whsCode = {}".format(whse))

#         result = [dict(row) for row in transfer]
#         return ResponseMessage(True, data=result).resp()


#     except (pyodbc.IntegrityError, exc.IntegrityError) as err:
#         return ResponseMessage(True, message=f"{err}").resp(), 500
#     except Exception as err:
#         return ResponseMessage(True, message=f"{err}").resp(), 500


# # Get SAP IT Details
# @sapb1.route('/api/sapb1/itdetails/<docentry>')
# @token_required
# def get_it_details(curr_user, docentry):
#     try:
#         transfer = db.engine.execute("SELECT* FROM vSAP_IT_Rows a1 WHERE a1.DocEntry = {}".format(docentry))
#         result = [dict(row) for row in transfer]
#         return ResponseMessage(True, data=result).resp()
#     except (pyodbc.IntegrityError, exc.IntegrityError) as err:
#         return ResponseMessage(True, message=f"{err}").resp(), 500
#     except Exception as err:
#         return ResponseMessage(True, message=f"{err}").resp(), 500


# # Get SAP PO
# @sapb1.route('/api/sapb1/getpo')
# @token_required
# def get_all_po(curr_user):
#     docnum = request.args.get('docnum')
#     whse = f"'{curr_user.whse}'"
#     try:
#         if docnum:
#             transfer = db.engine.execute(
#                 "SELECT* FROM vSAP_PO_Header a1 WHERE a1.whsCode = {} and a1.DocNum = {}".format(whse, docnum))
#         else:
#             transfer = db.engine.execute("SELECT* FROM vSAP_PO_Header a1 WHERE a1.whsCode = {}".format(whse))

#         result = [dict(row) for row in transfer]
#         return ResponseMessage(True, data=result).resp()
#     except (pyodbc.IntegrityError, exc.IntegrityError) as err:
#         return ResponseMessage(True, message=f"{err}").resp()
#     except Exception as err:
#         return ResponseMessage(True, message=f"{err}").resp()


# # Get SAP PO Details
# @sapb1.route('/api/sapb1/podetails/<docentry>')
# @token_required
# def get_po_details(curr_user, docentry):
#     try:
#         transfer = db.engine.execute("SELECT* FROM vSAP_PO_Rows a1 WHERE a1.DocEntry = {}".format(docentry))
#         result = [dict(row) for row in transfer]
#         return ResponseMessage(True, data=result).resp()
#     except (pyodbc.IntegrityError, exc.IntegrityError) as err:
#         return ResponseMessage(True, message=f"{err}").resp()
#     except Exception as err:
#         return ResponseMessage(True, message=f"{err}").resp()
