import json
import pyodbc
from sqlalchemy import exc
from datetime import datetime, date
from flask import Blueprint, request, jsonify, json
from flask_login import current_user
from bakery_app import db, auth
from bakery_app.users.routes import token_required
from bakery_app._utils import Check, ResponseMessage

sapb1 = Blueprint('sapb1', __name__)


# Get All IT
@sapb1.route('/api/sapb1/getit')
@token_required
def get_all_it(curr_user):
    docnum = request.args.get('docnum')
    whse = f"'{curr_user.whse}'"
    try:
        if docnum:
            transfer = db.engine.execute(
                "SELECT* FROM vSAP_IT_Header a1 WHERE a1.whsCode = {} and a1.DocNum = {}".format(whse, docnum))
        else:
            transfer = db.engine.execute("SELECT* FROM vSAP_IT_Header a1 WHERE a1.whsCode = {}".format(whse))

        result = [dict(row) for row in transfer]
        return ResponseMessage(True, data=result).resp()
    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        return ResponseMessage(True, message=f"{err}").resp(), 500
    except Exception as err:
        return ResponseMessage(True, message=f"{err}").resp(), 500


# Get SAP IT Details
@sapb1.route('/api/sapb1/itdetails/<docentry>')
@token_required
def get_it_details(curr_user, docentry):
    try:
        transfer = db.engine.execute("SELECT* FROM vSAP_IT_Rows a1 WHERE a1.DocEntry = {}".format(docentry))
        result = [dict(row) for row in transfer]
        return ResponseMessage(True, data=result).resp()
    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        return ResponseMessage(True, message=f"{err}").resp(), 500
    except Exception as err:
        return ResponseMessage(True, message=f"{err}").resp(), 500


# Get SAP PO
@sapb1.route('/api/sapb1/getpo')
@token_required
def get_all_po(curr_user):
    docnum = request.args.get('docnum')
    whse = f"'{curr_user.whse}'"
    try:
        if docnum:
            transfer = db.engine.execute(
                "SELECT* FROM vSAP_PO_Header a1 WHERE a1.whsCode = {} and a1.DocNum = {}".format(whse, docnum))
        else:
            transfer = db.engine.execute("SELECT* FROM vSAP_PO_Header a1 WHERE a1.whsCode = {}".format(whse))

        result = [dict(row) for row in transfer]
        return ResponseMessage(True, data=result).resp()
    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        return ResponseMessage(True, message=f"{err}").resp()
    except Exception as err:
        return ResponseMessage(True, message=f"{err}").resp()


# Get SAP PO Details
@sapb1.route('/api/sapb1/podetails/<docentry>')
@token_required
def get_po_details(curr_user, docentry):
    try:
        transfer = db.engine.execute("SELECT* FROM vSAP_PO_Rows a1 WHERE a1.DocEntry = {}".format(docentry))
        result = [dict(row) for row in transfer]
        return ResponseMessage(True, data=result).resp()
    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        return ResponseMessage(True, message=f"{err}").resp()
    except Exception as err:
        return ResponseMessage(True, message=f"{err}").resp()
