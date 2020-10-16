import json
from datetime import datetime
from flask import Blueprint, request, jsonify, json
from flask_login import current_user, login_required
import pyodbc
from sqlalchemy.exc import ProgrammingError, IntegrityError, DataError
from bakery_app import db, auth
from bakery_app.branches.models import (Warehouses, Branch, ObjectType, 
                                Series, BranchSchema, WarehouseSchema, 
                                SeriesSchema, ObjectTypeSchema)
from bakery_app._utils import Check, status_response, ResponseMessage
from bakery_app.users.routes import token_required


branches = Blueprint('branches', __name__)

# Create New Warehouse
@branches.route('/api/warehouse/new', methods=['POST'])
@token_required
def new_warehouse(curr_user):
    user = curr_user

    if not user.is_admin():
        response = ResponseMessage(False, message="You're not authorized!")
        return response.resp()

    whsecode = request.args.get('whsecode')
    whsename = request.args.get('whsename')
    branch = request.args.get('branch')

    if not whsecode or not whsename or not branch:
        response = ResponseMessage(False, message="Missing required field!")
        return response.resp()

    data = {'whsecode': whsecode}
    check = Check(**data)
    
    if check.whsecode_exist():
        response = ResponseMessage(False, message="Warehouse code is already exists!")
        return response.resp()
    whse = Warehouses(whsecode=whsecode, whsename=whsename, branch=branch)
    whse.created_by=user.id
    whse.updated_by=user.id
    
    try:
        db.session.add(whse)
        db.session.commit()
        whse_schema = WarehouseSchema(only=("id", "whsecode", "whsename", "branch"))
        result = whse_schema.dump(whse)
        response = ResponseMessage(True, message="Successfully added!", data=result)
        return response.resp()

    except:
        db.session.rollback()
        response = ResponseMessage(False, message="Unable to add!")
        return response.resp()
    finally:
        db.session.close()

    
# Get All Warehouse
@branches.route('/api/whse/getall')
@token_required
def get_all_whse(curr_user):

    q = request.args.get('q')
    
    if q:
        whses = Warehouses.query.filter(Warehouses.whsecode.contains(q) | \
                    Warehouses.whsename.contains(q)).all()       
    else:
        whses = Warehouses.query.all()
    whse_schema = WarehouseSchema(many=True)
    result = whse_schema.dump(whses)
    response = ResponseMessage(False, data=result)
    return response.resp()

# Get Specific Warehouse
@branches.route('/api/whse/getwhse/<int:id>')
@token_required
def get_whse(curr_user, id):

    try:
        whse = Warehouses.query.get(id)
    except IntegrityError as err:
        response = ResponseMessage(False, message=err)
        return response.resp()
    
    if not whse:
        response = ResponseMessage(False, message="No warehouse found")
        return response.resp()

    whse_schema = WarehouseSchema()
    result = whse_schema.dump(whse)
    response = ResponseMessage(True, data=result)
    return response.resp()

# Update Warehouse
@branches.route('/api/whse/update/<int:id>', methods=['PUT'])
@token_required
def update_whse(curr_user, id):
    user = curr_user
    if not user.is_admin():
        response = ResponseMessage(False, message="You're not authorized!")
        return response.resp()

    whsecode = request.args.get('whsecode')
    whsename = request.args.get('whsename')
    sales = request.args.get('sales')

    try:
        whse = Warehouses.query.get(id)
        if not whse:
            response = ResponseMessage(False, message="Invalid warehouse id!")
            return response.resp()
    
        if whsecode:
            whse.whsecode = whsecode
        
        if whsename:
            whse.whsename = whsename
        
        if sales:
            try:
                whse.sales = bool(int(sales))
            except ValueError:
                return ResponseMessage(False, message="Invalid sales value, must be integer!").resp()

        whse.updated_by = curr_user.id
        whse.date_updated = datetime.now()
        db.session.commit()
        whse_schema = WarehouseSchema()
        result = whse_schema.dump(whse)
        response = ResponseMessage(True, message="Successfully updated!", data=result)
        return response.resp()
    except IntegrityError as e:
        db.session.rollback()
        response = ResponseMessage(False, message=f"{e}")
        return response.resp()         
    except TypeError as e:
        db.session.rollback()
        response = ResponseMessage(False, message=f"{e}")
        return response.resp()
    except ProgrammingError as e:
        db.session.rollback()
        response = ResponseMessage(False, message=f"{e}")
        return response.resp()
    except Exception as e:
        db.session.rollback()
        response = ResponseMessage(False, message=f"{e}")
        return response.resp()
    except:
        db.session.rollback()
        response = ResponseMessage(False, message="Unable to update!")
        return response.resp()
    finally:
        db.session.close()

# Delete Warehouse
@branches.route('/api/whse/delete/<int:id>', methods=['DELETE'])
@token_required
def delete_whse(curr_user, id):
    user = curr_user
    if not user.is_admin():
        response = ResponseMessage(False, message="You're not authorized!")
        return response.resp()

    try:
        whse = Warehouses.query.get(id)
    except IntegrityError as err:
        response = ResponseMessage(False, message=err)
        return response.resp()

    if not whse:
        response = ResponseMessage(False, message="Invalid warehouse id!")
        return response.resp()

    try:
        db.session.delete(whse)
    except:
        response = ResponseMessage(False, message="Unable to delete!")
        return response.resp() 

    db.session.commit()
    whse_schema = WarehouseSchema()
    result = whse_schema.dump(whse)
    response = ResponseMessage(True, message="Successfully deleted!", \
            data=result)
    return response.resp() 
    
@branches.route('/api/branch/new', methods=['POST'])
@token_required
def new_branch(curr_user):
    user = curr_user
    if not curr_user.is_admin():
        response = ResponseMessage(False, message="You're not authorized!")
        return response.resp()

    code = request.args.get('code')
    name = request.args.get('name')
    if not code or not name:
        response = ResponseMessage(False, message="Missing required argument!")
        return response.resp()

    data = {'code': code }  
    check = Check(**data)
    
    # check if Branch is exists
    if check.branch_exist():
        response = ResponseMessage(False, message="Branch code already exists!")
        return response.resp()
    
    try:
        branch = Branch(code=code, name=name, created_by=user.id, updated_by=user.id)
        db.session.add(branch)
        db.session.commit()
    except Exception as err:
        db.session.rollback()
        response = ResponseMessage(False, message=f"{err}")
        return response.resp()
    except IntegrityError as err:
        db.session.rollback()
        response = ResponseMessage(False, message=f"{err}")
        return response.resp()
    except:
        db.session.rollback()
        response = ResponseMessage(False, message="Unkown error!")
        return response.resp()
    finally:
        db.session.close()

    branch_schema = BranchSchema()
    result = branch_schema.dump(branch)
    response = ResponseMessage(True, message="Successfully added!", data=result)
    return response.resp()

# Get All Branch
@branches.route('/api/branch/getall')
@token_required
def get_all_branch(curr_user):
    
    q = request.args.get('q')

    if q:
        branch = Branch.query.filter(Branch.code.contains(q) | \
                    Branch.name.contains(q)).all()       
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
@branches.route('/api/branch/getbranch/<int:id>')
@token_required
def get_branch(curr_user, id):
    
    try:
        branch = Branch.query.get(id)
    except IntegrityError as err:
        response = ResponseMessage(False, message=f"{err}")
        return response.resp()
    except DataError as err:
        response = ResponseMessage(False, message=f"{err}")
        return response.resp()

    if not branch:
        response = ResponseMessage(False, message="Invalid branch id!")
        return response.resp()
    
    branch_schema = BranchSchema()
    result = branch_schema.dump(branch)
    response = ResponseMessage(True, data=result)
    return response.resp()

# Update Branch
@branches.route('/api/branch/update/<int:id>', methods=['PUT'])
@token_required
def update_branch(curr_user, id):
    user = curr_user
    if not user.is_admin():
        response = ResponseMessage(False, message="You're not authorized!")
        return response.resp()

    branch = Branch.query.get(id)
    
    if not branch:
        response = ResponseMessage(False, message="Invalid branch id!")
        return response.resp()
    
    if request.args.get('code'):
        branch.code = request.args.get('code')
    
    if request.args.get('name'):
        branch.name = request.args.get('name')
    
    branch.updated_by = user.id
    branch.date_updated = datetime.now
    
    try:
        db.session.commit()
    except Exception as err:
        db.session.rollback()
        response = ResponseMessage(False, message=f"{err}")
        return response.resp()
    except:
        db.session.rollback()
        response = ResponseMessage(False, message="Unable to update!")
        return response.resp()
    finally:
        db.session.close()
    
    branch_schema = BranchSchema()
    result = branch_schema.dump(branch)
    response = ResponseMessage(True, message=f"Successfully updated!", data=result)
    return response.resp()

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
    user = curr_user

    if not user.is_admin():
        return jsonify({"success": False, "message": "You're not authorized!"})
    data = request.get_json()
    code = data['code']
    objtype = data['objtype']
    description = data['description']
    table = data['table']
    

    if not objtype or not description or not table or not code:
        response = ResponseMessage(False, message=f"Missing required fields!")
        return response.resp()
    
    if ObjectType.query.filter_by(code=code, objtype=objtype).first():
        return ResponseMessage(False, message="Already exists!")

    try:
        obj = ObjectType(objtype=objtype, description=description, table=table, code=code)
        obj.created_by = user.id
        obj.updated_by = user.id
        db.session.add(obj)
        db.session.commit()
        obj_schema = ObjectTypeSchema()
        result = obj_schema.dump(objtype)
        return ResponseMessage(True, message="Successfully added!", data=result).resp()
    except (pyodbc.IntegrityError, IntegrityError) as err:
        db.session.rollback()
        return ResponseMessage(False, message=f"{err}").resp()
    except Exception as err:
        db.session.rollback()
        return ResponseMessage(False, message=f"{err}").resp()
    except: 
        db.session.rollback()
        return ResponseMessage(False, message="Unable to create new Object Type!").resp()
    finally:
        db.session.close() 
   
# Get All Objtype
@branches.route('/api/objtype/getall')
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
@branches.route('/api/objtype/getdetails/<int:id>')
@token_required
def get_objtype(curr_user, id):

    try:
        obj = ObjectType.query.get(id)
    except:
        response = ResponseMessage(False, message=f"Invalid object type id!")
        return response.resp()
    if not obj:
        response = ResponseMessage(False, message=f"Invalid object type id!")
        return response.resp()
    
    obj_schema = ObjectTypeSchema()
    result = obj_schema.dump(obj)
    response = ResponseMessage(True, data=result)
    return response.resp()

# Update ObjType
@branches.route('/api/objtype/update/<int:id>', methods=['PUT'])
@token_required
def update_objtype(curr_user, id):
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
            next_num=next_num, end_num=end_num, created_by=user.id, whsecode=whsecode\
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
@branches.route('/api/series/getall')
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
@branches.route('/api/series/getdetails/<int:id>')
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
@branches.route('/api/series/getseries/<int:id>', methods=['DELETE'])
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
        
    