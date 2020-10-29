import json
import pyodbc

from datetime import datetime, date
from flask import Blueprint, request, jsonify, json
from flask_login import current_user
from sqlalchemy import exc, and_, or_, cast, Date

from bakery_app import db, auth
from bakery_app._utils import Check, ResponseMessage
from bakery_app.users.routes import token_required

from bakery_app.master_data.models import Items, ItemGroup, UnitOfMeasure
from bakery_app.master_data.md_schema import *

master_data = Blueprint('master_data', __name__)


# Create New Item
@master_data.route('/api/item/new', methods=['POST'])
@token_required
def create_item(curr_user):
    user = curr_user
    if not user.is_admin():
        return ResponseMessage(False, message="Unauthorized user!").resp(), 401

    data = request.get_json()

    try:

        success = []
        unsuccess = []

        for row in data:
            row['created_by'] = curr_user.id
            row['updated_by'] = curr_user.id

            if not row['item_code'] or not row['item_name'] or not row['item_group'] or not row['price']:
                return ResponseMessage(
                    False, message="Missing required fields!").resp(), 401
            check = Check(**row)

            # initialize dictionary to append in success or unsuccess list
            d = {}
            id = row['item_code']
            d[id] = []

            if not check.uom_exist():
                d[id].append(f"Uom '{row['uom']}' not exists!")
                unsuccess.append(d)
                continue

            if not check.itemgroup_exist():
                unsuccess.append(d)
                d[id].append(f"Item group '{row['item_group']}' not exists!")
                continue

            if check.itemcode_exist():
                unsuccess.append(d)
                d[id].append(f"Item code '{row['item_code']}' already exists!")
                continue

            item = Items(**row)
            success.append(d)
            db.session.add(item)
            
        db.session.commit()
        return ResponseMessage(True, data={"Successfully": success, "Unsuccessful ": unsuccess}).resp()
    except Exception as err:
        db.session.rollback()
        return ResponseMessage(False, message=f'{err}').resp(), 401
    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        db.session.rollback()
        return ResponseMessage(False, message=f'{err}').resp(), 401
    except:
        db.session.rollback()
        return ResponseMessage(False, message="Unknown error").resp(), 401
    finally:
        db.session.close()


# Get All Items
@master_data.route('/api/item/getall')
@token_required
def get_all_items(curr_user):

    q = request.args.get('q')

    if q:
        items = Items.query.filter(Items.item_code.contains(
            q.upper()) | Items.item_name.contains(q.upper())).all()
    else:
        items = Items.query.all()

    item_schema = ItemsSchema(many=True, only=("id", "item_code", "item_name", "min_stock",
                                               "max_stock", "uom", "item_group",))
    result = item_schema.dump(items)
    return ResponseMessage(True, data=result).resp()


# Get Item detail
@master_data.route('/api/item/getdetail/<int:id>')
@token_required
def get_item_detail(curr_user, id):

    try:
        item = Items.query.get(id)
        if not item:
            return ResponseMessage(False, message="Invalid Item id").resp(), 401
    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        return ResponseMessage(False, message=f"{err}").resp(), 401
    except:
        return ResponseMessage(False, message="Invalid Item id").resp(), 401

    item_schema = ItemsSchema()
    result = item_schema.dump(item)
    return ResponseMessage(True, data=result).resp()


# Update Item
@master_data.route('/api/item/update/<int:id>', methods=['PUT'])
@token_required
def update_item(curr_user, id):
    user = curr_user
    if not user.is_admin():
        return ResponseMessage(False, message="Unauthorized user!").resp(), 401

    data = request.get_json()

    try:
        item = Items.query.get(id)
    except:
        return ResponseMessage(False, message="Invalid item id!").resp(), 401

    check = Check(**data)
    if data['item_code']:
        if check.itemcode_exist():
            return ResponseMessage(False, message="Item code already exists!").resp(), 401
        item.item_code = data['item_code']

    if data['item_name']:
        item.item_name = data['item_name']

    if data['uom']:
        if not check.uom_exist():
            return ResponseMessage(False, message="Uom doesn't exists!").resp(), 401
        item.uom = data['uom']

    if data['group_code']:
        if not check.itemgroup_exist():
            return ResponseMessage(False, message="Item group doesn't exists!").resp(), 401
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
        return ResponseMessage(False, message=f"{err}").resp(), 401
    except:
        db.session.rollback()
        return ResponseMessage(False, message="Unable to update!. Unknown error!").resp(), 401
    finally:
        db.session.close()


# Delete Item
@master_data.route('/api/item/delete/<int:id>', methods=['DELETE'])
@token_required
def delete_item(curr_user, id):
    if not curr_user.is_admin():
        return ResponseMessage(False, message="You're not authorized").resp(), 401

    try:
        item = Items.query.get(id)
        if not item:
            return ResponseMessage(False, message="Invalid item id!")
        db.session.delete(item)
        db.session.commit()
        item_schema = ItemsSchema()
        result = item_schema.dump(item)
        return ResponseMessage(True, message="Successfully deleted!", data=result).resp(), 401
    except (exc.IntegrityError, pyodbc.IntegrityError) as err:
        db.session.rollback()
        return ResponseMessage(False, message=err).resp(), 401
    except Exception as err:
        db.session.rollback()
        return ResponseMessage(False, message=err).resp(), 401
    except:
        db.session.rollback()
        return ResponseMessage(False, message="Unable to delete!").resp(), 401
    finally:
        db.session.close()


# Create Item Group
@master_data.route('/api/item/item_grp/create', methods=['POST'])
@token_required
def create_itemgroup(curr_user):
    user = curr_user
    if not user.is_admin():
        return ResponseMessage(False, message="Unathorized user!").resp(), 401

    data = {
        'code': request.args.get('code'),
        'description': request.args.get('description')
    }

    if not data['code'] or not data['description']:
        return ResponseMessage(False, message="Missing required fields!").resp(), 401

    if ItemGroup.query.filter_by(code=data['code']).first():
        return ResponseMessage(False, message="Item group code already exist").resp(), 401

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
        return ResponseMessage(False, message=f"{err}").resp(), 401
    except Exception as err:
        db.session.rollback()
        return ResponseMessage(False, message=f"{err}").resp(), 401
    finally:
        db.session.close()


# Get All Item Group
@master_data.route('/api/item/item_grp/getall')
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
@master_data.route('/api/item/item_grp/details/<int:id>')
@token_required
def get_itemgrp_details(curr_user, id):

    try:
        group = ItemGroup.query.get(id)
        if not group:
            return ResponseMessage(False, message="Invalid item group id!").resp(), 401

    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        return ResponseMessage(False, message=f"{err}").resp(), 401
    except Exception as err:
        return ResponseMessage(False, message=f"{err}").resp(), 401

    group_schema = ItemGroupSchema()
    result = group_schema.dump(group)
    return ResponseMessage(True, data=result).resp()


# Update Item Group
@master_data.route('/api/item/item_grp/update/<int:id>', methods=['PUT'])
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

    data = request.get_json()

    if ItemGroup.query.filter_by(code=data['code']).first():
        return ResponseMessage(False, message="Item group code already exist").resp()
    if data['code']:
        group.code = data['code']
    if data['description']:
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
        return ResponseMessage(False, message=f"{err}").resp(), 401
    except Exception as err:
        db.session.rollback()
        return ResponseMessage(False, message=f"{err}").resp(), 401
    except:
        db.session.rollback()
        return ResponseMessage(False, message="Unable to update!").resp(), 401
    finally:
        db.session.close()


# Delete Item Group
@master_data.route('/api/item/item_grp/delete/<int:id>', methods=['DELETE'])
@token_required
def delete_itemgrp(curr_user, id):
    if not curr_user.is_admin():
        return ResponseMessage(False, message="You're not authorized!")

    try:
        group = ItemGroup.query.get(id)
        if not group:
            return ResponseMessage(False, message="Invalid item group id!").resp(), 401
        db.session.delete(group)
        db.session.commit()
        group_schema = ItemGroupSchema()
        result = group_schema.dump(group)
        return ResponseMessage(True, message="Successfully deleted!", data=result).resp()
    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        db.session.rollback()
        return ResponseMessage(False, message=f"{err}").resp(), 401
    except Exception as err:
        db.session.rollback()
        return ResponseMessage(False, message=f"{err}").resp(), 401
    except:
        db.session.rollback()
        return ResponseMessage(False, message="Invalid item group id!").resp(), 401
    finally:
        db.session.close()


# Create UoM
@master_data.route('/api/item/uom/create', methods=['POST'])
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


@master_data.route('/api/item/uom/getall')
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


# Get UoM Details
@master_data.route('/api/item/uom/details/<int:id>')
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


# Update UoM
@master_data.route('/api/item/uom/update/<int:id>', methods=['PUT'])
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


# Delete UoM
@master_data.route('/api/item/uom/delete/<int:id>', methods=['DELETE'])
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
