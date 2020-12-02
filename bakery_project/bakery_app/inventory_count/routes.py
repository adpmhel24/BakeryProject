import pyodbc

from datetime import datetime
from flask import Blueprint, request
from sqlalchemy import exc, and_, cast, DATE, func, case

from bakery_app import db
from bakery_app._utils import Check, ResponseMessage
from bakery_app.customers.models import Customer
from bakery_app.sales.models import SalesHeader, SalesRow
from bakery_app.branches.models import Series, ObjectType, Warehouses
from bakery_app.users.routes import token_required
from bakery_app.items.models import PriceListRow, PriceListHeader, Items
from bakery_app.inventory.models import WhseInv
from bakery_app.inventory.inv_schema import WhseInvSchema
from bakery_app.inventory_adjustment.models import ItemAdjustmentIn, ItemAdjustmentInRow
from bakery_app.pullout.models import PullOutHeader, PullOutRow, PullOutRowRequest, PullOutHeaderRequest

from .models import (CountingInventoryHeader, CountingInventoryRow, FinalInvCount, FinalInvCountRow)
from .inv_count_schema import CountingInventoryRowSchema

inventory_count = Blueprint('inventory_count', __name__, url_prefix='/api/inv')


# Create Inventory Count
@inventory_count.route('/count/create', methods=['POST', 'GET'])
@token_required
def create_inv_count(curr_user):
    if not curr_user.is_admin() and not curr_user.is_allow_ending():
        return ResponseMessage(False, message="Unauthorized user!").resp(), 401

    whse = Warehouses.query.filter_by(whsecode=curr_user.whse).first()
    if not whse.is_cutoff():
        return ResponseMessage(False, message="Cutoff is disable").resp(), 401

    date = request.args.get('date')

    if request.method == 'GET':
        try:
            if not curr_user.is_manager():
                whse_inv_case = case([(WhseInv.quantity != 0, 1)], else_=0)
                inv = db.session.query(WhseInv.item_code,
                                       WhseInv.item_code,
                                       WhseInv.quantity,
                                       Items.uom
                                       ).filter(WhseInv.warehouse == curr_user.whse
                                                ).outerjoin(
                    Items, Items.item_code == WhseInv.item_code
                ).order_by(whse_inv_case.desc(), WhseInv.item_code
                           ).all()
                inv_schema = WhseInvSchema(many=True)
                result = inv_schema.dump(inv)
                return ResponseMessage(True, data=result).resp()
            elif curr_user.is_manager():
                count_header = CountingInventoryHeader
                count_row = CountingInventoryRow
                sales_case = case([(count_header.user_type == 'sales', count_row.actual_count)])
                auditor_case = case([(count_header.user_type == 'auditor', count_row.actual_count)])
                inv = db.session.query(
                    count_row.item_code,
                    WhseInv.quantity.label('quantity'),
                    func.sum(func.isnull(sales_case, 0)).label('sales_count'),
                    func.sum(func.isnull(auditor_case, 0)).label('auditor_count'),
                    func.sum(func.isnull(sales_case, 0) - func.isnull(auditor_case, 0)).label('variance'),
                    count_row.uom
                ).outerjoin(WhseInv,
                            and_(count_row.whsecode == WhseInv.warehouse, WhseInv.item_code == count_row.item_code)
                            ).filter(
                    and_(cast(count_header.transdate, DATE) == date,
                         count_row.whsecode == curr_user.whse,
                         count_header.id == count_row.counting_id,
                         False == count_header.confirm
                         )
                ).group_by(count_row.item_code, WhseInv.quantity, count_row.uom
                           ).having(func.sum(func.isnull(sales_case, 0) - func.isnull(auditor_case, 0)) != 0
                                    ).all()

                inv_schema = CountingInventoryRowSchema(many=True)
                result = inv_schema.dump(inv)
                return ResponseMessage(True, data=result).resp()
        except (pyodbc.IntegrityError, exc.IntegrityError) as err:
            return ResponseMessage(False, message=f"{err}").resp(), 500
        except Exception as err:
            return ResponseMessage(False, message=f"{err}").resp(), 500

    elif request.method == 'POST':
        try:
            # query the whse and check if the cutoff is true
            data = request.get_json()
            header = data['header']
            rows = data['rows']

            # add to headers
            header['created_by'] = curr_user.id
            header['updated_by'] = curr_user.id
            if curr_user.is_manager():
                header['user_type'] = 'manager'
            elif curr_user.is_auditor():
                header['user_type'] = 'auditor'
            elif curr_user.is_sales() and not curr_user.is_manager():
                header['user_type'] = 'sales'

            if CountingInventoryHeader.query.filter(
                    and_(CountingInventoryHeader.user_type == header['user_type'],
                         func.cast(CountingInventoryHeader.transdate, DATE) == header['transdate'],
                         CountingInventoryHeader.docstatus == 'C',
                         False == CountingInventoryHeader.confirm)).first():
                return ResponseMessage(False, message=f"You're already added ending inventory this day").resp(), 401

            obj = ObjectType.query.filter_by(code='ICNT').first()

            # Check if has objtype
            if not obj:
                return ResponseMessage(False, message="Object type not found!").resp(), 401

            # query the series
            series = Series.query.filter_by(whsecode=curr_user.whse, objtype=obj.objtype).first()

            # check if has series
            if not series:
                return ResponseMessage(False, message="Series not found!").resp(), 401

            # check if next num is not greater done end num
            if series.next_num + 1 > series.end_num:
                return ResponseMessage(False, message="Series number is greater than next num!").resp(), 401

            # construct reference
            reference = f"{series.code}-{obj.code}-{series.next_num}"

            # add to header
            header['series'] = series.id
            header['objtype'] = obj.objtype
            header['seriescode'] = series.code
            header['transnumber'] = series.next_num
            header['reference'] = reference

            # add 1 to next series
            series.next_num += 1

            inv_count_header = CountingInventoryHeader(**header)
            db.session.add_all([series, inv_count_header])
            db.session.flush()

            for row in rows:
                row['whsecode'] = curr_user.whse
                check = Check(**row)
                # check if valid
                if not check.itemcode_exist():
                    raise Exception("Invalid item code!")

                inv_count_row = CountingInventoryRow(counting_id=inv_count_header.id, **row)
                inv_count_row.objtype = inv_count_header.objtype
                inv_count_row.created_by = inv_count_header.created_by
                inv_count_row.updated_by = inv_count_header.updated_by

                db.session.add(inv_count_row)

            db.session.commit()

            return ResponseMessage(True, message="Successfully added!").resp()

        except (pyodbc.IntegrityError, exc.IntegrityError) as err:
            db.session.rollback()
            return ResponseMessage(False, message=f"{err}").resp(), 500
        except Exception as err:
            db.session.rollback()
            return ResponseMessage(False, message=f"{err}").resp(), 500
        finally:
            db.session.close()


# Confirm Actual Ending
@inventory_count.route('/count/confirm', methods=['GET', 'PUT'])
@token_required
def inv_count_confirm(curr_user):
    if (not curr_user.is_manager() or not curr_user.is_admin()) and not curr_user.is_allow_ending():
        return ResponseMessage(False, message="Unauthorized user!").resp(), 401

    date = request.args.get('transdate')

    # create an instance
    count_header = CountingInventoryHeader
    count_row = CountingInventoryRow
    po_req_header = PullOutHeaderRequest
    po_req_row = PullOutRowRequest

    final_count = """
        DECLARE @date varchar(20)
        DECLARE @whse varchar(30)
        
        SET @date = '{}' 
        SET @whse = '{}'

        SELECT
        y.item_code, y.quantity, 
        y.ending_sales_count, y.ending_auditor_count, y.ending_manager_count, y.ending_final_count,
        y.po_sales_count, y.po_auditor_count, y.po_manager_count, y.po_final_count,
        CASE WHEN y.variance != 0 THEN y.variance * -1 ELSE 0 END variance,
        y.sales_user, y.auditor_user, y.manager_user, y.uom
        FROM( SELECT x.item_code, x.quantity , x.ending_sales_count, 
        x.ending_auditor_count, x.ending_manager_count, 
        CASE WHEN x.ending_manager_count IS NOT NULL THEN 
        x.ending_manager_count WHEN x.ending_manager_count IS NULL AND x.ending_auditor_count IS NOT NULL THEN 
        x.ending_auditor_count ELSE x.ending_sales_count END AS [ending_final_count] 
                    
            , x.po_sales_count, x.po_auditor_count, x.po_manager_count,
                CASE WHEN x.po_manager_count IS NOT NULL THEN x.po_manager_count 
                    WHEN x.po_manager_count IS NULL AND x.po_auditor_count IS NOT NULL THEN x.po_auditor_count
                    ELSE x.po_sales_count END [po_final_count]
            , (quantity - 
            ISNULL(CASE WHEN x.ending_manager_count IS NOT NULL THEN x.ending_manager_count
                WHEN x.ending_manager_count IS NULL AND x.ending_auditor_count IS NOT NULL THEN x.ending_auditor_count
                ELSE x.ending_sales_count END, 0) -
            ISNULL(CASE WHEN x.po_manager_count IS NOT NULL THEN x.po_manager_count 
                    WHEN x.po_manager_count IS NULL AND x.po_auditor_count IS NOT NULL THEN x.po_auditor_count
                    ELSE x.po_sales_count END, 0)) AS variance
			, x.sales_user
			, x.auditor_user
			, x.manager_user
            , x.uom

            FROM
            (SELECT tblwhseinv.item_code, tblwhseinv.quantity AS quantity, 
        
            (SELECT sum(tblcounting_inv_row.actual_count) AS sum_1 FROM tblcounting_inv_row, tblcounting_inv WHERE 
            CAST(tblcounting_inv.transdate AS DATE) = @date AND tblcounting_inv.confirm = 0 AND tblwhseinv.item_code 
            = tblcounting_inv_row.item_code and tblcounting_inv_row.counting_id = tblcounting_inv.id and 
            tblcounting_inv.user_type = 'sales') AS ending_sales_count 
        
            ,(SELECT sum(tblcounting_inv_row.actual_count) AS sum_1 FROM tblcounting_inv_row, tblcounting_inv WHERE 
            CAST(tblcounting_inv.transdate AS DATE) = @date AND tblcounting_inv.confirm = 0 AND tblwhseinv.item_code 
            = tblcounting_inv_row.item_code and tblcounting_inv_row.counting_id = tblcounting_inv.id and 
            tblcounting_inv.user_type = 'auditor') AS ending_auditor_count 
        
            ,(SELECT sum(tblcounting_inv_row.actual_count) AS sum_1 FROM tblcounting_inv_row, tblcounting_inv WHERE 
            CAST(tblcounting_inv.transdate AS DATE) = @date AND tblcounting_inv.confirm = 0 AND tblwhseinv.item_code 
            = tblcounting_inv_row.item_code and tblcounting_inv_row.counting_id = tblcounting_inv.id and 
            tblcounting_inv.user_type = 'manager') AS ending_manager_count 
        
            , (SELECT sum(tblpulloutreqrow.quantity) AS sum_2 FROM tblpulloutreqrow, tblpulloutreq WHERE CAST(
            tblpulloutreq.transdate AS DATE) = @date AND tblpulloutreq.confirm = 0 AND tblwhseinv.item_code = 
            tblpulloutreqrow.item_code and tblpulloutreqrow.pulloutreq_id = tblpulloutreq.id and 
            tblpulloutreq.user_type = 'sales') AS po_sales_count 
        
            , (SELECT sum(tblpulloutreqrow.quantity) AS sum_2 FROM tblpulloutreqrow, tblpulloutreq WHERE CAST(
            tblpulloutreq.transdate AS DATE) = @date AND tblpulloutreq.confirm = 0 AND tblwhseinv.item_code = 
            tblpulloutreqrow.item_code and tblpulloutreqrow.pulloutreq_id = tblpulloutreq.id and 
            tblpulloutreq.user_type = 'auditor') AS po_auditor_count 
        
            , (SELECT sum(tblpulloutreqrow.quantity) AS sum_2 FROM tblpulloutreqrow, tblpulloutreq WHERE CAST(
            tblpulloutreq.transdate AS DATE) = @date AND tblpulloutreq.confirm = 0 AND tblwhseinv.item_code = 
            tblpulloutreqrow.item_code and tblpulloutreqrow.pulloutreq_id = tblpulloutreq.id and 
            tblpulloutreq.user_type = 'manager') AS po_manager_count 

			,(SELECT TOP 1 tbluser.username FROM tblcounting_inv_row, tblcounting_inv, tbluser WHERE 
            CAST(tblcounting_inv.transdate AS DATE) = @date AND tblcounting_inv.confirm = 0 AND tblwhseinv.item_code 
            = tblcounting_inv_row.item_code and tblcounting_inv_row.counting_id = tblcounting_inv.id and 
            tblcounting_inv.user_type = 'sales' and tblcounting_inv.created_by = tbluser.id) AS sales_user

			,(SELECT TOP 1tbluser.username FROM tblcounting_inv_row, tblcounting_inv, tbluser WHERE 
            CAST(tblcounting_inv.transdate AS DATE) = @date AND tblcounting_inv.confirm = 0 AND tblwhseinv.item_code 
            = tblcounting_inv_row.item_code and tblcounting_inv_row.counting_id = tblcounting_inv.id and 
            tblcounting_inv.user_type = 'auditor' and tblcounting_inv.created_by = tbluser.id) AS auditor_user

			,(SELECT TOP 1 tbluser.username FROM tblcounting_inv_row, tblcounting_inv, tbluser WHERE 
            CAST(tblcounting_inv.transdate AS DATE) = @date AND tblcounting_inv.confirm = 0 AND tblwhseinv.item_code 
            = tblcounting_inv_row.item_code and tblcounting_inv_row.counting_id = tblcounting_inv.id and 
            tblcounting_inv.user_type = 'manager' and tblcounting_inv.created_by = tbluser.id) AS manager_user
        
            , tblitems.uom 
            FROM tblwhseinv LEFT OUTER JOIN tblitems ON tblwhseinv.item_code = tblitems.item_code 
            WHERE tblwhseinv.warehouse = @whse)x)y
            WHERE y.ending_final_count IS NOT NULL or y.po_final_count IS NOT NULL
            ORDER BY y.item_code""".format(date, curr_user.whse)

    inv = db.engine.execute(final_count)

    # query if there's inventory count to confirm
    count_inv = count_header.query.filter(
        and_(count_header.confirm == False, cast(count_header.transdate, DATE) == date)).first()
    # if none return error message
    if not count_inv:
        return ResponseMessage(False, message="No inventory count to confirm").resp(), 401

    if request.method == 'GET':

        try:

            inv_schema = CountingInventoryRowSchema(many=True)
            result = inv_schema.dump(inv)

            return ResponseMessage(True, data=result).resp()

        except (pyodbc.IntegrityError, exc.IntegrityError) as err:
            return ResponseMessage(False, message=f"{err}").resp(), 500
        except Exception as err:
            return ResponseMessage(False, message=f"{err}").resp(), 500
        finally:
            db.session.close()

    if request.method == 'PUT':
        try:
            data = request.get_json()
            transdate = data['transdate']
            if not data['confirm']:
                return ResponseMessage(False, message="Invalid confirm value").resp(), 401
        except TypeError as err:
            return ResponseMessage(False, message=f"{err}").resp(), 401
        try:
            # check if there's a variance
            for_adjustment_in = [] # append here if variance is negative
            for_charge = [] # append here if variance is positive
            for_po = [] # append here if has final_po

            # get the obj type of adjustment in
            obj = ObjectType.query.filter_by(code='FNLC').first()

            # Check if has objtype
            if not obj:
                return ResponseMessage(False, message="Object type not found!").resp(), 401

            # query the series
            series = Series.query.filter_by(whsecode=curr_user.whse, objtype=obj.objtype).first()

            if not series:
                return ResponseMessage(False, message="Series not found!").resp(), 401
            # check if next num is not greater done end num
            if series.next_num + 1 > series.end_num:
                return ResponseMessage(False, message="Series number is greater than next num!").resp(), 401
            # construct reference
            reference = f"{series.code}-{obj.code}-{series.next_num}"

            # check if next num is not greater done end num
            # add to header
            header = {'series': series.id, 'objtype': obj.objtype, 'seriescode': series.code,
                    'transnumber': series.next_num, 'reference': reference,
                    'remarks': 'Final Count', 'created_by': curr_user.id,
                    'updated_by': curr_user.id, 'transdate': transdate}

            f_c = FinalInvCount(**header)
            db.session.add(f_c)
            db.session.flush()
            sales_u = set()
            auditor_u = set()
            manager_u = set()
            for item in inv:
                # get first then whse inv
                item_bal = WhseInv.query.filter_by(item_code=item.item_code, warehouse=curr_user.whse).first()
                # if the variance is negative which is the system inv is less than the actual
                # then for adjustment in
                if item.variance > 0:
                    # append to for adjustment in if variance is positive
                    for_adjustment_in.append(item)
                # if the variance is positive which is the system is greater than actual
                # then for charge
                elif item.variance < 0:
                    for_charge.append(item)
                # append to for po
                if item.po_final_count:
                    for_po.append(item)

                sales_u.add(item.sales_user)
                auditor_u.add(item.auditor_user)
                manager_u.add(item.manager_user)

                f_r = FinalInvCountRow()
                f_r.finalcount_id = f_c.id
                f_r.item_code = item.item_code
                f_r.quantity = item.quantity
                f_r.ending_sales_count = item.ending_sales_count
                f_r.ending_auditor_count = item.ending_auditor_count
                f_r.ending_manager_count = item.ending_manager_count
                f_r.ending_final_count = item.ending_final_count
                f_r.po_sales_count = item.po_sales_count
                f_r.po_auditor_count = item.po_auditor_count
                f_r.po_manager_count = item.po_manager_count
                f_r.po_final_count = item.po_final_count
                f_r.variance = item.variance
                f_r.uom = item.uom
                f_r.whsecode = curr_user.whse

                db.session.add(f_r)

            f_c.sales_user = str(sales_u).replace('{', '').replace('}', '')
            f_c.auditor_user = str(auditor_u).replace('{', '').replace('}', '')
            f_c.manager_user = str(manager_u).replace('{', '').replace('}', '')
            
            db.session.query(count_header).filter(
                and_(count_header.confirm == False, cast(count_header.transdate, DATE) == date)
            ).update({'confirm': True},synchronize_session=False)

            # if there's for adjustment in
            if for_adjustment_in:
                # get the obj type of adjustment in
                obj = ObjectType.query.filter_by(code='ADJI').first()
                # Check if has objtype
                if not obj:
                    raise Exception("Object type not found!")

                # query the series
                series = Series.query.filter_by(whsecode=curr_user.whse, objtype=obj.objtype).first()
                if not series:
                    raise Exception("Series not found!")

                # check if next num is not greater done end num
                if series.next_num + 1 > series.end_num:
                    raise Exception("Series number is greater than next num!")

                # construct reference
                reference = f"{series.code}-{obj.code}-{series.next_num}"

                # check if next num is not greater done end num
                # add to header
                header = {'series': series.id, 'objtype': obj.objtype, 'seriescode': series.code,
                        'transnumber': series.next_num, 'reference': reference,
                        'remarks': 'Based on Ending balance variance', 'created_by': curr_user.id,
                        'updated_by': curr_user.id, 'transdate': transdate}

                adj_in = ItemAdjustmentIn(**header)
                # add 1 to next series
                series.next_num += 1

                db.session.add_all([series, adj_in])
                db.session.flush()

                for row in for_adjustment_in:

                    adj_row = ItemAdjustmentInRow()
                    adj_row.adjustin_id = adj_in.id
                    adj_row.objtype = adj_in.objtype
                    adj_row.item_code = row.item_code
                    adj_row.quantity = row.variance
                    adj_row.uom = row.uom
                    adj_row.whsecode = curr_user.whse
                    adj_row.created_by = adj_in.created_by
                    adj_row.updated_by = adj_in.updated_by

                    db.session.add(adj_row)
            
            # if there's for charge
            if for_charge:
                # get the obj type of adjustment in
                obj = ObjectType.query.filter_by(code='SLES').first()
                # Check if has objtype
                if not obj:
                    raise Exception("Object type not found!")
                # query the series
                series = Series.query.filter_by(whsecode=curr_user.whse, objtype=obj.objtype).first()
                # check if has series
                if not series:
                    raise Exception("Series not found!")
                # check if next num is not greater done end num
                if series.next_num + 1 > series.end_num:
                    raise Exception("Series number is greater than next num!")
                # construct reference
                reference = f"{series.code}-{obj.code}-{series.next_num}"

                # add to data header
                header = {'objtype': obj.objtype, 'series': series.id, 'seriescode': series.code,
                        'transnumber': series.next_num, 'reference': reference,
                        'remarks': 'Based on Ending balance variance', 'created_by': curr_user.id,
                        'updated_by': curr_user.id, 'transtype': 'AR Sales', 'transdate': transdate}

                cust = db.session.query(Customer).filter(
                    and_(Customer.whse == curr_user.whse,
                         Customer.code.contains('Inv Short'))
                ).first()
                header['cust_code'] = cust.code
                header['cust_name'] = cust.name

                sales = SalesHeader(**header)

                # add 1 to next series
                series.next_num += 1

                db.session.add_all([series, sales])
                db.session.flush()

                for row in for_charge:
                    # query the inventory of warehouse
                    whseinv = WhseInv.query.filter_by(item_code=row.item_code, warehouse=curr_user.whse).first()
                    # check the quantity
                    if row.variance > whseinv.quantity:
                        raise Exception(f"{row['item_code'].title()} below qty!")

                    item_bal = WhseInv.query.filter_by(item_code=row.item_code, warehouse=curr_user.whse).first()
                    sales_row = SalesRow()
                    sales_row.sales_id = sales.id
                    sales_row.item_code = row.item_code
                    sales_row.quantity = row.variance * -1
                    # get the price
                    pricelist = db.session.query(PriceListRow
                                                 ).join(PriceListHeader
                                                        ).join(Warehouses, Warehouses.pricelist == PriceListHeader.id
                                                               ).filter(
                        and_(
                            Warehouses.whsecode == curr_user.whse,
                            PriceListRow.item_code == row.item_code
                        )
                    ).first()
                    if not pricelist:
                        raise Exception("Item code has no price!")
                    sales_row.unit_price = pricelist.price
                    sales_row.gross = sales_row.unit_price * sales_row.quantity
                    sales_row.whsecode = curr_user.whse
                    sales_row.uom = row.uom

                    

                    sales.gross += float(sales_row.gross)

                    db.session.add(sales_row)

                # update sales header
                sales.disc_amount = sales.gross * (sales.discprcnt / 100) + sales.row_discount
                sales.doctotal = sales.gross + sales.delfee - sales.disc_amount - sales.gc_amount
                sales.amount_due = sales.doctotal
            
            # if there's for po
            if for_po:
                to_whse = data['po_whse']
                sap_number = data['po_sap']
                # get the obj type of adjustment in
                obj = ObjectType.query.filter_by(code='POUT').first()
                # Check if has objtype
                if not obj:
                    raise Exception("Object type not found!")

                # query the series
                series = Series.query.filter_by(
                    whsecode=curr_user.whse, objtype=obj.objtype).first()
                if not series:
                    raise Exception("Series not found!")

                # check if next num is not greater done end num
                if series.next_num + 1 > series.end_num:
                    raise Exception("Series number is greater than next num!")

                # construct reference
                reference = f"{series.code}-{obj.code}-{series.next_num}"

                # check if next num is not greater done end num
                # add to header
                header = {'series': series.id, 'objtype': obj.objtype, 'seriescode': series.code,
                        'transnumber': series.next_num, 'reference': reference, 'created_by': curr_user.id,
                        'updated_by': curr_user.id, 'transdate': transdate,
                        'sap_number': sap_number if sap_number else None, 'confirm': True}

                po_header = PullOutHeader(**header)

                # add 1 to next series
                series.next_num += 1

                db.session.add_all([series, po_header])
                db.session.flush()

                for row in for_po:
                    # get first then whse inv
                    item_bal = WhseInv.query.filter_by(
                        item_code=row.item_code, warehouse=curr_user.whse).first()

                    # check if final count is greater than whse bal
                    if row.po_final_count > item_bal.quantity:
                        raise Exception(f"{row.item_code.title()} is below quantity.")

                    row = {'objtype': po_header.objtype, 'item_code': row.item_code,
                        'quantity': row.po_final_count, 'uom': row.uom, 'whsecode': curr_user.whse,
                        'created_by': po_header.created_by, 'updated_by': po_header.updated_by,
                        'to_whse': to_whse}

                    po_row = PullOutRow(**row)
                    po_row.pullout_id = po_header.id

                    db.session.add(po_row)

                db.session.query(po_req_header).filter(
                    and_(po_req_header.confirm == False,
                        cast(po_req_header.transdate, DATE) == date,
                        po_req_header.docstatus == 'O')
                ).update({'confirm': True, 'docstatus': 'C'}, synchronize_session=False)

            
            db.session.commit()
            return ResponseMessage(True, message="Successfully confirm!").resp()
        except (pyodbc.IntegrityError, exc.IntegrityError) as err:
            db.session.rollback()
            return ResponseMessage(False, message=f"{err}").resp(), 500
        except Exception as err:
            db.session.rollback()
            return ResponseMessage(False, message=f"{err}").resp(), 500
        finally:
            db.session.close()

