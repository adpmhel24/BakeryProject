import json
import pyodbc
from datetime import datetime, date
from functools import wraps
from flask import Blueprint, request, jsonify, json
from flask_login import current_user
from sqlalchemy import exc, and_, or_, cast, Date
from bakery_app import db, auth
from bakery_app._utils import Check, ResponseMessage
from bakery_app.inventory.models import (Items, ItemGroup, UnitOfMeasure,
        TransferHeader, TransferRow, InvTransaction, ItemsSchema,
        ItemGroupSchema, UomSchema, WhseInvSchema, TransferHeaderSchema,
        TransferRowSchema, ReceiveHeader, ReceiveRow, ReceiveHeaderSchema,
        ReceiveRowSchema, WhseInv)
from bakery_app.branches.models import Branch, Series, Warehouses
from bakery_app.users.routes import token_required

inventory = Blueprint('inventory', __name__)

# Create New Item


@inventory.route('/api/item/create', methods=['POST'])
@token_required
def create_item(curr_user):
    user = curr_user
    if not user.is_admin():
        return jsonify({"success": False, "message": "You're not authorized!"})

    data = {
        'item_code': request.args.get('item_code'),
        'item_name': request.args.get('item_name'),
        'group_code': request.args.get('group_code'),
        'uom': request.args.get('uom'),
        'price': request.args.get('price'),
        'min_stock': request.args.get('min_stock'),
        'max_stock': request.args.get('max_stock'),
    }

    if not data['item_code'] or not data['item_name'] or not data['group_code'] or not data['price']:
        response = ResponseMessage(False, message="Missing required fields!")
        return response.resp()

    check = Check(**data)

    if not check.uom_exist():
        response = ResponseMessage(False, message="Uom doesn't exists!")
        return response.resp()

    if not check.itemgroup_exist():
        response = ResponseMessage(False, message="Item group doesn't exists!")
        return response.resp()

    if check.itemcode_exist():
        response = ResponseMessage(False, message="Item code already exists!")
        return response.resp()

    try:
        item = Items(item_code=data['item_code'], item_name=data['item_name'],
            item_group=data['group_code'].title(), uom=data['uom'], price=data['price'],
                created_by=user.id, updated_by=user.id)

        if data['min_stock']:
            item.min_stock = data['min_stock']

        if data['max_stock']:
            item.max_stock = data['max_stock']

        db.session.add(item)
        db.session.commit()
        item_schema = ItemsSchema()
        result = item_schema.dump(item)
        response = ResponseMessage(
            True, message="Successfully added!", data=result)
        return response.resp()
    except Exception as err:
        db.session.rollback()
        response = ResponseMessage(False, message=err)
        return response.resp()
    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        db.session.rollback()
        response = ResponseMessage(False, message=err)
        return response.resp()
    except:
        db.session.rollback()
        response = ResponseMessage(False, message="Unable to add!")
        return response.resp()
    finally:
        db.session.close()

# Get All Items
@inventory.route('/api/item/getall')
@token_required
def get_all_items(curr_user):

    q = request.args.get('q')

    if q:
        items = Items.query.filter(Items.item_code.contains(
            q) | Items.item_name.contains(q)).all()
    else:
        items = Items.query.all()

    item_schema = ItemsSchema(many=True, only=("id", "item_code", "item_name", "min_stock",
            "max_stock", "uom", "item_group",))
    result = item_schema.dump(items)
    return ResponseMessage(True, data=result).resp()

# Get Item detail
@inventory.route('/api/item/getdetail/<int:id>')
@token_required
def get_item_detail(curr_user, id):

    try:
        item = Items.query.get(id)
        if not item:
            response = ResponseMessage(False, message="Invalid Item id")
            return response.resp()
    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        response = ResponseMessage(False, message=err)
        return response.resp()
    except:
        response = ResponseMessage(False, message="Invalid Item id")
        return response.resp()

    item_schema = ItemsSchema()
    result = item_schema.dump(item)
    return ResponseMessage(True, data=result).resp()

# Update Item
@inventory.route('/api/item/update/<int:id>', methods=['PUT'])
@token_required
def update_item(curr_user, id):
    user = curr_user
    if not user.is_admin():
        return jsonify({"success": "false", "message": "You're not authorized!"})

    data = {
        'item_code': request.args.get('item_code'),
        'item_name': request.args.get('item_name'),
        'group_code': request.args.get('group_code'),
        'uom': request.args.get('uom'),
        'price': request.args.get('price'),
        'min_stock': request.args.get('min_stock'),
        'max_stock': request.args.get('max_stock'),
    }

    try:
        item = Items.query.get(id)
    except:
        response = ResponseMessage(False, message="Invalid item id!")
        return response.resp()

    check = Check(**data)
    if data['item_code']:
        if check.itemcode_exist():
            response = ResponseMessage(
                False, message="Item code already exists!")
            return response.resp()
        item.item_code = data['item_code']

    if data['item_name']:
        item.item_name = data['item_name']

    if data['uom']:
        if not check.uom_exist():
            response = ResponseMessage(False, message="Uom doesn't exists!")
            return response.resp()
        item.uom = data['uom']

    if data['group_code']:
        if not check.itemgroup_exist():
            response = ResponseMessage(
                False, message="Item group doesn't exists!")
            return response.resp()
        item.item_group = data['group_code']

    if data['min_stock']:
        item.min_stock = data['min_stock']
    if data['max_stock']:
        item.max_stock = data['max_stock']
    if data['price']:
        item.price = data['price']
    item.updated_by = user.id
    item.date_updated = datetime.now()

    try:
        db.session.commit()
        item_schema = ItemsSchema()
        result = item_schema.dump(item)
        return ResponseMessage(True, message="Succesfully updated", data=result).resp()
    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        db.session.rollback()
        response = ResponseMessage(False, message=err)
        return response.resp()
    except:
        db.session.rollback()
        return ResponseMessage(False, message="Unable to update!. Unknown error!")
    finally:
        db.session.close()

# Delete Item
@inventory.route('/api/item/delete/<int:id>', methods=['DELETE'])
@token_required
def delete_item(curr_user, id):
    if not curr_user.is_admin():
        return ResponseMessage(False, message="You're not authorized").resp()

    try:
        item = Items.query.get(id)
        if not item:
            return ResponseMessage(False, message="Invalid item id!")
        db.session.delete(item)
        db.session.commit()
        item_schema = ItemsSchema()
        result = item_schema.dump(item)
        return ResponseMessage(True, message="Successfully deleted!", data=result).resp()
    except (exc.IntegrityError, pyodbc.IntegrityError) as err:
        db.session.rollback()
        return ResponseMessage(False, message=err).resp()
    except Exception as err:
        db.session.rollback()
        return ResponseMessage(False, message=err).resp()
    except:
        db.session.rollback()
        return ResponseMessage(False, message="Unable to delete!").resp()
    finally:
        db.session.close()

# Create Item Group
@inventory.route('/api/item/item_grp/create', methods=['POST'])
@token_required
def create_itemgroup(curr_user):
    user = curr_user
    if not user.is_admin():
        return jsonify({"success": False, "message": "You're not authorized!"})

    data = {
        'code': request.args.get('code'),
        'description': request.args.get('description')
        }

    if not data['code'] or not data['description']:
        response = ResponseMessage(False, message="Missing required fields!")
        return response.resp()

    if ItemGroup.query.filter_by(code=data['code']).first():
        response = ResponseMessage(
            False, message="Item group code already exist")
        return response.resp()

    try:
        group = ItemGroup(code=data['code'], description=data['description'],
            created_by=user.id, updated_by=user.id)
        db.session.add(group)
        db.session.commit()
        group_schema = ItemGroupSchema()
        result = group_schema.dump(group)
        return ResponseMessage(True, message="Successfully added!", data=result).resp()

    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        db.session.rollback()
        return ResponseMessage(False, message="Unable to add!").resp()
    finally:
        db.session.close()

# Get All Item Group
@inventory.route('/api/item/item_grp/getall')
@token_required
def get_all_itemgrp(curr_user):

    q = request.args.get('q')
    if q:
        group = ItemGroup.query.filter(ItemGroup.code.contains(
            q) | ItemGroup.description.contains(q))
    else:
        group = ItemGroup.query.all()

    group_schema = ItemGroupSchema(
        many=True, only=("id", "code", "description",))
    result = group_schema.dump(group)
    return ResponseMessage(True, data=result).resp()


# Get Item Group details
@inventory.route('/api/item/item_grp/details/<int:id>')
@token_required
def get_itemgrp_details(curr_user, id):

    try:
        group = ItemGroup.query.get(id)
        if not group:
            return ResponseMessage(False, message="Invalid item group id!")
    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        return ResponseMessage(False, message=err).resp()

    group_schema = ItemGroupSchema()
    result = group_schema.dump(group)
    return ResponseMessage(True, data=result).resp()

# Update Item Group


@inventory.route('/api/item/item_grp/update/<int:id>', methods=['PUT'])
@token_required
def update_itemgrp(curr_user, id):
    if not curr_user.is_admin():
        return ResponseMessage(False, message="You're not authorized!")

    try:
        group = ItemGroup.query.get(id)
        if not group:
            return ResponseMessage('False', message="Invalid item group id!").resp()
    except:
        return ResponseMessage('False', message="Invalid item group id!").resp()

    data = {
        'code': request.args.get('code'),
        'description': request.args.get('description')
    }

    if ItemGroup.query.filter_by(code=data['code']).first():
        response = ResponseMessage(
            False, message="Item group code already exist")
        return response.resp()

    group.code = data['code']
    group.description = data['description']
    group.updated_by = curr_user.id
    group.date_updated = datetime.now()

    try:
        db.session.commit()
        group_schema = ItemGroupSchema()
        result = group_schema.dump(group)
        return ResponseMessage(True, data=result).resp()
    except (exc.IntegrityError, pyodbc.IntegrityError) as err:
        db.session.rollback()
        return ResponseMessage(False, message=f"{err}").resp()
    except Exception as err:
        db.session.rollback()
        return ResponseMessage(False, message=f"{err}").resp()
    except:
        db.session.rollback()
        return ResponseMessage(False, message="Unable to update!").resp()
    finally:
        db.session.close()


# Delete Item Group
@inventory.route('/api/item/item_grp/delete/<int:id>', methods=['DELETE'])
@token_required
def delete_itemgrp(curr_user, id):
    if not curr_user.is_admin():
        return ResponseMessage(False, message="You're not authorized!")

    try:
        group = ItemGroup.query.get(id)
        if not group:
            return ResponseMessage('False', message="Invalid item group id!").resp()
        db.session.delete(group)
        db.session.commit()
    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        db.session.rollback()
        return ResponseMessage(False, message=f"{err}").resp()
    except Exception as err:
        db.session.rollback()
        return ResponseMessage(False, message=f"{err}").resp()
    except:
        db.session.rollback()
        return ResponseMessage('False', message="Invalid item group id!").resp()
    finally:
        db.session.close()

    group_schema = ItemGroupSchema()
    result = group_schema.dump(group)
    return ResponseMessage(True, message="Successfully deleted!", data=result).resp()

# Create UoM


@inventory.route('/api/item/uom/create', methods=['POST'])
@token_required
def create_uom(curr_user):
    user = curr_user
    if not user.is_admin():
        return jsonify({"success": False, "message": "You're not authorized!"})

    code = request.args.get('code')
    description = request.args.get('description')

    if UnitOfMeasure.query.filter_by(code=code).first():
        return ResponseMessage(False, message="UoM code is already exists!").resp()
    try:
        uom = UnitOfMeasure(code=code, description=description,
                created_by=user.id, updated_by=user.id)
        db.session.add(uom)
        db.session.commit()
        uom_schema = UomSchema(only=("id", "code", "description"))
        result = uom_schema.dump(uom)
        return ResponseMessage(True, message="Successfully added!", data=result).resp()
    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        db.session.rollback()
        return ResponseMessage(False, message=f"{err}").resp()
    except Exception as err:
        db.session.rollback()
        return ResponseMessage(False, message=f"{err}").resp()
    except:
        db.session.rollback()
        return ResponseMessage(False, message="Unknown error!").resp()
    finally:
        db.session.close()


@inventory.route('/api/item/uom/getall')
@token_required
def get_all_uom(curr_user):

    q = request.args.get('q')
    if q:
        oum = UnitOfMeasure.query.filter(UnitOfMeasure.code.contains(
            q) | UnitOfMeasure.code.contains(q)).all()
    else:
        uom = UnitOfMeasure.query.all()

    uom_schema = UomSchema(many=True, only=('code', 'description',))
    result = uom_schema.dump(uom)
    return ResponseMessage(True, data=result).resp()


@inventory.route('/api/item/uom/details/<int:id>')
@token_required
def get_uom_details(curr_user, id):

    try:
        uom = UnitOfMeasure.query.get(id)
        if not uom:
            return ResponseMessage(False, message="Invalid uom id!")
        uom_schema = UomSchema()
        result = uom_schema.dump(uom)
        return ResponseMessage(True, data=result).resp()
    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        return ResponseMessage(False, message=f"{err}").resp()
    except Exception as err:
        db.session.rollback()
        return ResponseMessage(False, message=f"{err}").resp()
    except:
        return ResponseMessage(False, message="Unknown error!").resp()


@inventory.route('/api/item/uom/update/<int:id>', methods=['PUT'])
@token_required
def update_uom(curr_user, id):
    if not curr_user.is_admin():
        return ResponseMessage(False, message="You're not authorized!")

    code = request.args.get('code')
    description = request.args.get('description')

    try:
        uom = UnitOfMeasure.query.get(id)
        if not uom:
            return ResponseMessage(False, message="Invalid uom id!")
        uom.code = code
        uom.description = description
        uom.date_updated = datetime.now()
        uom.updated_by = curr_user.id

        db.commit()
        uom_schema = UomSchema()
        result = uom_schema.dump(uom)
        return ResponseMessage(True, message="Successfully updated!", data=result).resp()
    except (exc.IntegrityError, pyodbc.IntegrityError) as err:
        db.session.rollback()
        return ResponseMessage(False, message=f"{err}").resp()
    except Exception as err:
        db.session.rollback()
        return ResponseMessage(False, message=f"{err}").resp()
    except:
        db.session.rollback()
        return ResponseMessage(False, message="Unknown error!")
    finally:
        db.session.close()


@inventory.route('/api/item/uom/delete/<int:id>', methods=['DELETE'])
@token_required
def delete_uom(curr_user, id):
    if not curr_user.is_admin():
        return ResponseMessage(False, message="You're not authorized!")

    try:
        uom = UnitOfMeasure.query.get(id)
        if not uom:
            return ResponseMessage(False, message="Invalid uom id!")
        db.session.delete(uom)
        db.session.commit()
        uom_schema = UomSchema()
        result = uom_schema.dump(uom)
        return ResponseMessage(True, message="Successfully deleted!", data=result).resp()
    except (exc.IntegrityError, pyodbc.IntegrityError) as err:
        db.session.rollback()
        return ResponseMessage(False, message=err)
    except:
        db.session.rollback()
        return ResponseMessage(False, message="Unknown error!")
    finally:
        db.session.close()

@inventory.route('/api/inv/trfr/new', methods=['POST'])
@token_required
def create_transfer(curr_user):
    if not curr_user.can_transfer():
        return ResponseMessage(False, message="Unathorized to transfer!").resp()

    transdate = request.json['transdate']
    reference2 = request.json['ref2']
    remarks = request.json['remarks']
    sap_number = request.json['sap_num']
    details = request.json['details']

    if transdate:
        transdate = datetime.strptime(transdate, '%Y/%m/%d %H:%M')
    
    if not details:
            return ResponseMessage(False, message="No data in details argument!").resp()
            
    try:
        series = Series.query.filter_by(
            whsecode=curr_user.whse, objtype=1).first()
        if series.next_num + 1 > series.end_num:
            raise Exception("Series number already in max!")
        if not series:
            raise Exception("Invalid Series")

        reference = series.code + str(series.next_num)

        t_h = TransferHeader(series=series.id, seriescode=series.code,\
            transnumber=series.next_num, transdate=transdate,\
            reference=reference, reference2=reference2, remarks=remarks,\
            created_by=curr_user.id, updated_by=curr_user.id)

        # add 1 to series next num
        series.next_num += 1

        db.session.add_all([t_h, series])
        db.session.flush()

        for row in details:
            data = row
            # add to user whse to data dictionary as from whse
            data['from_whse'] = curr_user.whse
            check = Check(**data)

            # check if valid
            if not check.itemcode_exist():
                raise Exception("Invalid itemcode!")
            elif not check.uom_exist():
                raise Exception("Invalid uom!")
            elif not check.fromwhse_exist():
                raise Exception("Invalid from whse code!")
            elif not check.towhse_exist():
                raise Exception("Invalid from whse code!")
            if data['from_whse'] != curr_user.whse:
                raise Exception("Invalid from_whse!")

            # query first the quantity of inventory
            whseinv = WhseInv.query.filter_by(warehouse=data['from_whse'],
                    item_code=data['item_code']).first()

            # if below quantity raise an error!
            if data['quantity'] > whseinv.quantity:
                raise Exception("Below quantity stock!")

            # table row
            t_r = TransferRow(transfer_id=t_h.id, transnumber=t_h.transnumber, \
                item_code=data['item_code'], from_whse=data['from_whse'], \
                to_whse=data['to_whse'],quantity=data['quantity'], uom=data['uom'], \
                created_by=curr_user.id, updated_by=curr_user.id, sap_number=sap_number)

            db.session.add(t_r)
            db.session.flush()

        db.session.commit()
        trans_schema = TransferHeaderSchema()
        result = trans_schema.dump(t_h)
        return ResponseMessage(True, message="Successfully added!", data=result).resp()
    except Exception as err:
        db.session.rollback()
        return ResponseMessage(False, message=f"{err}").resp()
    except (exc.IntegrityError, pyodbc.IntegrityError) as err:
        db.session.rollback()
        return ResponseMessage(False, message=f"{err}").resp()
    except:
        db.session.rollback()
        return ResponseMessage(False, message="Unknown error!").resp()
    finally:
        db.session.close()

@inventory.route('/api/inv/trfr/getall')
@token_required
def get_all_transfer(curr_user):
    docstatus = request.args.get('docstatus')
    transnum = request.args.get('transnum')
    trans_schema = TransferHeaderSchema(many=True, only=("id", "transnumber", "sap_number",
            "transdate", "remarks", "docstatus"))

    if not docstatus or docstatus.title() == 'Open':
        if transnum:
            transfer = db.session.query(TransferHeader).\
                filter(and_(TransferHeader.transnumber==transnum, 
                            or_(TransferRow.from_whse==curr_user.whse, \
                            TramsferRow.to_whse==curr_user.whse),\
                            TransferHeader.docstatus=='O')).all()
        else:
            transfer = db.session.query(TransferHeader).\
                filter(and_(TransferRow.from_whse==curr_user.whse,
                TransferHeader.docstatus=='O')).all()

    elif docstatus.title() == 'Closed':
        if transnum:
            transfer = db.session.query(TransferHeader).\
                filter(and_(TransferHeader.transnumber==transnum, 
                            or_(TransferRow.from_whse==curr_user.whse, \
                            TramsferRow.to_whse==curr_user.whse),\
                            TransferHeader.docstatus=='C')).all()
        else:
            transfer = db.session.query(TransferHeader).\
                filter(and_(TransferRow.from_whse==curr_user.whse,\
                    TransferHeader.docstatus=='C')).all()
    elif docstatus.title() == 'All':
        if transnum:
            transfer = db.session.query(TransferHeader).\
                filter(and_(TransferHeader.transnumber==transnum, 
                            or_(TransferRow.from_whse==curr_user.whse, \
                            TramsferRow.to_whse==curr_user.whse))).all()
        else:
            transfer = db.session.query(TransferHeader).\
                filter(and_(TransferRow.from_whse==curr_user.whse)).all()

    result = trans_schema.dump(transfer)
    return ResponseMessage(True, data=result).resp()

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

@inventory.route('/api/inv/recv/new', methods=['POST'])
@token_required
def create_receive(curr_user):
    if not curr_user.can_receive():
        return ResponseMessage(False, message="Unathorized user!").resp()

    data = request.get_json()
    # manual, sap it, po, pos transfer
    transtype = data['transtype']
    sap_number = data['sap_num']
    transdate = data['transdate']  # transaction date
    remarks = data['remarks']
    base_id = data['transfer_id']  # from system transfer id
    reference2 = data['ref2']
    details = data['details']
    supplier = data['supplier']

    try:
        if transtype in ['SAPIT', 'SAPPO']:
            if not sap_number:
                raise Exception("Missing SAP number!")
            elif type(int(sap_number)) != int:
                raise Exception("Invalid SAP number, must be integer!")
    except Exception as err:
        return ResponseMessage(False, message=f"{err}").resp()

    if transtype != 'TRFR':
        if not details:
            return ResponseMessage(False, message="No data in details argument!")

    try:
        series = Series.query.filter_by(whsecode=curr_user.whse, objtype=2).first()
        if series.next_num + 1 > series.end_num:
            raise Exception("Series number already in max!")
        if not series:
            raise Exception("Invalid Series")

        reference = series.code + str(series.next_num)
        

        r_h = ReceiveHeader(series=series.id, seriescode=series.code,\
            transnumber=series.next_num, transdate=transdate,\
            reference=reference, reference2=reference2, remarks=remarks,\
            created_by=curr_user.id, updated_by=curr_user.id,\
            base_id=base_id, transtype=transtype, sap_number=sap_number)
        
        if sap_number:
            if type(int(sap_number)) != int:
                r_h.docstatus = 'C'
            else:
                r_h.docstatus = 'O'

        # add 1 to series next num
        series.next_num += 1

        db.session.add_all([r_h, series])
        db.session.flush()  
        # if SAP IT
        if transtype == 'SAPIT':
            for row in details:
                data = row
                check = Check(**data)
                # check if valid
                if not check.itemcode_exist():
                    raise Exception("Invalid itemcode!")
                elif not check.uom_exist():
                    raise Exception("Invalid uom!")
                elif not check.towhse_exist():
                    raise Exception("Invalid to whse code!")
                if data['to_whse'] != curr_user.whse:
                    raise Exception("Invalid to_whse must be current user whse!")

                r_r = ReceiveRow(receive_id=r_h.id, transnumber=r_h.transnumber,
                    created_by=curr_user.id, updated_by=curr_user.id,
                    sap_number=sap_number, item_code=data['item_code'],
                    from_whse=data['from_whse'], to_whse=data['to_whse'],
                    quantity=data['quantity'], actualrec=data['actualrec'],
                    uom=data['uom'])

                db.session.add(r_r)

        # if From SAP PO
        elif transtype == 'SAPPO':
            for row in details:
                data = row
                check = Check(**data)
                data['from_whse'] = supplier
                data['to_whse'] = curr_user.whse
                # check if valid
                if not check.itemcode_exist():
                    raise Exception("Invalid itemcode!")
                elif not check.uom_exist():
                    raise Exception("Invalid uom!")
                elif not check.towhse_exist():
                    raise Exception("Invalid from whse code!")
                if data['to_whse'] != curr_user.whse:
                    raise Exception("Invalid to_whse must be current user whse!")

                r_r = ReceiveRow(receive_id=r_h.id, transnumber=r_h.transnumber,\
                    created_by=curr_user.id, updated_by=curr_user.id,\
                    sap_number=sap_number, item_code=data['item_code'],\
                    from_whse=data['from_whse'], to_whse=data['to_whse'],\
                    quantity=data['quantity'], actualrec=data['actualrec'],\
                    uom=data['uom'])

                db.session.add(r_r)

        # if from pos system transfer
        elif transtype == 'TRFR':
            if base_id:
                transfer = TransferHeader.query.get(base_id)
                if not transfer:
                    raise Exception("Invalid transfer_id")
                transfer.docstatus = 'C'
                
                trans_row = TransferRow.query.filter_by(transfer_id=base_id).all()
                if not trans_row:
                    raise Exception("No transfer rows!")
                
                for row in trans_row:
                    if row.to_whse != curr_user.whse:
                        raise Exception("Invalid to whse! Must be user warehouse!")
                    row.confirm = 1
                    r_r = ReceiveRow(receive_id=r_h.id, transnumber=r_h.transnumber,\
                        created_by=curr_user.id, updated_by=curr_user.id,\
                        sap_number=r_h.sap_number)
                    r_r.item_code = row.item_code
                    r_r.from_whse = row.from_whse
                    r_r.to_whse = row.to_whse
                    r_r.quantity = row.quantity
                    r_r.actualrec = row.quantity
                    r_r.uom = row.uom

                    db.session.add(r_r)

        # Manual
        elif transtype not in ['TRFR', 'SAPIT', 'SAPPO']:
            for row in details:
                data = row
                check = Check(**data)

                # check if valid
                if not check.itemcode_exist():
                    raise Exception("Invalid itemcode!")
                elif not check.uom_exist():
                    raise Exception("Invalid uom!")
                elif not check.fromwhse_exist():
                    raise Exception("Invalid from whse code!")
                elif not check.towhse_exist():
                    raise Exception("Invalid from whse code!")
                if data['to_whse'] != curr_user.whse:
                    raise Exception("Invalid to_whse!")

                r_r = ReceiveRow(receive_id=r_h.id, transnumber=r_h.transnumber,\
                    created_by=curr_user.id, updated_by=curr_user.id,\
                    sap_number=r_h.sap_number, item_code=data['item_code'],\
                    from_whse=data['from_whse'], to_whse=data['to_whse'],\
                    quantity=data['actualrec'], actualrec=data['actualrec'],\
                    uom=data['uom'])

                db.session.add(r_r)

        db.session.commit()
        recv_schema = ReceiveHeaderSchema(only=("id", "series", "seriescode", "transnumber", \
                "sap_number", "docstatus", "transtype", "transdate", "reference", "reference2",\
                "remarks", "recrow"))
        result = recv_schema.dump(r_h)
        return ResponseMessage(True, message="Successfully added!", data=result).resp()
    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        db.session.rollback()
        return ResponseMessage(False, message=f"{err}").resp()
    except Exception as err:
        db.session.rollback()
        return ResponseMessage(False, message=f"{err}").resp()
    except:
        db.session.rollback()
        return ResponseMessage(False, message=f"Unknown error!").resp()
    finally:
        db.session.close()
        
@inventory.route('/api/inv/recv/getall')
@token_required
def get_all_recv(curr_user):
    docstatus = request.args.get('docstatus')
    transnum = request.args.get('transnum')
    recv_schema = ReceiveHeaderSchema(many=True, only=("id", "series", "seriescode", "transnumber", \
                "sap_number", "docstatus", "transtype", "transdate", "reference", "reference2",\
                "remarks"))

    if not docstatus or docstatus.title() == 'Open':
        if transnum:
            receive = db.session.query(ReceiveHeader).\
                filter(and_(ReceiveHeader.transnumber==transnum, 
                            or_(ReceiveRow.from_whse==curr_user.whse, \
                            ReceiveRow.to_whse==curr_user.whse),\
                            ReceiveHeader.docstatus=='O')).all()
        else:
            receive = db.session.query(ReceiveHeader).\
                filter(and_(ReceiveHeader.docstatus=='O',
                    or_(ReceiveRow.from_whse==curr_user.whse,\
                        ReceiveRow.to_whse==curr_user.whse))).all()
    elif docstatus.title() == 'Closed':
        if transnum:
            receive = db.session.query(ReceiveHeader).\
                filter(and_(ReceiveHeader.transnumber==transnum, 
                            or_(ReceiveRow.from_whse==curr_user.whse, \
                            ReceiveRow.to_whse==curr_user.whse),\
                            ReceiveHeader.docstatus=='C')).all()
        else:
            receive = db.session.query(ReceiveHeader).\
                filter(and_(ReceiveHeader.docstatus=='C',
                    or_(ReceiveRow.from_whse==curr_user.whse,\
                        ReceiveRow.to_whse==curr_user.whse))).all()
    else:
        if transnum:
            receive = db.session.query(ReceiveHeader).\
                filter(and_(ReceiveHeader.transnumber==transnum, 
                            or_(TransferRow.from_whse==curr_user.whse, \
                            TramsferRow.to_whse==curr_user.whse))).all()
        else:
            receive = db.session.query(ReceiveHeader).\
                filter(or_(ReceiveRow.from_whse==curr_user.whse,\
                        ReceiveRow.to_whse==curr_user.whse)).all()
    
    result = recv_schema.dump(receive)
    return ResponseMessage(True, data=result).resp()

@inventory.route('/api/inv/recv/getdetails/<int:id>')
@token_required
def get_recv_details(curr_user, id):

    recv_schema = ReceiveHeaderSchema(only=("id", "series", "seriescode", "transnumber", \
                "sap_number", "docstatus", "transtype", "transdate", "reference", "reference2",\
                "remarks", "recrow"))
    
    try:
        receive = ReceiveHeader.query.get(id)
        if not receive:
            return ResponseMessage(False, message="Invalid receive id!")
    except:
        return ResponseMessage(False, message="Unknown error!").resp()

    result = recv_schema.dump(receive)
    return ResponseMessage(True, data=result).resp()

@inventory.route('/api/inv/whseinv/getall')
@token_required
def get_whseinv(curr_user):
    
    whseinv = WhseInv.query.filter_by(warehouse=curr_user.whse).all()

    whseinv_schema = WhseInvSchema(many=True)
    result = whseinv_schema.dump(whseinv)
    return ResponseMessage(True, data=result).resp()