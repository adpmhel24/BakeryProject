from datetime import datetime
from flask import Blueprint, request, jsonify
import pyodbc
from sqlalchemy.exc import IntegrityError, DataError
from bakery_app import db
from bakery_app._helpers import BaseQuery
from bakery_app._utils import Check, ResponseMessage
from bakery_app.users.routes import token_required

from .branch_schema import (BranchSchema, WarehouseSchema,
                            SeriesSchema, ObjectTypeSchema)
from .models import (Warehouses, Branch, ObjectType, Series)

branches = Blueprint('branches', __name__)


# Create New Warehouse
@branches.route('/api/warehouse/new', methods=['POST'])
@token_required
def new_warehouse(curr_user):
    user = curr_user

    if not user.is_admin():
        return ResponseMessage(False, message="Unathorized user!").resp(), 401

    # list of dictionary
    data = request.get_json()
    success = []
    unsuccess = []
    try:
        for row in data:
            if not row['whsecode'] or not row['whsename'] or not row['branch']:
                raise Exception("Missing required field!")

            check = Check(**row)
            # initialize dictionary to append in success or unsuccess list
            d = {}
            id = row['whsecode']
            d[id] = []

            if check.whsecode_exist():
                raise Exception(f"Warehouse code '{row['whsecode']}' is already exists!")
            if not check.branch_exist(row['branch']):
                raise Exception(f"Branch code '{row['branch']}' doesnt exist!")

            whse = Warehouses(**row)
            whse.created_by = user.id
            whse.updated_by = user.id

            success.append(d)
            db.session.add(whse)

        db.session.commit()
        return ResponseMessage(True, data={"Successfully": success, "Unsuccessful ": unsuccess}).resp()
    except (pyodbc.IntegrityError, IntegrityError) as err:
        db.session.rollback()
        return ResponseMessage(False, message=f"{err}").resp(), 500
    except Exception as err:
        db.session.rollback()
        return ResponseMessage(False, message=f"{err}").resp(), 500
    finally:
        db.session.close()


# Get All Warehouse
@branches.route('/api/whse/get_all')
@token_required
def get_all_whse(curr_user):
    try:
        branch = request.args.get('branch')
        filt = []
        if branch:
            filt.append(('branch', '==', branch))

        branch_filter = BaseQuery.create_query_filter(Warehouses, filters={'and_': filt})
        warehouses = db.session.query(Warehouses).filter(*branch_filter).all()
        whse_schema = WarehouseSchema(many=True, only=("id", "whsecode", "whsename", "branch",))
        result = whse_schema.dump(warehouses)
        return ResponseMessage(True, data=result).resp()
    except (pyodbc.IntegrityError, IntegrityError) as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500
    except Exception as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500


# Get Specific Warehouse
@branches.route('/api/whse/details/<int:id>')
@token_required
def get_whse(curr_user, id):
    try:
        whse = Warehouses.query.get(id)
        whse_schema = WarehouseSchema()
        result = whse_schema.dump(whse)
        return ResponseMessage(True, data=result).resp()

    except (pyodbc.IntegrityError, IntegrityError) as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500
    except Exception as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500


# Update Warehouse
@branches.route('/api/whse/update/<int:id>', methods=['PUT'])
@token_required
def update_whse(curr_user, id):
    if not curr_user.is_admin():
        return ResponseMessage(False, message="Unauthorized user!").resp(), 401

    data = request.get_json()
    whsecode = data['whsecode']
    whsename = data['whsename']

    try:
        whse = Warehouses.query.get(id)
        if not whse:
            return ResponseMessage(False, message="Invalid warehouse id!").resp(), 401

        if whsecode:
            whse.whsecode = whsecode

        if whsename:
            whse.whsename = whsename

        whse.updated_by = curr_user.id
        whse.date_updated = datetime.now()

        db.session.commit()

        whse_schema = WarehouseSchema()
        result = whse_schema.dump(whse)

        return ResponseMessage(True, message="Successfully updated!", data=result).resp()
    except (pyodbc.IntegrityError, IntegrityError) as err:
        db.session.rollback()
        return ResponseMessage(False, message=f"{err}").resp(), 500
    except Exception as err:
        db.session.rollback()
        return ResponseMessage(False, message=f"{err}").resp(), 500
    finally:
        db.session.close()


# Delete Warehouse
@branches.route('/api/whse/delete/<int:id>', methods=['DELETE'])
@token_required
def delete_whse(curr_user, id):
    if not curr_user.is_admin():
        return ResponseMessage(False, message="Unauthorized user!").resp(), 401

    try:
        whse = Warehouses.query.get(id)
        db.session.delete(whse)
        db.session.commit()
        whse_schema = WarehouseSchema()
        result = whse_schema.dump(whse)
        return ResponseMessage(True, message="Successfully deleted!", data=result).resp()
    except (pyodbc.IntegrityError, IntegrityError) as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500
    except Exception as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500


# Get Branch Warehouse
@branches.route('/api/branch/whse/all')
@token_required
def get_branch_whse(curr_user):
    branch = request.args.get('branch')
    try:
        whse = db.session.query(Warehouses). \
            filter(Warehouses.branch == branch).all()

        whse_schema = WarehouseSchema(many=True, include=("whsecode", "whsename", "branch"))
        result = whse_schema.dump(whse)
        return ResponseMessage(True, data=result).resp()
    except (pyodbc.IntegrityError, IntegrityError) as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500
    except Exception as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500


# Create New Branch
@branches.route('/api/branch/new', methods=['POST'])
@token_required
def new_branch(curr_user):
    if not curr_user.is_admin():
        return ResponseMessage(False, message="Unauthorized user!").resp(), 401

    data = request.get_json()
    data['created_by'] = curr_user.id
    data['updated_by'] = curr_user.id
    if not data['code'] or not data['name']:
        return ResponseMessage(False, message="Missing required argument!").resp(), 401

    check = Check(**data)

    # check if Branch is exists
    if check.branch_exist(data['code']):
        return ResponseMessage(False, message="Branch code already exists!").resp(), 401

    try:
        branch = Branch(**data)
        db.session.add(branch)
        db.session.commit()
        branch_schema = BranchSchema()
        result = branch_schema.dump(branch)
        return ResponseMessage(True, message="Successfully added!", data=result).resp()
    except (pyodbc.IntegrityError, IntegrityError) as err:
        db.session.rollback()
        return ResponseMessage(False, message=f"{err}").resp(), 500
    except Exception as err:
        db.session.rollback()
        return ResponseMessage(False, message=f"{err}").resp(), 500
    finally:
        db.session.close()


# Get All Branch
@branches.route('/api/branch/get_all')
@token_required
def get_all_branch(curr_user):
    q = request.args.get('q')

    if q:
        branch = Branch.query.filter(Branch.code.contains(q) | Branch.name.contains(q)).all()
    else:
        branch = Branch.query.all()

    if not branch:
        response = ResponseMessage(False, message="Invalid search keyword!")
        return response.resp()

    branch_schema = BranchSchema(many=True)
    result = branch_schema.dump(branch)
    response = ResponseMessage(True, data=result)
    return response.resp()


# Get Specific Branch
@branches.route('/api/branch/details/<int:id>')
@token_required
def get_branch(curr_user, id):
    try:
        branch = Branch.query.get(id)
        if not branch:
            return ResponseMessage(False, message="Invalid branch id!").resp(), 401
        branch_schema = BranchSchema()
        result = branch_schema.dump(branch)
        response = ResponseMessage(True, data=result)
        return response.resp()
    except IntegrityError as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500
    except DataError as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500


# Update Branch
@branches.route('/api/branch/update/<int:id>', methods=['PUT'])
@token_required
def update_branch(curr_user, id):
    if not curr_user.is_admin():
        return ResponseMessage(False, message="You're not authorized!").resp(), 401

    branch = Branch.query.get(id)

    if not branch:
        return ResponseMessage(False, message="Invalid branch id!").resp(), 401

    if request.args.get('code'):
        branch.code = request.args.get('code')

    if request.args.get('name'):
        branch.name = request.args.get('name')

    branch.updated_by = curr_user.id
    branch.date_updated = datetime.now

    try:
        db.session.commit()
        branch_schema = BranchSchema()
        result = branch_schema.dump(branch)
        return ResponseMessage(True, message=f"Successfully updated!", data=result).resp()
    except (pyodbc.IntegrityError, IntegrityError) as err:
        db.session.rollback()
        return ResponseMessage(False, message=f"{err}").resp(), 500
    except Exception as err:
        db.session.rollback()
        return ResponseMessage(False, message=f"{err}").resp(), 500
    finally:
        db.session.close()


# Delete Branch
@branches.route('/api/branch/delete/<int:id>', methods=['DELETE'])
@token_required
def delete_branch(curr_user, id):
    user = curr_user
    if not user.is_admin():
        response = ResponseMessage(False, message="You're not authorized!")
        return response.resp()

    branch = Branch.query.get(id)

    if not branch:
        response = ResponseMessage(False, message="Invalid branch id!")
        return response.resp()

    try:
        db.session.delete(branch)
        db.session.commit()
    except Exception as err:
        db.session.rollback()
        response = ResponseMessage(False, message=f"{err}")
        return response.resp()
    except:
        db.session.rollback()
        response = ResponseMessage(False, message="Unable to delete!")
        return response.resp()
    finally:
        db.session.close()

    branch_schema = BranchSchema()
    result = branch_schema.dump(branch)
    response = ResponseMessage(True, message=f"Successfully deleted!", data=result)
    return response.resp()


# Create New ObjType
@branches.route('/api/objtype/new', methods=['POST'])
@token_required
def new_objtype(curr_user):
    if not curr_user.is_admin():
        return ResponseMessage(False, message="Unauthorized user!").resp(), 401
    data = request.get_json()
    code = data['code']
    objtype = data['objtype']
    description = data['description']
    table = data['table']

    if not objtype or not description or not table or not code:
        return ResponseMessage(False, message=f"Missing required fields!").resp(), 401

    if ObjectType.query.filter_by(code=code, objtype=objtype).first():
        return ResponseMessage(False, message="Already exists!").resp(), 401

    try:
        obj = ObjectType(objtype=objtype, description=description, table=table, code=code)
        obj.created_by = curr_user.id
        obj.updated_by = curr_user.id
        db.session.add(obj)
        db.session.commit()
        obj_schema = ObjectTypeSchema()
        result = obj_schema.dump(obj)
        return ResponseMessage(True, message="Successfully added!", data=result).resp()
    except (pyodbc.IntegrityError, IntegrityError) as err:
        db.session.rollback()
        return ResponseMessage(False, message=f"{err}").resp(), 500
    except Exception as err:
        db.session.rollback()
        return ResponseMessage(False, message=f"{err}").resp(), 500
    finally:
        db.session.close()


# Get All Objtype
@branches.route('/api/objtype/get_all')
@token_required
def get_all_objtype(curr_user):
    q = request.args.get('q')

    if q:
        obj = ObjectType.query.filter_by(ObjectType.objtype.contains(q) | ObjectType.description.contains(q) \
                                         | ObjectType.table.contains(q)).all()
    else:
        obj = ObjectType.query.all()

    obj_schema = ObjectTypeSchema(many=True, only=("id", "objtype", "description", "table"))
    result = obj_schema.dump(obj)
    response = ResponseMessage(True, data=result)
    return response.resp()


# Get Specific ObjType
@branches.route('/api/objtype/details/<int:id>')
@token_required
def get_objtype(curr_user, id):
    try:
        obj = ObjectType.query.get(id)
        if not obj:
            return ResponseMessage(False, message=f"Invalid object type id!").resp(), 401
        obj_schema = ObjectTypeSchema()
        result = obj_schema.dump(obj)
        return ResponseMessage(True, data=result).resp()
    except Exception as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500


# Update ObjType
@branches.route('/api/objtype/update/<int:id>', methods=['PUT'])
@token_required
def update_objtype(curr_user, id):
    if not curr_user.is_admin():
        return ResponseMessage(False, message="You're not authorized!").resp(), 401

    try:
        obj = ObjectType.query.get(id)
        if not obj:
            return ResponseMessage(False, message=f"Invalid object type id!").resp(), 401
    except Exception as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500

    objtype = request.args.get('objtype')
    description = request.args.get('description')
    table = request.args.get('table')

    if objtype:
        obj.objtype = objtype
    if description:
        obj.description = description
    if table:
        obj.table = table

    obj.updated_by = user.id
    obj.date_updated = datetime.now

    try:
        db.session.commit()
    except:
        db.session.rollback()
        response = ResponseMessage(False, message=f"Unable to update!")
        return response.resp()
    finally:
        db.session.close()

    obj_schema = ObjectTypeSchema()
    result = obj_schema.dump(obj)
    response = ResponseMessage(True, message="Successfully updated", data=result)
    return response.resp()


# Delete ObjType
@branches.route('/api/objtype/delete/<int:id>', methods=['DELETE'])
@token_required
def delete_objtype(curr_user, id):
    user = curr_user

    if not user.is_admin():
        response = ResponseMessage(False, message="You're not authorized!")
        return response.resp()

    try:
        obj = ObjectType.query.get(id)
        if not obj:
            response = ResponseMessage(False, message=f"Invalid object type id!")
            return response.resp()
    except:
        response = ResponseMessage(False, message=f"Invalid object type id!")
        return response.resp()

    try:
        db.session.delete(obj)
        db.session.commit()
        obj_schema = ObjectTypeSchema()
        result = obj_schema.dump(obj)
        response = ResponseMessage(True, message="Successfully deleted", data=result)
        return response.resp()
    except:
        db.session.rollback()
        response = ResponseMessage(False, message=f"Unable to delete!")
        return response.resp()
    finally:
        db.session.close()


# Create new Series
@branches.route('/api/series/new', methods=['POST'])
@token_required
def new_series(curr_user):
    user = curr_user
    if not user.is_admin():
        return jsonify({"success": False, "message": "You're not authorized!"})

    data = request.get_json()
    code = data['code']
    name = data['name']
    whsecode = data['whsecode']
    objtype = data['objtype']
    start_num = data['start_num']
    next_num = data['next_num']
    end_num = data['end_num']

    if not code or not name or not objtype or not start_num or not next_num \
            or not end_num or not whsecode:
        response = ResponseMessage(False, message=f"Missing required field!")
        return response.resp()

    try:
        if not Warehouses.query.filter_by(whsecode=whsecode).first():
            raise Exception("Invalid whsecode")
        if Series.query.filter_by(code=code, objtype=objtype).first():
            raise Exception("Already exist!")
        series = Series(code=code, name=name, objtype=objtype, start_num=start_num, \
                        next_num=next_num, end_num=end_num, created_by=user.id, whsecode=whsecode \
                        # ,updated_by=user.id
                        )
        db.session.add(series)
        db.session.commit()
        series_schema = SeriesSchema()
        result = series_schema.dump(series)
        return ResponseMessage(True, message="Successfully added", data=result).resp()
    except Exception as err:
        db.session.rollback()
        return ResponseMessage(False, message=f"{err}").resp()
    except (pyodbc.IntegrityError, IntegrityError) as err:
        db.session.rollback()
        return ResponseMessage(False, message=f"{err}").resp()
    except:
        db.session.rollback()
        return ResponseMessage(False, message=f"Unable to add!").resp()
    finally:
        db.session.close()


# Get All Series
@branches.route('/api/series/get_all')
@token_required
def get_all_series(curr_user):
    q = request.args.get('q')

    if q:
        series = Series.query.filter(Series.code.contains(q) | Series.name.contains(q)).all()

    else:
        series = Series.query.all()

    series_schema = SeriesSchema(many=True, only=("id", "code", "name", "objtype", \
                                                  "start_num", "next_num", "end_num"))
    result = series_schema.dump(series)
    response = ResponseMessage(True, data=result)
    return response.resp()


# Get specific series
@branches.route('/api/series/details/<int:id>')
@token_required
def get_series(curr_user, id):
    try:
        series = Series.query.get(id)
        if not series:
            response = ResponseMessage(False, message="Invalid series id!")
            return response.resp()
    except:
        response = ResponseMessage(False, message="Invalid series id!")
        return response.resp()

    series_schema = SeriesSchema()
    result = series_schema.dump(series)
    response = ResponseMessage(True, data=result)
    return response.resp()


# Update Series
@branches.route('/api/series/update/<int:id>', methods=['PUT'])
@token_required
def update_series(curr_user, id):
    user = curr_user
    if not user.is_admin():
        return jsonify({"success": False, "message": "You're not authorized!"})

    data = request.get_json()

    try:
        series = Series.query.get(id)
        if not series:
            response = ResponseMessage(False, message="Invalid series id!")
            return response.resp()
    except:
        response = ResponseMessage(False, message="Invalid series id!")
        return response.resp()

    if series.next_num != series.start_num:
        response = ResponseMessage(False, message="Unable to update series! \
            Series in already used!")
        return response.resp()

    code = data['code']
    name = data['name']
    whsecode = data['whsecode']
    objtype = data['objtype']
    start_num = data['start_num']
    next_num = data['next_num']
    end_num = data['end_num']

    if Series.query.filter_by(code=code, objtype=objtype).first():
        raise Exception("Already exist!")

    if code:
        series.code = code
    if whsecode:
        series.whsecode = whsecode
    if name:
        series.name = name
    if objtype:
        series.objtype = objtype
    if start_num:
        series.start_num = start_num
    if next_num:
        series.next_num = next_num
    if end_num:
        series.end_num = end_num

    try:
        db.session.commit()
        series_schema = SeriesSchema()
        result = series_schema.dump(series)
        response = ResponseMessage(True, data=result)
        return response.resp()
    except:
        db.session.rollback()
        response = ResponseMessage(False, message="Unable to update!")
        return response.resp()
    finally:
        db.session.close()


# Delete Series
@branches.route('/api/series/delete/<int:id>', methods=['DELETE'])
@token_required
def delete_series(curr_user, id):
    user = curr_user
    if not user.is_admin():
        return jsonify({"success": False, "message": "You're not authorized!"})

    try:
        series = Series.query.get(id)
        if not series:
            response = ResponseMessage(False, message="Invalid series id!")
            return response.resp()
    except:
        response = ResponseMessage(False, message="Invalid series id!")
        return response.resp()

    try:
        db.session.delete(series)
        db.session.commit()
        series_schema = SeriesSchema()
        result = series_schema.dump(series)
        response = ResponseMessage(True, data=result)
        return response.resp()
    except Exception as err:
        db.session.rollback()
        response = ResponseMessage(False, message=err)
        return response.resp()
    except (IntegrityError, pyodbc.IntegrityError) as err:
        db.session.rollback()
        response = ResponseMessage(False, message=err)
        return response.resp()
    except:
        db.session.rollback()
        response = ResponseMessage(False, message="Unable to delete!")
        return response.resp()
    finally:
        db.session.close()
