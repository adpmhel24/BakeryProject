from flask import Blueprint, request, jsonify
from bakery_app import db
from bakery_app.inventory.models import Items, ItemGroup, UnitOfMeasure

inventory = Blueprint('inventory', __name__)


@inventory.route('/api/inv/item/create', methods=['POST'])
def create_item():
    item_code = request.args.get('item_code')
    item_name = request.args.get('item_name')
    group = request.args.get('group')
    uom = request.args.get('uom')

    if not ItemGroup.query.filter_by(name=group).first():
        return jsonify({'success':'false', 'status':{'code':2, 'description': \
           f"Invalid group name '{group}'!"}})

    elif not UnitOfMeasure.query.filter_by(name=uom).first():
        return jsonify({'success':'false', 'status':{'code':2, 'description': \
           f"Invalid uom name '{uom}'!"}})

    elif Items.query.filter_by(item_name=item_code).first():
        return jsonify({'success':'false', 'status':{'code':2, 'description': \
            f"This item code '{item_code}' is already exists."}})

    item = Items(item_code=item_code, item_name=item_name, item_group=group, uom=uom)
    db.session.add(item)
    db.session.commit()
    return jsonify({'success':'true', 'status':{'code':1, 'description': 'Added successfully!'}})


@inventory.route('/api/inv/item_grp/create', methods=['POST'])
def create_itemgroup():
    name = request.args.get('name')
    description = request.args.get('description')

    if ItemGroup.query.filter_by(name=name).first():
        return jsonify({'success':'false', 'status':{'code':3, 'description': \
           f"This item group name is already exists."}})

    group = ItemGroup(name=name, description=description)
    db.session.add(group)
    db.session.commit()
    return jsonify({'success':'true', 'status':{'code':1, 'description': 'Added successfully'}})

@inventory.route('/api/inv/item_uom/create', methods=['POST'])
def create_uom():
    name = request.args.get('name')
    description = request.args.get('description')

    if UnitOfMeasure.query.filter_by(name=name).first():
        return jsonify({'success':'false', 'status':{'code':3, 'description': \
           f"This item group name is already exists."}})

    uom = UnitOfMeasure(name=name, description=description)
    db.session.add(uom)
    db.session.commit()
    return jsonify({'success':'true', 'status':{'code':1, 'description': 'Added successfully'}})
