import json
from datetime import datetime
import pyodbc
from functools import wraps
from flask import (Blueprint, request, jsonify)
from flask_login import current_user, login_user
from sqlalchemy import exc

from bakery_app import auth, db
from bakery_app._helpers import BaseQuery
from bakery_app.branches.models import Branch, Warehouses
from bakery_app._utils import Check, ResponseMessage

from .models import User, UserSchema

users = Blueprint('users', __name__)


# decorator to check if valid credentials
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_user.is_authenticated:
            # allow user through
            curr_user = User.query.filter_by(id=current_user.id).first()
            return f(curr_user, *args, **kwargs)
        try:
            auth_header = request.headers['Authorization']  # grab the auth header
        except:
            return jsonify({"success": False, 'message': 'Authorization is invalid'}), 401
        token = None
        if auth_header:
            token = auth_header.split(" ")[1]
        if not token:
            return jsonify({"success": False, 'message': 'Token is missing'}), 401

        try:
            user = User.verify_auth_token(token)
            curr_user = User.query.filter_by(id=user.id).first()
        except:
            return jsonify({"success": False, 'message': 'Token is invalid'}), 401
        return f(curr_user, *args, **kwargs)

    return decorated


# Create New User
@users.route('/api/auth/user/new', methods=['POST'])
@token_required
def new_user(curr_user):
    if not curr_user.is_admin():
        return ResponseMessage(False, message="Unauthorized user!").resp(), 401

    data = request.get_json()

    if data['username'] is None or data['password'] is None \
            or data['fullname'] is None or not data['whse'] or not data['whse']:
        return ResponseMessage(False, message="Missing required fields!").resp(), 401

    if User.query.filter_by(username=data['username']).first() is not None:
        return ResponseMessage(False, message="User is already exist!").resp(), 401
    if not Warehouses.query.filter_by(whsecode=data['whse']).first():
        return ResponseMessage(False, message="Invalid warehouse!").resp(), 401

    try:
        user = User(**data)
        user.hash_password(data['password'])
        db.session.add(user)
        db.session.commit()
        user_schema = UserSchema(exclude=("password",))
        result = user_schema.dump(user)
        return ResponseMessage(True, data=result).resp()
    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        db.session.rollback()
        return ResponseMessage(False, message=f"{err}").resp(), 500
    except Exception as err:
        db.session.rollback()
        return ResponseMessage(False, message=f"{err}").resp(), 500
    finally:
        db.session.close()


@users.route('/api/auth/login')
def get_auth_token():
    try:
        username = request.args.get('username')
        password = request.args.get('password')
        user = User.query.filter_by(username=username).first()
        if user:
            if user.verify_password(password):
                token = user.generate_auth_token()
                user_schema = UserSchema(exclude=("password", "date_created"))
                result = user_schema.dump(user)
                response = ResponseMessage(True, message="You logged in successfully!", token=token, data=result)
                return response.resp()
            else:
                return ResponseMessage(False, message='Invalid password!').resp(), 401
        else:
            return ResponseMessage(False, message='Invalid username').resp(), 401
    except Exception as err:
        return ResponseMessage(False, message=str(err)).resp(), 500


@auth.verify_token
def verify_token(token):
    user = User.verify_auth_token(token)
    if user:
        return user
    return False


# Get All User
@users.route('/api/auth/user/get_all')
@token_required
def get_all_users(curr_user):
    # contains to filter
    filt = []

    data = request.args.to_dict()

    for k, v in data.items():
        if k == 'search':
            filt.append(('username', 'like', f'%{v}%'))
        elif k == 'branch':
            if v:
                filt.append((k, '==', v))
        elif k == 'whse':
            if v:
                filt.append((k, '==', v))
        else:
            filt.append((k, '==', bool(int(v))))
    try:
        
        user_filter = BaseQuery.create_query_filter(User, filters={'and': filt})
        user = db.session.query(User).filter(*user_filter). \
            order_by(User.fullname.asc()).all()

        user_schema = UserSchema(many=True, only=("id", "username", "fullname",))
        result = user_schema.dump(user)
        return ResponseMessage(True, count=len(result), data=result).resp()
    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500
    except Exception as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500


# Get User Details
@users.route('/api/auth/user/details/<int:id>')
@token_required
def get_user(curr_user, id):
    user = curr_user
    if not user.is_admin() and not curr_user.is_manager():
        return ResponseMessage(False, message="Unauthorized user!").resp(), 401

    try:
        u = User.query.get(id)
        user_schema = UserSchema(exclude=("password", "date_created",))
        result = user_schema.dump(u)
        return ResponseMessage(True, data=result).resp()
    except exc.IntegrityError as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500
    except Exception as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500


# Update User
@users.route('/api/auth/user/update/<int:id>', methods=['PUT'])
@token_required
def update_user(curr_user, id):
    data = request.get_json()

    if not curr_user.is_admin():
        return ResponseMessage(False, message="Unauthorized user!").resp(), 401
    try:
        user = User.query.get(id)
        if not user:
            return ResponseMessage(False, message="Invalid user id!").resp()

        for k, v in data.items():
            if k == 'branch':
                if not Branch.query.filter_by(code=v).first():
                    raise Exception("Invalid branch code!")
            if k == 'whse':
                if not Warehouses.query.filter_by(whsecode=v).first():
                    raise Exception("Invalid warehouse code!")
            if k == 'password':
                user.hash_password(v)
            else:
                setattr(user, k, v)

        db.session.commit()
        user_schema = UserSchema(exclude=("password", "date_created",))
        result = user_schema.dump(user)
        return ResponseMessage(True, message="User data successfully updated!", data=result).resp()
    except (exc.IntegrityError, pyodbc.IntegrityError) as err:
        db.session.rollback()
        return ResponseMessage(False, message=f"{err}").resp(), 500
    except Exception as err:
        db.session.rollback()
        return ResponseMessage(False, message=f"{err}").resp(), 500
    finally:
        db.session.close()


# Change Password    
@users.route('/api/user/change_pass', methods=['PUT'])
@token_required
def change_pass(curr_user):
    user = curr_user

    data = request.get_json()
    u = User.query.filter_by(id=curr_user.id).first()
    if not data['password']:
        return ResponseMessage(False, message="Missing required field!").resp(), 401

    u.hash_password(data['password'])
    try:
        db.session.commit()
        return ResponseMessage(True, message="Password successfully updated!").resp()
    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        db.session.rollback()
        return ResponseMessage(False, message=f"{err}").resp(), 500
    except Exception as err:
        db.session.rollback()
        return ResponseMessage(False, message=f"{err}").resp(), 500
    finally:
        db.session.close()


# Delete User
@users.route('/api/user/delete/<int:id>', methods=['DELETE'])
@token_required
def delete_branch(curr_user, id):
    # Check if user is admin
    if not curr_user.is_admin():
        return ResponseMessage(False, message="Unauthorized user!").resp(), 401

    try:
        u = User.query.get(id)

        if not u:
            return ResponseMessage(False, message="Invalid user id!").resp(), 401

        db.session.delete(u)
        db.session.commit()
        user_schema = UserSchema()
        result = user_schema.dump(u)
        response = ResponseMessage(True, message=f"Successfully deleted!", data=result)
        return response.resp()
    except (exc.IntegrityError, pyodbc.IntegrityError) as err:
        db.session.rollback()
        return ResponseMessage(False, message=f"{err}").resp(), 500
    except Exception as err:
        db.session.rollback()
        return ResponseMessage(False, message=f"{err}").resp(), 500
    finally:
        db.session.close()
