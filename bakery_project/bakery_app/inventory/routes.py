import pyodbc

from datetime import datetime
from flask import Blueprint, request
from sqlalchemy import exc, and_, or_, DATE, func

from bakery_app import db
from bakery_app._utils import Check, ResponseMessage
from bakery_app._helpers import BaseQuery
from bakery_app.users.models import User
from bakery_app.branches.models import Series, ObjectType, Warehouses
from bakery_app.users.routes import token_required
from bakery_app.items.models import PriceListRow, Items

from .models import (TransferHeader, TransferRow, ReceiveHeader, ReceiveRow,
                     WhseInv, ITRow, ITHeader, POHeader, PORow)
from .inv_schema import (TransferHeaderSchema, ReceiveHeaderSchema,
                         WhseInvSchema)

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
    try:

        data = request.args.to_dict()
        date = ''
        user_filt = []
        filt = []
        whse_filt = []
        row_filt = []

        for k, v in data.items():
            if k == 'transdate':
                if v:
                    date = v
            elif k == 'user':
                if v:
                    user_filt.append(('id', 'like', v))
            elif 'sap_number' == k:
                if v:
                    filt.append((k, "==", v))
                else:
                    filt.append((k, "==", None))
            elif 'branch' == k and v:
                whse_filt.append((k, "==", v))
            elif 'from_whse' == k and v:
                row_filt.append((k, "==", v))
            elif 'to_whse' == k and v:
                row_filt.append((k, "==", v))
            else:
                if v:
                    filt.append((k, "==", v))

        user_filters = BaseQuery.create_query_filter(User, filters={'and': user_filt})
        row_filters = BaseQuery.create_query_filter(TransferRow, filters={'and': row_filt})
        trans_filters = BaseQuery.create_query_filter(TransferHeader, filters={'and': filt})
        whse_filters = BaseQuery.create_query_filter(Warehouses, filters={"and": whse_filt})

        if date:
            trans_filters.append((func.cast(TransferHeader.transdate, DATE) == date))

        transfer = db.session.query(TransferHeader).\
            select_from(TransferHeader).\
            join(TransferRow, TransferRow.transfer_id == TransferHeader.id).\
            join(Warehouses, Warehouses.whsecode == TransferRow.to_whse).\
            outerjoin(User, TransferHeader.created_by == User.id).\
            filter(and_(
                 *trans_filters,
                 *user_filters,
                 *row_filters,
                 *whse_filters)).all()

        trans_schema = TransferHeaderSchema(many=True, only=("id", "transnumber", "sap_number",
                                                             "transdate", "remarks", "docstatus", "reference"))
        result = trans_schema.dump(transfer)
        return ResponseMessage(True, data=result).resp()
    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        return ResponseMessage(True, message=f'{err}').resp(), 500
    except Exception as err:
        return ResponseMessage(True, message=f'{err}').resp(), 500
    finally:
        db.session.close()


# Get Transfer Details
@inventory.route('/api/inv/trfr/getdetails/<int:id>')
@token_required
def transfer_details(curr_user, id):
    trans_schema = TransferHeaderSchema(only=("id", "transnumber", "sap_number",
                                              "transdate", "remarks", "docstatus", "reference", "transrow"))
    try:
        transfer = TransferHeader.query.get(id)

        result = trans_schema.dump(transfer)
        return ResponseMessage(True, data=result).resp()
    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        return ResponseMessage(True, message=f'{err}').resp(), 500
    except Exception as err:
        return ResponseMessage(True, message=f'{err}').resp(), 500
    finally:
        db.session.close()


# Cancel Transfer
@inventory.route('/api/inv/trfr/cancel/<int:id>', methods=['PUT'])
@token_required
def cancel_transfer(curr_user, id):
    if not curr_user.is_admin() and not curr_user.is_manager():
        return ResponseMessage(False, message="Unauthorized user!").resp(), 401

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
        return ResponseMessage(True, message='Transfer successfully canceled!').resp()

    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        print(err)
        db.session.rollback()
        return ResponseMessage(True, message=f'{err}').resp(), 500
    except Exception as err:
        print(err)
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

        it = ITHeader.query.filter(and_(ITHeader.docnum == r_h.sap_number, 
                                        ITHeader.docstatus.in_(['C', 'N']))).first()
        if it:
            if it.docstatus == 'C':
                raise Exception("Document is already closed!")
            raise Exception("Document is already canceled!")

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

                for row in details:
                    check = Check(**row)
                    # check if valid
                    if not check.itemcode_exist():
                        raise Exception("Invalid item code!")
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

        # Manual
        elif data['header']['transtype'] not in ['TRFR', 'SAPIT', 'SAPPO']:
            for row in details:
                row['to_whse'] = curr_user.whse
                check = Check(**row)
                # check if valid
                if r_h.type2.upper() == 'SAPIT':
                    if not check.fromwhse_exist():
                        raise Exception("Invalid from whse code!")
                if not check.itemcode_exist():
                    raise Exception("Invalid item code!")
                elif not check.uom_exist():
                    raise Exception("Invalid uom!")
                elif not check.towhse_exist():
                    raise Exception("Invalid from whse code!")
                if row['to_whse'] != curr_user.whse:
                    raise Exception("Invalid to_whse!")

                r_r = ReceiveRow(receive_id=r_h.id, transnumber=r_h.transnumber,
                                 created_by=curr_user.id, updated_by=curr_user.id,
                                 sap_number=r_h.sap_number, objtype=r_h.objtype, **row)

                db.session.add(r_r)
        
        # Check and Update docstatus of SAP IT Table
        if r_h.transtype == 'SAPIT':
            it_header = ITHeader.query.filter(and_(ITHeader.docnum == r_h.sap_number, 
                                                ITRow.actual_rec != None,
                                                ITHeader.docstatus == 'O')).first()
            it_header.docstatus = 'C'
        # Check and Update docstatus of SAP PO table
        if r_h.transtype == 'SAPPO':
            po_header = POHeader.query.filter(and_(POHeader.docnum == r_h.sap_number, 
                                                PORow.actual_rec != None,
                                                POHeader.docstatus == 'O')).first()
            po_header.docstatus = 'C'

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
        db.session.rollback()
        db.session.close()


# Get All Receive
@inventory.route('/api/inv/recv/get_all')
@token_required
def get_all_recv(curr_user):
    try:

        data = request.args.to_dict()
        date = ''
        filt = []
        row_filt = []
        whse_filt = []

        for k, v in data.items():
            if k == 'transdate':
                if v:
                    date = v
            elif 'sap_number' == k:
                if not v:
                    filt.append((k, '==', None))
                elif v:
                    filt.append((k, '==', v))
            elif 'branch' == k and v:
                whse_filt.append((k, "==", v))
            elif 'from_whse' == k and v:
                row_filt.append((k, "==", v))
            elif 'to_whse' == k and v:
                row_filt.append((k, "==", v))
            else:
                if v:
                    filt.append((k, "==", v))

        rec_filters = BaseQuery.create_query_filter(ReceiveHeader, filters={'and': filt})
        row_filters = BaseQuery.create_query_filter(ReceiveRow, filters={'and': row_filt})
        whse_filters = BaseQuery.create_query_filter(Warehouses, filters={"and": whse_filt})

        if date:
            rec_filters.append((func.cast(ReceiveHeader.transdate, DATE) == date))

        receive = db.session.query(ReceiveHeader).\
            select_from(ReceiveHeader).\
            join(ReceiveRow, ReceiveRow.receive_id == ReceiveHeader.id).\
            join(Warehouses, ReceiveRow.to_whse == Warehouses.whsecode).\
            filter(and_(*rec_filters,
                        *row_filters,
                        *whse_filters)).\
            all()

        recv_schema = ReceiveHeaderSchema(many=True, only=("id", "series", "seriescode", "transnumber",
                                                           "sap_number", "docstatus", "transtype", "transdate",
                                                           "reference",
                                                           "reference2",
                                                           "remarks"))
        result = recv_schema.dump(receive)
        return ResponseMessage(True, count=len(result), data=result).resp()

    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        return ResponseMessage(True, message=f'{err}').resp(), 500
    except Exception as err:
        return ResponseMessage(True, message=f'{err}').resp(), 500
    finally:
        db.session.close()


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
        result = recv_schema.dump(receive)
        return ResponseMessage(True, data=result).resp()

    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        return ResponseMessage(True, message=f'{err}').resp(), 500
    except Exception as err:
        return ResponseMessage(True, message=f'{err}').resp(), 500
    finally:
        db.session.close()


# Cancel Receive
@inventory.route('/api/inv/recv/cancel/<int:id>', methods=['PUT'])
@token_required
def cancel_recv(curr_user, id):
    if not curr_user.is_admin():
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

        return ResponseMessage(True, message='Successfully canceled!').resp()
    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500
    except Exception as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500
    finally:
        db.session.close()


# Update SAP Number in Received Transaction
@inventory.route('/api/inv/recv/update/<int:id>', methods=['PUT'])
@token_required
def update_receive_sap_number(curr_user, id):
    if not curr_user.is_admin() and not curr_user.is_can_add_sap():
        return ResponseMessage(False, message="Unauthorized user!").resp(), 401
    try:
        sap_number = request.json['sap_number']

        receive = ReceiveHeader.query.get(id)
        
        receive.sap_number = sap_number
        receive.updated_by = curr_user.id
        receive.date_updated = datetime.now()

        row = ReceiveRow.query.filter(ReceiveRow.receive_id == id).all()
        for i in row:
            i.sap_number == sap_number
            i.updated_by = curr_user.id
            i.date_updated = datetime.now()

        receive.docstatus = 'C'
        db.session.commit()

        return ResponseMessage(True, message='Successfully updated!').resp()

        
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
        whseinv = db.session.query(WhseInv.item_code,
                                   WhseInv.quantity,
                                   PriceListRow.price,
                                   Items.uom
                                   ).join(
            Warehouses, WhseInv.warehouse == Warehouses.whsecode
        ).outerjoin(
            Items, Items.item_code == WhseInv.item_code
        ).outerjoin(
            PriceListRow,
            and_(PriceListRow.pricelist_id == Warehouses.pricelist,
                 PriceListRow.item_code == WhseInv.item_code)
        ).filter(
            and_(WhseInv.warehouse == curr_user.whse, WhseInv.quantity > 0)
        ).order_by(WhseInv.item_code, WhseInv.quantity.desc()
        ).all()

        whseinv_schema = WhseInvSchema(many=True)
        result = whseinv_schema.dump(whseinv)
        return ResponseMessage(True, data=result).resp()
    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500
    except Exception as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500
    finally:
        db.session.close()


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
            
            SELECT x.*
            , x.[Beginning] + x.[Received] + x.TransferIn + x.AdjIn [TotalIn]
            , x.[Beginning] + x.[Received] + x.TransferIn + x.AdjIn - x.AdjOut - x.[Transferred] - x.PullOut - x.[Sold] [Available]
            FROM(
            SELECT 
                a1.item_code,
                ISNULL((SELECT SUM(T1.inqty-T1.outqty) 
                    FROM tblwhstransaction T1 inner join tblwhses T2 on T1.warehouse = T2.whsecode
                    WHERE T1.item_code = a1.item_code 
                    and (@whse IS NULL OR T1.warehouse = @whse) and (@branch IS NULL or T2.branch = @branch)
                    and (@fromdate IS NULL OR T1.transdate < @fromdate)
                    ),0) [Beginning],

                SUM(ISNULL(CASE WHEN a1.objtype = 2 and a3.transtype != 'TRFR' and (@fromdate IS NULL OR CAST(a1.transdate as DATE) >= @fromdate) 
            and (@todate IS NULL OR CAST(a1.transdate as DATE) <= @todate) 
                    THEN a1.inqty - a1.outqty
                    END,0)) [Received],

				SUM(ISNULL(CASE WHEN a1.objtype = 2 and a3.transtype = 'TRFR' and (@fromdate IS NULL OR CAST(a1.transdate as DATE) >= @fromdate) 
            and (@todate IS NULL OR CAST(a1.transdate as DATE) <= @todate) 
                    THEN a1.inqty - a1.outqty
                    END,0)) [TransferIn],

				SUM(ISNULL(CASE WHEN a1.objtype = 9 and (@fromdate IS NULL OR CAST(a1.transdate as DATE) >= @fromdate) 
            and (@todate IS NULL OR CAST(a1.transdate as DATE) <= @todate) 
                    THEN a1.inqty - a1.outqty
                    END,0)) [AdjIn],
				SUM(ISNULL(CASE WHEN a1.objtype = 12 and (@fromdate IS NULL OR CAST(a1.transdate as DATE) >= @fromdate) 
            and (@todate IS NULL OR CAST(a1.transdate as DATE) <= @todate) 
                    THEN a1.outqty - a1.inqty
                    END,0)) [AdjOut],
                SUM(ISNULL(CASE WHEN a1.objtype = 1 and (@fromdate IS NULL OR CAST(a1.transdate as DATE) >= @fromdate) 
            and (@todate IS NULL OR CAST(a1.transdate as DATE) <= @todate) 
                    THEN a1.outqty - a1.inqty
                    END,0)) [Transferred],
				SUM(ISNULL(CASE WHEN a1.objtype = 11 and (@fromdate IS NULL OR CAST(a1.transdate as DATE) >= @fromdate) 
            and (@todate IS NULL OR CAST(a1.transdate as DATE) <= @todate) 
                    THEN a1.outqty - a1.inqty
                    END,0)) [PullOut],
                SUM(ISNULL(CASE WHEN a1.objtype = 3 and (@fromdate IS NULL OR CAST(a1.transdate as DATE) >= @fromdate) 
            and (@todate IS NULL OR CAST(a1.transdate as DATE) <= @todate) 
                    THEN  a1.outqty - a1.inqty
                    END,0)) [Sold]
            
            FROM tblwhstransaction a1 
            inner join tblwhses a2 on a1.warehouse = a2.whsecode
			left join tblreceive a3 on a1.objtype = a3.objtype and a1.trans_id = a3.id
            where (@branch IS NULL OR branch = @branch)
            and (@whse IS NULL OR warehouse = @whse)
            GROUP BY a1.item_code)x"""
        execute = db.engine.execute(query.format(branch, whse, from_date, to_date))
        result = [dict(row) for row in execute]
        return ResponseMessage(True, data=result).resp()
    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500
    except Exception as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500
