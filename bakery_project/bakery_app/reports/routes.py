import pyodbc

from flask import Blueprint, request, jsonify, json
from sqlalchemy import and_, or_, case, cast, exc
from bakery_app import db
from bakery_app._helpers import BaseQuery
from bakery_app._utils import ResponseMessage
from bakery_app.users.routes import token_required
from bakery_app.payment.models import PayTransHeader, CashTransaction, Deposit
from bakery_app.sales.models import SalesHeader, SalesRow
from bakery_app.users.models import User


reports = Blueprint('reports', __name__)


@reports.route('/api/report/cs')
@token_required
def cash_sales_report(curr_user):
    try:
        branch = curr_user.branch
        from_date = request.args.get('from_date')
        to_date = request.args.get('to_date')
        user_id = request.args.get('user_id')
        cashier_id = request.args.get('cashier_id')
        query_cash_trans ="""
            Declare @branch varchar(100)
            Declare @cashier_id varchar(100)
            Declare @from_date varchar(100)
            Declare @to_date varchar(100)

            SET @branch = '{}'
            SET @from_date = '{}'
            SET @to_date = '{}'
            SET @cashier_id = '{}'


            SELECT SUM(ISNULL(CASE WHEN (a1.objtype = 6 and a1.transtype = 'DEPS') 
                                    OR (a1.objtype = 4 and a1.transtype != 'DEPS') 
                                THEN a1.amount END, 0)) [TotalCashOnHand],
                    -- Cash Sales
                    SUM(ISNULL(CASE WHEN a3.transtype = 'CASH' and a1.objtype = 4 THEN a1.amount END, 0)) [CashSales], 
                    -- AR Cash(Payment to Cash)
                    SUM(ISNULL(CASE WHEN a3.transtype = 'AR Sales' and a1.objtype = 4 THEN a1.amount END, 0)) [ARCash],
                    -- Add to OnHand Cash
                    SUM(ISNULL(CASE WHEN a1.objtype = 6 and a1.transtype = 'DEPS' THEN a1.amount END, 0)) [DepositCash],
                    -- Payment From Deposit
                    SUM(ISNULL(CASE WHEN a1.objtype = 4 and a1.transtype = 'DEPS' THEN a1.amount END, 0)) [FromDep] 

            FROM tblcashtrans a1 LEFT JOIN
            tblpayment a2 on a1.trans_id = a2.id and a1.objtype = a2.objtype LEFT JOIN 
            tblsales a3 on a2.base_id = a3.id
            WHERE (@from_date IS NULL OR CAST(a1.date_created as DATE) >= @from_date)
                    AND (@to_date IS NULL OR CAST(a1.date_created as DATE) <= @to_date)
                    AND (CAST(a1.created_by AS VARCHAR(MAX)) IN (SELECT a1.id FROM bakery_db.dbo.[tbluser] a1 
                            WHERE (@branch IS NULL OR a1.branch = @branch)))
                    AND (@cashier_id IS NULL OR CAST(a1.created_by as VARCHAR(100)) = @cashier_id) 
            """.format(branch, from_date, to_date, cashier_id)

        query_sales_trans ="""
            Declare @branch varchar(100)
            Declare @user varchar(100)
            Declare @from_date varchar(100)
            Declare @to_date varchar(100)

            SET @branch = '{}'
            SET @from_date = '{}'
            SET @to_date = '{}'
            SET @user = '{}'
            
            SELECT DISTINCT
            SUM(a3.gross) [Gross Sales],
            SUM(ISNULL(CASE WHEN a3.transtype = 'AR Sales' then doctotal end, 0)) [AR Sales],
            SUM(ISNULL(CASE WHEN a3.transtype = 'CASH' then doctotal end, 0)) [Cash Sales],
            SUM(a3.disc_amount) [Discount Amount]
            FROM tblpayment a2 LEFT JOIN
            tblsales a3 on a2.base_id = a3.id
            WHERE 
            (@from_date IS NULL OR CAST(a2.date_created as DATE) >= @from_date)
            AND (@to_date IS NULL OR CAST(a2.date_created as DATE) <= @to_date)
            AND (CAST(a3.created_by AS VARCHAR(MAX)) IN (SELECT a1.id FROM bakery_db.dbo.[tbluser] a1 
                    WHERE (@branch IS NULL OR a1.branch = @branch) and (@user IS NULL OR a1.id = @user)))
        """.format(branch, from_date, to_date, user_id)

        query_rows ="""
        Declare @branch varchar(100)
        Declare @user varchar(100)
        Declare @from_date varchar(100)
        Declare @to_date varchar(100)

        SET @branch = '{}'
        SET @from_date = '{}'
        SET @to_date = '{}'
        SET @user = '{}'

        select a2.reference, CAST(a2.transdate as DATE)[transdate], a1.amount, 
            CASE WHEN a1.objtype = 4 THEN '/api/sales/details/' + CAST(a2.base_id as varchar(30))
            WHEN a1.objtype = 6 THEN '/api/deposit/details/' + CAST(a1.trans_id as varchar(30))
            WHEN a1.objtype = 7 THEN '/api/cashout/details/' + CAST(a1.trans_id as varchar(30)) END [url]
        FROM tblcashtrans a1 LEFT JOIN
        tblpayment a2 on a1.trans_id = a2.id and a1.objtype = a2.objtype LEFT JOIN
        tblsales a3 on a2.base_id = a3.id
        WHERE 
        (@from_date IS NULL OR CAST(a1.date_created as DATE) >= @from_date)
        AND (@to_date IS NULL OR CAST(a1.date_created as DATE) <= @to_date)
        AND (CAST(a3.created_by AS VARCHAR(MAX)) IN (SELECT a1.id FROM bakery_db.dbo.[tbluser] a1 
                WHERE (@branch IS NULL OR a1.branch = @branch) and (@user IS NULL OR a1.id = @user)))
        """.format(branch, from_date, to_date, user_id)

        exec_cash_trans = db.engine.execute(query_cash_trans)
        exec_sales_trans = db.engine.execute(query_sales_trans)
        exec_rows = db.engine.execute(query_rows)

        result_cash_trans_dict = [dict(row) for row in exec_cash_trans]
        result_sales_trans_dict = [dict(row) for row in exec_sales_trans]
        result_rows_dict = [dict(row) for row in exec_rows]

        return ResponseMessage(True, data={
            'cash_trans': result_cash_trans_dict,
            'sales_trans': result_sales_trans_dict, 
            'sales_rows': result_rows_dict}
            ).resp()

    
    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
            return ResponseMessage(False, message=f"{err}").resp(), 500
    except Exception as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500
