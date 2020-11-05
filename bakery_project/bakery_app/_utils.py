from flask import jsonify
from bakery_app.branches.models import Warehouses, Branch
from bakery_app.items.models import (Items, ItemGroup, UnitOfMeasure)


class Check():

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def itemcode_exist(self):
        if Items.query.filter_by(item_code=self.item_code).first():
            return True
        return False

    def itemname_exist(self):
        if Items.query.filter_by(item_name=self.item_name).first():
            return True
        return False

    def uom_exist(self):
        if UnitOfMeasure.query.filter_by(code=self.uom).first():
            return True
        return False

    def itemgroup_exist(self):
        if ItemGroup.query.filter_by(code=self.item_group).first():
            return True
        return False

    def fromwhse_exist(self):
        if Warehouses.query.filter_by(whsecode=self.from_whse).first():
            return True
        return False

    def towhse_exist(self):
        if Warehouses.query.filter_by(whsecode=self.to_whse).first():
            return True
        return False

    def whsecode_exist(self):
        if Warehouses.query.filter_by(whsecode=self.whsecode).first():
            return True
        return False

    def branch_exist(self, code):
        if Branch.query.filter_by(code=code).first():
            return True
        return False


def status_response(status_code, item=None):
    payload = {}
    if status_code == 1:
        payload['success'] = 'true'
        payload['status'] = {}
        payload['status']['code'] = status_code
        if item:
            payload['status']['message'] = f"{item}"
        else:
            payload['status']['message'] = 'Added successfully!'
    elif status_code in [2, 3, 4]:
        payload['status'] = {}
        payload['success'] = 'false'
        payload['status']['code'] = status_code
        if item and status_code == 2:
            payload['status']['message'] = f"Invalid '{item}'/not exist!"
        elif item and status_code == 3:
            payload['status']['message'] = f"Invalid '{item}'/Already exist!"
        elif item and status_code == 4:
            payload['status']['message'] = f"{item}"
        else:
            payload['status']['message'] = f"Unknown Error"
    response = jsonify(payload)
    return response


class ResponseMessage:
    """First argument is success = True or False"""

    def __init__(self, success, message=None, data=None, token=None, count=None):
        self.success = success
        self.message = message
        self.data = data
        self.token = token
        self.count = count

    def resp(self):
        payload = {"success": self.success}
        payload["message"] = self.message
        payload["count"] = self.count
        payload["data"] = self.data
        if self.token:
            payload["token"] = self.token
        response = jsonify(payload)
        return response
