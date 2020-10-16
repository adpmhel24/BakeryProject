import json
from datetime import datetime
from functools import wraps
from flask import (Blueprint, request, jsonify, abort, 
                flash, redirect, url_for, render_template, json)
from flask_login import current_user, login_user
from sqlalchemy import exc
from bakery_app.users.models import User, UserSchema
from bakery_app.branches.models import Branch, Warehouses
from bakery_app import auth, db, bcrypt
from bakery_app._utils import Check, status_response, ResponseMessage


users = Blueprint('users', __name__)

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_user.is_authenticated:
            # allow user through
            curr_user = User.query.filter_by(id=current_user.id).first()
            return f(curr_user, *args, **kwargs)
        try:
            auth_header = request.headers['Authorization'] # grab the auth header
        except:
            return jsonify({"success":False, 'message': 'Authorization is invalid'}), 401
        token = None
        if auth_header:
            token = auth_header.split(" ")[1]
        if not token:
            return jsonify({"success":False, 'message': 'Token is missing'}), 401
        
        try:
            user = User.verify_auth_token(token)
            curr_user = User.query.filter_by(id=user.id).first()
        except:
            return jsonify({"success":False, 'message': 'Token is invalid'}), 401
        return f(curr_user, *args, **kwargs)
    return decorated

# Create New User 
@users.route('/api/user/create', methods = ['POST'])
@token_required
def new_user(curr_user):
    if not curr_user.is_admin():
        return jsonify({'success': 'false', 'message': 'Your Not Admin!'})

    data = request.get_json()
    
    if data['username'] is None or data['password'] is None \
        or data['fullname'] is None or not data['whse']:
        response = ResponseMessage(False, message="Missing required fields!")
        return response.resp()

    if User.query.filter_by(username = data['username']).first() is not None:
        response = ResponseMessage(False, message="User is already exist!")
        return response.resp()
    if not Warehouses.query.filter_by(whsecode=data['whse']).first():
        raise Exception("Invalide warehouse!")
    
    try:
        user = User(**data)
        user.hash_password(data['password'])
        db.session.add(user)
        db.session.commit()
        user_schema = UserSchema()
        return user_schema.jsonify(user)
    except ValueError as err:
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

@users.route('/api/get_token')
def get_auth_token():

    data = request.get_json()
    username = data['username']
    password = data['password']
    user = User.query.filter_by(username=username).first()
    if user:
        if user.verify_password(password):
            token = user.generate_auth_token()
            user_schema = UserSchema(exclude=("password", "date_created"))
            result = user_schema.dump(user)
            response = ResponseMessage(True, token=token, data=result)
            return response.resp()
        else:
            response = ResponseMessage(False, message='Invalid password!')
            return response.resp()
    else:
        response = ResponseMessage(False, message='Invalid username')
        return response.resp()

@auth.verify_token
def verify_token(token):
    user = User.verify_auth_token(token)
    if user:
        return user
    return False

# Get All User
@users.route('/api/user/get_all_users', methods=['GET'])
@token_required
def get_all_users(curr_user):
    if not curr_user.is_admin():
        return jsonify({'success': 'false', 'message': "You're not authorized"})
    q =  request.args.get('q')

    data = []
    if q:
        user = User.query.filter(User.username.contains(q) | User.fullname.contains(q)).order_by(User.fullname.asc()).all()
    else:
        user = User.query.all()

    user_schema = UserSchema(many=True)
    result = user_schema.dump(user)
    response = ResponseMessage(True, data=result)
    return response.resp() 

# Get Specific User
@users.route('/api/user/get_user/<int:id>')
@token_required
def get_user(curr_user, id):
    user = curr_user
    if not user.is_admin():
        response = ResponseMessage(False, message="Unauthorized user!")
        return response.resp()
    
    try:
        u = User.query.get(id)
    except exc.IntegrityError:
        response = ResponseMessage(False, message="User could not be found!")
        return response.resp()
    if not u:
        response = ResponseMessage(False, message="User could not be found")
        return response.resp()

    user_schema = UserSchema()
    result = user_schema.dump(u)
    response = ResponseMessage(True, data=result)
    return response.resp() 


# Update User
@users.route('/api/user/update/<int:id>', methods=['PUT'])
@token_required
def update_user(curr_user, id):
    user = curr_user
    data = request.get_json()
    
    if not curr_user.is_admin():
        response = ResponseMessage(False, message="Unauthorized user!")
        return response.resp()
    try:
        u = User.query.get(id)
    except exc.IntegrityError:
        response = ResponseMessage(False, message="User could not be found")
        return response.resp()
    if not u:
        response = ResponseMessage(False, message="Invalid user id!")
        return response.resp()
    
    if data['username']:
        u.username = data['username']
        
    if data['fullname']:
        u.fullname = data['fullname']

    if data['password']:
        u.hash_password(data['password'])

    branch = data['branch']
    whse = data['whse']
    admin = data['admin']
    sales = data['sales']
    cashier = data['cashier']
    manager = data['manager']
    own_stock = data['own_stock']
    transfer = data['transfer']
    receive = data['receive']
    void = data['void']

    try:
        if branch:
            if not Branch.query.filter_by(code=branch).first():
                raise Exception("Invalid branch code!")
            u.branch = branch
        if whse:
            if not Warehouses.query.filter_by(whsecode=whse).first():
                raise Exception("Invalide warehouse code!")
            else:
                u.whse = whse
        if admin:
            u.admin = admin
        if sales:
            u.sales = sales
        if cashier:
            u.cashier = cashier
        if manager:
            u.manager = manager
        if own_stock:
            u.own_stock = own_stock
        if transfer:
            u.transfer = transfer
        if receive:
            u.receive = receive
        if void:
            u.void = void
    
        db.session.commit()
        user_schema = UserSchema(exclude=("password", "date_created",))
        result = user_schema.dump(u)
        response = ResponseMessage(True, message="User data successfully updated!", data=result)
        return response.resp()
    except TypeError as e:
        db.session.rollback()
        response = ResponseMessage(False, message=f"{e}")
        return response.resp()
    except exc.ProgrammingError as e:
        db.session.rollback()
        response = ResponseMessage(False, message=f"{e}")
        return response.resp()
    except Exception as e:
        db.session.rollback()
        response = ResponseMessage(False, message=f"{e}")
        return response.resp()
    finally:
        db.session.close()

    
# Change Password    
@users.route('/api/user/change_pass', methods=['PUT'])
@token_required
def change_pass(curr_user):
    user = curr_user

    u = User.query.filter_by(id=curr_user.id).first()
    if not request.args.get('password'):
        response = ResponseMessage(False, message="Missing required field!")
        return response.resp()

    u.hash_password(request.args.get('password'))
    try:
        db.session.commit()
    except TypeError as e:
        db.session.rollback()
        response = ResponseMessage(False, message=e)
        return response.resp()
    except exc.ProgrammingError as e:
        db.session.rollback()
        response = ResponseMessage(False, message=e)
        return response.resp()
    except Exception as e:
        db.session.rollback()
        response = ResponseMessage(False, message=e)
        return response.resp()
    finally:
        db.session.close() 
    
    user_schema = UserSchema()
    result = user_schema.dump(u)
    response = ResponseMessage(True, message="Password successfully updated!", data=result)
    return response.resp()

# Delete User
@users.route('/api/user/delete/<int:id>', methods=['DELETE'])
@token_required
def delete_branch(curr_user, id):
    user = curr_user
    if not user.is_admin():
        response = ResponseMessage(False, message="You're not authorized!")
        return response.resp()
    
    u = User.query.get(id)

    if not u:
        response = ResponseMessage(False, message="Invalid user id!")
        return response.resp()
    
    try:
        db.session.delete(u)
    except TypeError as e:
        db.session.rollback()
        db.session.close()
        response = ResponseMessage(False, message=e)
        return response.resp()
    except exc.ProgrammingError as e:
        db.session.rollback()
        db.session.close()
        response = ResponseMessage(False, message=e)
        return response.resp()
    except exc.IntegrityError as e:
        db.session.rollback()
        db.session.close()
        response = ResponseMessage(False, message=e)
        return response.resp()
    except:
        db.session.rollback()
        db.session.close()
        response = ResponseMessage(False, message="Unable to delete!")
        return response.resp()

    db.session.commit()
    user_schema = UserSchema()
    result = user_schema.dump(u)
    response = ResponseMessage(True, message=f"Successfully deleted!", data=result)
    return response.resp()