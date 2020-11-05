import json
import pyodbc

from datetime import datetime, date
from flask import Blueprint, request, jsonify, json
from flask_login import current_user
from sqlalchemy import exc, and_, or_, cast, Date

from bakery_app import db, auth
from bakery_app._utils import Check, ResponseMessage
from bakery_app._helpers import BaseQuery
from bakery_app.branches.models import Series, ObjectType, Warehouses
from bakery_app.users.routes import token_required

from bakery_app.inventory.models import (TransferHeader, TransferRow, ReceiveHeader, ReceiveRow,
                                         WhseInv, ItemRequest, ItemRequestRow)
from .inv_schema import (TransferHeaderSchema, TransferRowSchema, InvTransactionSchema, ReceiveHeaderSchema,
                         ReceiveRowSchema, WhseInvSchema, ItemRequestSchema, ItemRequestRowSchema)

inventory = Blueprint('inventory', __name__)


# Create Transfer
@inventory.route('/api/inv/trfr/new', methods=['POST'])
@token_required
def create_transfer(curr_user):
    if not curr_user.can_transfer():
        return ResponseMessage(False, message="Unauthorized to transfer!").resp(), 401
    
    # query the whse
    whse = Warehouses.query.filter_by(whsecode=curr_user.whse).first()
    if whse.is_cutoff():
        return ResponseMessage(False, message="Your warehouse cutoff is enable!").resp(), 401

    data = request.get_json()
    details = data['details']

    if data['header']['transdate']:
        data['header']['transdate'] = datetime.strptime(
            data['header']['transdate'], '%Y/%m/%d %H:%M')

    if not details:
        return ResponseMessage(False, message="No data in details argument!").resp()

    try:
        obj = ObjectType.query.filter_by(code='TRFR').first()
        series = Series.query.filter_by(
            whsecode=curr_user.whse, objtype=obj.objtype).first()
        if series.next_num + 1 > series.end_num:
            raise Exception("Series number already in max!")
        if not series:
            raise Exception("Invalid Series")

        reference = f"{series.code}-{obj.code}-{series.next_num}"

        t_h = TransferHeader(series=series.id, seriescode=series.code,
                             transnumber=series.next_num, reference=reference,
                             created_by=curr_user.id, updated_by=curr_user.id,
                             **data['header'])
        t_h.objtype = obj.objtype

        # add 1 to series next num
        series.next_num += 1

        db.session.add_all([t_h, series])
        db.session.flush()

        for row in details:
            # add to user whse to data dictionary as from whse
            row['from_whse'] = curr_user.whse
            check = Check(**row)

            # check if valid
            if not check.itemcode_exist():
                raise Exception("Invalid itemcode!")
            elif not check.uom_exist():
                raise Exception("Invalid uom!")
            elif not check.towhse_exist():
                raise Exception("Invalid to whse code!")
            if row['from_whse'] != curr_user.whse:
                raise Exception("Invalid from_whse!")
            if not row['quantity']:
                raise Exception("Quantity is less than 1.")

            # query first the quantity of inventory
            whseinv = WhseInv.query.filter_by(warehouse=row['from_whse'],
                                              item_code=row['item_code']).first()

            # if below quantity raise an error!
            if row['quantity'] > whseinv.quantity:
                raise Exception("Below quantity stock!")

            # table row
            t_r = TransferRow(transfer_id=t_h.id, transnumber=t_h.transnumber,
                              created_by=curr_user.id, updated_by=curr_user.id,
                              sap_number=t_h.sap_number, objtype=t_h.objtype, **row)

            db.session.add(t_r)
            db.session.flush()

        db.session.commit()
        trans_schema = TransferHeaderSchema()
        result = trans_schema.dump(t_h)
        return ResponseMessage(True, message="Successfully added!", data=result).resp()
    except Exception as err:
        db.session.rollback()
        return ResponseMessage(False, message=f"{err}").resp(), 500
    except (exc.IntegrityError, pyodbc.IntegrityError) as err:
        db.session.rollback()
        return ResponseMessage(False, message=f"{err}").resp(), 500
    finally:
        db.session.close()


# Get All Transfer
@inventory.route('/api/inv/trfr/getall')
@token_required
def get_all_transfer(curr_user):
    docstatus = request.args.get('docstatus')
    transnum = request.args.get('transnum')
    trans_schema = TransferHeaderSchema(many=True, only=("id", "transnumber", "sap_number",
                                                         "transdate", "remarks", "docstatus"))

    if not docstatus or docstatus.title() == 'Open':
        if transnum:
            transfer = db.session.query(TransferHeader). \
                filter(and_(TransferHeader.transnumber == transnum,
                            or_(TransferRow.from_whse == curr_user.whse,
                                TramsferRow.to_whse == curr_user.whse),
                            TransferHeader.docstatus == 'O')).all()
        else:
            transfer = db.session.query(TransferHeader). \
                filter(and_(TransferRow.from_whse == curr_user.whse,
                            TransferHeader.docstatus == 'O')).all()

    elif docstatus.title() == 'Closed':
        if transnum:
            transfer = db.session.query(TransferHeader). \
                filter(and_(TransferHeader.transnumber == transnum,
                            or_(TransferRow.from_whse == curr_user.whse,
                                TramsferRow.to_whse == curr_user.whse),
                            TransferHeader.docstatus == 'C')).all()
        else:
            transfer = db.session.query(TransferHeader). \
                filter(and_(TransferRow.from_whse == curr_user.whse,
                            TransferHeader.docstatus == 'C')).all()

    elif docstatus.title() == 'All':
        if transnum:
            transfer = db.session.query(TransferHeader). \
                filter(and_(TransferHeader.transnumber == transnum,
                            or_(TransferRow.from_whse == curr_user.whse,
                                TramsferRow.to_whse == curr_user.whse))).all()
        else:
            transfer = db.session.query(TransferHeader). \
                filter(and_(TransferRow.from_whse == curr_user.whse)).all()

    result = trans_schema.dump(transfer)
    return ResponseMessage(True, data=result).resp()



# Get Transfer Details
@inventory.route('/api/inv/trfr/getdetails/<int:id>')
@token_required
def transfer_details(curr_user, id):
    trans_schema = TransferHeaderSchema(only=("id", "transnumber", "sap_number",
                                              "transdate", "remarks", "docstatus", "transrow"))
    try:
        transfer = TransferHeader.query.get(id)
        if not transfer:
            return ResponseMessage(False, message="Invalid transfer id!").resp()
    except:
        return ResponseMessage(False, message="Unknown error!").resp()

    result = trans_schema.dump(transfer)
    return ResponseMessage(True, data=result).resp()



# Cancel Transfer
@inventory.route('/api/inv/trfr/cancel/<int:id>', methods=['PUT'])
@token_required
def cancel_tranfer(curr_user, id):
    if not curr_user.is_admin():
        return ResponseMessage(False, message="Unauthorized user!")

    # query the whse
    whse = Warehouses.query.filter_by(whsecode=curr_user.whse).first()
    if whse.is_cutoff():
        return ResponseMessage(False, message="Your warehouse cutoff is enable!").resp(), 401

    data = request.get_json()

    try:
        transfer = TransferHeader.query.get(id)
        if transfer.docstatus == 'N':
            raise Exception('Transfer already canceled!')
        rec = db.session.query(ReceiveHeader). \
            filter(and_(ReceiveHeader.base_id == transfer.id,
                        ReceiveHeader.docstatus != 'N')).all()
        if rec:
            raise Exception('Please cancel the receive transaction first!')

        transfer.docstatus = 'N'
        transfer.updated_by = curr_user.id
        transfer.date_updated = datetime.now()
        transfer.remarks = data['remarks']

        db.session.commit()
        return ResponseMessage(True, message='Transfer Successfully canceled!').resp()

    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        db.session.rollback()
        return ResponseMessage(True, message=f'{err}').resp(), 500
    except Exception as err:
        db.session.rollback()
        return ResponseMessage(True, message=f'{err}').resp(), 500
    finally:
        db.session.close()



# Get from System Transfer For Receive
@inventory.route('/api/inv/trfr/forrec')
@token_required
def get_for_receive(curr_user):
    if not curr_user.can_receive():
        return ResponseMessage(False, message="Unauthorized user!").resp(), 401

    try:
        transfer = db.session.query(TransferHeader).join(TransferRow).filter(and_(
            TransferHeader.docstatus == 'O', TransferRow.to_whse == curr_user.whse)).all()

        trans_schema = TransferHeaderSchema(many=True, only=(
            "id", "seriescode", "transnumber", "reference", "objtype", "sap_number", "docstatus", "transdate",
            "remarks", "transrow"))
        result = trans_schema.dump(transfer)
        return ResponseMessage(True, data=result).resp()
    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500
    except Exception as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500



# Create Receive
@inventory.route('/api/inv/recv/new', methods=['POST'])
@token_required
def create_receive(curr_user):
    if not curr_user.can_receive():
        return ResponseMessage(False, message="Unauthorized user!").resp(), 401
    
    # query the whse
    whse = Warehouses.query.filter_by(whsecode=curr_user.whse).first()
    if whse.is_cutoff():
        return ResponseMessage(False, message="Your warehouse cutoff is enable!").resp(), 401

    data = request.get_json()
    details = data['details']
    data['header']['created_by'] = curr_user.id
    data['header']['updated_by'] = curr_user.id

    try:
        if data['header']['transtype'] in ['SAPIT', 'SAPPO']:
            if not data['header']['sap_number']:
                raise Exception("Missing SAP number!")
            elif type(int(data['header']['sap_number'])) != int:
                raise Exception("Invalid SAP number, must be integer!")
    except Exception as err:
        return ResponseMessage(False, message=f"{err}").resp(), 401

    if data['header']['transtype'] != 'TRFR':
        if not details:
            return ResponseMessage(False, message="No data in details argument!").resp(), 401

    try:
        obj = ObjectType.query.filter_by(code='RCVE').first()
        series = Series.query.filter_by(
            whsecode=curr_user.whse, objtype=obj.objtype).first()
        if series.next_num + 1 > series.end_num:
            raise Exception("Series number already in max!")
        if not series:
            raise Exception("Invalid Series")
        
        reference = f"{series.code}-{obj.code}-{series.next_num}"

        # add to header
        data['header']['series'] = series.id
        data['header']['objtype'] = obj.objtype
        data['header']['seriescode'] = series.code
        data['header']['transnumber'] = series.next_num
        data['header']['reference'] = reference


        r_h = ReceiveHeader(**data['header'])

        # add 1 to series next num
        series.next_num += 1

        db.session.add_all([r_h, series])
        db.session.flush()

        # if SAP IT
        if data['header']['transtype'] == 'SAPIT':

            if data['header']['sap_number']:
                if type(int(data['header']['sap_number'])) != int:
                    r_h.docstatus = 'O'
                else:
                    r_h.docstatus = 'C'

            for row in details:
                check = Check(**row)
                # check if valid
                if not check.itemcode_exist():
                    raise Exception("Invalid itemcode!")
                elif not check.uom_exist():
                    raise Exception("Invalid uom!")
                elif not check.towhse_exist():
                    raise Exception("Invalid to whse code!")
                if row['to_whse'] != curr_user.whse:
                    raise Exception(
                        "Invalid to_whse must be current user whse!")
                if row['actualrec'] < 1:
                    raise Exception("Cannot add if actual receive is less than 1.")

                r_r = ReceiveRow(receive_id=r_h.id, transnumber=r_h.transnumber,
                                 created_by=curr_user.id, updated_by=curr_user.id,
                                 sap_number=r_h.sap_number, objtype=r_h.objtype, **row)

                db.session.add(r_r)

        # if From SAP PO
        elif data['header']['transtype'] == 'SAPPO':
            if data['header']['sap_number']:
                if type(int(data['header']['sap_number'])) != int:
                    r_h.docstatus = 'O'
                else:
                    r_h.docstatus = 'C'

            for row in details:
                check = Check(**row)
                data['from_whse'] = data['header']['supplier']
                data['to_whse'] = curr_user.whse
                # check if valid
                if not check.itemcode_exist():
                    raise Exception("Invalid itemcode!")
                elif not check.uom_exist():
                    raise Exception("Invalid uom!")
                elif not check.towhse_exist():
                    raise Exception("Invalid to whse code!")
                if row['to_whse'] != curr_user.whse:
                    raise Exception("Invalid to_whse must be current user whse!")

                r_r = ReceiveRow(receive_id=r_h.id, transnumber=r_h.transnumber,
                                 created_by=curr_user.id, updated_by=curr_user.id,
                                 sap_number=r_h.sap_number, objtype=r_h.objtype, **row)

                db.session.add(r_r)

        # if from pos system transfer
        elif data['header']['transtype'] == 'TRFR':

            # transfer id
            base_id = data['header']['base_id']

            if base_id:
                transfer = TransferHeader.query.get(base_id)
                if not transfer:
                    raise Exception("Invalid base_id")
                transfer.docstatus = 'C'

                trans_row = TransferRow.query.filter_by(
                    transfer_id=base_id).all()
                if not trans_row:
                    raise Exception("No transfer rows!")

                for row in trans_row:
                    if row.to_whse != curr_user.whse:
                        raise Exception(
                            "Invalid to whse! Must be user warehouse!")
                    row.confirm = 1
                    r_r = ReceiveRow(receive_id=r_h.id, transnumber=r_h.transnumber,
                                     created_by=curr_user.id, updated_by=curr_user.id,
                                     sap_number=r_h.sap_number, objtype=r_h.objtype)
                    r_r.item_code = row.item_code
                    r_r.from_whse = row.from_whse
                    r_r.to_whse = row.to_whse
                    r_r.quantity = row.quantity
                    r_r.actualrec = row.quantity
                    r_r.uom = row.uom

                    db.session.add(r_r)

        # Manual
        elif data['header']['transtype'] not in ['TRFR', 'SAPIT', 'SAPPO']:
            for row in details:
                row['to_whse'] = curr_user.whse
                check = Check(**row)
                # check if valid
                if not check.itemcode_exist():
                    raise Exception("Invalid itemcode!")
                elif not check.uom_exist():
                    raise Exception("Invalid uom!")
                elif not check.fromwhse_exist():
                    raise Exception("Invalid from whse code!")
                elif not check.towhse_exist():
                    raise Exception("Invalid from whse code!")
                if row['to_whse'] != curr_user.whse:
                    raise Exception("Invalid to_whse!")

                r_r = ReceiveRow(receive_id=r_h.id, transnumber=r_h.transnumber,
                                 created_by=curr_user.id, updated_by=curr_user.id,
                                 sap_number=r_h.sap_number, objtype=r_h.objtype, **row)

                db.session.add(r_r)

        db.session.commit()
        recv_schema = ReceiveHeaderSchema(only=("id", "series", "seriescode", "transnumber",
                                                "sap_number", "docstatus", "transtype", "transdate", "reference",
                                                "reference2",
                                                "remarks", "recrow"))
        result = recv_schema.dump(r_h)
        return ResponseMessage(True, message="Successfully added!", data=result).resp()
    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        db.session.rollback()
        return ResponseMessage(False, message=f"{err}").resp(), 500
    except Exception as err:
        db.session.rollback()
        return ResponseMessage(False, message=f"{err}").resp(), 500
    finally:
        db.session.close()



# Get All Receive
@inventory.route('/api/inv/recv/get_all')
@token_required
def get_all_recv(curr_user):
    docstatus = request.args.get('docstatus')
    transnum = request.args.get('transnum')
    recv_schema = ReceiveHeaderSchema(many=True, only=("id", "series", "seriescode", "transnumber",
                                                       "sap_number", "docstatus", "transtype", "transdate", "reference",
                                                       "reference2",
                                                       "remarks"))

    if not docstatus or docstatus.title() == 'Open':
        if transnum:
            receive = db.session.query(ReceiveHeader). \
                filter(and_(ReceiveHeader.transnumber == transnum,
                            or_(ReceiveRow.from_whse == curr_user.whse,
                                ReceiveRow.to_whse == curr_user.whse),
                            ReceiveHeader.docstatus == 'O')).all()
        else:
            receive = db.session.query(ReceiveHeader). \
                filter(and_(ReceiveHeader.docstatus == 'O',
                            or_(ReceiveRow.from_whse == curr_user.whse,
                                ReceiveRow.to_whse == curr_user.whse))).all()
    elif docstatus.title() == 'Closed':
        if transnum:
            receive = db.session.query(ReceiveHeader). \
                filter(and_(ReceiveHeader.transnumber == transnum,
                            or_(ReceiveRow.from_whse == curr_user.whse,
                                ReceiveRow.to_whse == curr_user.whse),
                            ReceiveHeader.docstatus == 'C')).all()
        else:
            receive = db.session.query(ReceiveHeader). \
                filter(and_(ReceiveHeader.docstatus == 'C',
                            or_(ReceiveRow.from_whse == curr_user.whse,
                                ReceiveRow.to_whse == curr_user.whse))).all()
    else:
        if transnum:
            receive = db.session.query(ReceiveHeader). \
                filter(and_(ReceiveHeader.transnumber == transnum,
                            or_(TransferRow.from_whse == curr_user.whse,
                                TramsferRow.to_whse == curr_user.whse))).all()
        else:
            receive = db.session.query(ReceiveHeader). \
                filter(or_(ReceiveRow.from_whse == curr_user.whse,
                           ReceiveRow.to_whse == curr_user.whse)).all()

    result = recv_schema.dump(receive)
    return ResponseMessage(True, data=result).resp()



# Get Receive Details
@inventory.route('/api/inv/recv/details/<int:id>')
@token_required
def get_recv_details(curr_user, id):
    recv_schema = ReceiveHeaderSchema(only=("id", "series", "seriescode", "transnumber",
                                            "sap_number", "docstatus", "transtype", "transdate", "reference",
                                            "reference2",
                                            "remarks", "recrow"))

    try:
        receive = ReceiveHeader.query.get(id)
        if not receive:
            return ResponseMessage(False, message="Invalid receive id!").resp(), 401
    except:
        return ResponseMessage(False, message="Unknown error!").resp(), 401

    result = recv_schema.dump(receive)
    return ResponseMessage(True, data=result).resp()



# Cancel Receive
@inventory.route('/api/inv/recv/cancel/<int:id>')
@token_required
def cancel_recv(curr_user, id):
    if not current_user.is_admin():
        return ResponseMessage(False, message="Unauthorized user!").resp(), 401

    # query the whse
    whse = Warehouses.query.filter_by(whsecode=curr_user.whse).first()
    if whse.is_cutoff():
        return ResponseMessage(False, message="Your warehouse cutoff is enable!").resp(), 401

    data = request.get_json()

    try:
        receive = ReceiveHeader.query.get(id)
        if receive.docstatus == 'N':
            raise Exception("Already canceled!")
        receive.docstatus = 'N'
        receive.remarks = data['remarks']
        receive.updated_by = curr_user.id
        receive.date_updated = datetime.now()
        db.session.commit()

        return ResponseMessage(True, message='Successfully canceled!')
    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500
    except Exception as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500
    finally:
        db.session.close()



# Get All Warehouse Inv
@inventory.route('/api/inv/whseinv/getall')
@token_required
def get_whseinv(curr_user):
    try:
        whseinv = db.session.query(WhseInv).filter(
            and_(WhseInv.warehouse == curr_user.whse, WhseInv.quantity > 0)).all()

        whseinv_schema = WhseInvSchema(
            many=True, only=("item_code", "quantity", "item"))
        result = whseinv_schema.dump(whseinv)
        return ResponseMessage(True, data=result).resp()
    except Exception as err:
        return ResponseMessage(False, message=f"{err}").resp(), 401



# Inventory Report Per Warehouse
@inventory.route('/api/inv/warehouse/report')
@token_required
def get_inventory_report_per_whse(curr_user):
    try:
        branch = request.args.get('branch')
        whse = request.args.get('whse')
        from_date = request.args.get('from_date')
        to_date = request.args.get('to_date')
        query = """
            Declare @branch varchar(100)
            Declare @whse varchar(100)
            Declare @fromdate varchar(100)
            Declare @todate varchar(100)
            
            SET @branch = '{}'
            SET @whse = '{}'
            SET @fromdate = '{}'
            SET @todate = '{}'
            
            SELECT x.*, x.[Beginning] + x.[Received] - x.[Transferred] - x.[Sold] [Available]
            FROM(
            SELECT 
                a1.item_code,
                ISNULL((SELECT SUM(T1.inqty-T1.outqty) 
                    FROM tblwhstransaction T1 inner join tblwhses T2 on T1.warehouse = T2.whsecode
                    WHERE T1.item_code = a1.item_code 
                    and (@whse IS NULL OR T1.warehouse = @whse) and (@branch IS NULL or T2.branch = @branch)
                    and (@fromdate IS NULL OR T1.transdate < @fromdate)
                    ),0) [Beginning],
                SUM(ISNULL(CASE WHEN a1.objtype = 2
                    THEN a1.inqty - a1.outqty
                    END,0)) [Received],
                SUM(ISNULL(CASE WHEN a1.objtype = 1 
                    THEN a1.outqty - a1.inqty
                    END,0)) [Transferred],	
                SUM(ISNULL(CASE WHEN a1.objtype = 3
                    THEN  a1.outqty - a1.inqty
                    END,0)) [Sold]
            
            FROM tblwhstransaction a1 
            inner join tblwhses a2 on a1.warehouse = a2.whsecode
            where (@fromdate IS NULL OR CAST(a1.transdate as DATE) >= @fromdate) 
            and (@todate IS NULL OR CAST(a1.transdate as DATE) <= @todate) 
            and (@branch IS NULL OR branch = @branch)
            and (@whse IS NULL OR warehouse = @whse)
            GROUP BY a1.item_code)x"""
        execute = db.engine.execute(query.format(branch, whse, from_date, to_date))
        result = [dict(row) for row in execute]
        return ResponseMessage(True, data=result).resp()
    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500
    except Exception as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500



# Create New Item Request
@inventory.route('/api/inv/item_request/new', methods=['POST'])
@token_required
def create_item_request(curr_user):
    try:
        data = request.get_json()
        header = data['header']
        details = data['rows']
        obj = ObjectType.query.filter_by(code='REQT').first()
        series = Series.query.filter_by(
            whsecode=curr_user.whse, objtype=obj.objtype).first()
        if series.next_num + 1 > series.end_num:
            raise Exception("Series number already in max!")
        if not series:
            raise Exception("Invalid Series")
        
        reference = f"{series.code}-{obj.code}-{series.next_num}"
        req_header = ItemRequest(series=series.id, seriescode=series.code,
                            transnumber=series.next_num, reference=reference, 
                            objtype=obj.objtype, **header)
        req_header.created_by = curr_user.id
        req_header.updated_by = curr_user.id

        # add 1 to next num series
        series.next_num += 1
        
        db.session.add_all([req_header, series])
        db.session.flush()

        for row in details:
            if row['to_whse'] != curr_user.whse and not curr_user.is_admin():
                raise Exception(f"'{row['to_whse']}' is not equal to your user warehouse!")

            check = Check(**row)
            # check if valid
            if not check.itemcode_exist():
                raise Exception("Invalid itemcode!")
            elif not check.uom_exist():
                raise Exception("Invalid uom!")
            elif not check.fromwhse_exist():
                raise Exception("Invalid from whse code!")
            elif not check.towhse_exist():
                raise Exception("Invalid to whse code!")

            req_row = ItemRequestRow(request_id=req_header.id, objtype=req_header.objtype, 
                                    created_by=req_header.created_by,
                                    updated_by=req_header.updated_by,
                                    **row)
            db.session.add(req_row)
            
        db.session.commit()
        
        request_schema = ItemRequestSchema()
        result = request_schema.dump(req_header)
        return ResponseMessage(True, message="Successfully added!", data=result).resp()
        
    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500
    except Exception as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500



# Get All Item Request
@inventory.route('/api/inv/item_request/get_all')
@token_required
def get_all_item_request(curr_user):
    
    try:
        from_whse = curr_user.whse if not curr_user.is_admin() else request.args.get('from_whse')
        to_whse = request.args.get('to_whse')

        filt = []

        if from_whse:
            filt.append(("from_whse", "==", from_whse))
        if to_whse:
            filt.append(("to_whse", "==", to_whse))

        request_filter = BaseQuery.create_query_filter(ItemRequestRow, filters={'and': filt})
        request = db.session.query(ItemRequest).filter(*request_filter).all()

        request_schema = ItemRequestSchema(many=True, exclude=("date_created", "date_udpated", "created_by", "updated_by",))
        result = request_schema.dump(request)
        return ResponseMessage(True, message="Successfully added!", data=result).resp()
    
    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500
    except Exception as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500


# Get Item Request Details
@inventory.route('/api/inv/item_request/details/<int:id>')
@token_required
def get_item_request_details(curr_user):

    try:
        item_req = ItemRequest.query.get(id)
        request_schema = ItemRequestSchema()
        result = request_schema.dump(request)
        return ResponseMessage(True, message="Successfully added!", data=result).resp()
    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500
    except Exception as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500


# Cancel Item Request
@inventory.route('/api/inv/item_request/cancel/<int:id>')
@token_required
def cancel_item_request(curr_user):

    try:
        data = request.get_json()
        item_req = ItemRequest.query.get(id)
        if not item_req:
            raise Exception("Invalid item request id!")
        item_req.remarks = data['remarks']
        item_req.docstatus = 'N'
        request_schema = ItemRequestSchema()
        result = request_schema.dump(request)
        return ResponseMessage(True, message="Successfully added!", data=result).resp()
    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500
    except Exception as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500


# Create Inventory Count
@inventory.route('/api/inv/count/create', methods=['POST', 'GET'])
@token_required
def create_inv_count(curr_user):

    if request.method == 'GET':
        try:
            # query the whse and check if the cutoff is true
            whse = Warehouses.query.filter_by(whsecode=curr_user.whse).first()
            if not whse.is_cutoff():
                return ResponseMessage(False, message="Cutoff is disable").resp(), 401
            if not curr_user.is_manager():
                whseinv = WhseInv.query.filter(warehouse == curr_user.whse).all()
                whseinv_schema = WhseInvSchema(many=True)

        except (pyodbc.IntegrityError, exc.IntegrityError) as err:
            return ResponseMessage(False, message=f"{err}").resp()
        except Exception as err:
            return ResponseMessage(False, message=f"{err}").resp()
    elif request.method == 'POST':
        try:
            # query the whse and check if the cutoff is true
            whse = Warehouses.query.filter_by(whsecode=curr_user.whse).first()
            if not whse.is_cutoff():
                return ResponseMessage(False, message="Cutoff is disable").resp(), 401  
            pass
        except (pyodbc.IntegrityError, exc.IntegrityError) as err:
            return ResponseMessage(False, message=f"{err}").resp()
        except Exception as err:
            return ResponseMessage(False, message=f"{err}").resp()
    
        
    