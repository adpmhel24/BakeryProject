from flask import Blueprint, request, jsonify, json
from bakery_app import db
from bakery_app.inventory.models import (Items, ItemGroup, UnitOfMeasure,
        ItemPrice)

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
        return jsonify({'success':'false', 'status':{'code':3, 'description': \
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
           f"This item group name '{name}' is already exists."}})

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


@inventory.route('/api/inv/item_price/create', methods=['POST'])
def create_price():
    item_code = request.args.get('item_code')
    price = request.args.get('price')
    item = Items.query.filter_by(item_code=item_code).first()
    if not item:
        return jsonify({'success':'false', 'status':{'code':2, 'description': \
           f"Invalid item code '{item_code}'!"}})
    # elif item and ItemPrice.query.join(ItemPrice.price).filter_by(price=price).first():
    elif ItemPrice.query.filter_by(item_code=item_code, price=price).first():
        return jsonify({'success':'false', 'status':{'code':3, 'description': \
           f"Item code '{item_code}' and '{price}' is already exists!"}})
    
    price = ItemPrice(item_code=item_code, price=price)
    db.session.add(price)
    db.session.commit()
    return jsonify({'success':'true', 'status':{'code':1, 'description': 'Added successfully'}})


@inventory.route('/api/inv/get_items', methods=['GET'])
def get_items():
    # price = ItemPrice.query.filter(ItemPrice.item_code=='BUNNYSAL').all()
    items = db.session.query(Items.item_code, Items.item_name, Items.item_group, ItemPrice.price).join(ItemPrice, Items.item_code == ItemPrice.item_code)
    for i in items:
        return f'{i.item_name} {i.item_group} {i.price}'