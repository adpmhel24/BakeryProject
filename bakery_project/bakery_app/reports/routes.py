import pyodbc

from flask import Blueprint, request, jsonify, json
from sqlalchemy import and_, or_, case, cast, exc, DATE, func
from bakery_app import db
from bakery_app._helpers import BaseQuery
from bakery_app._utils import ResponseMessage
from bakery_app.users.routes import token_required
from bakery_app.payment.models import PayTransHeader, CashTransaction, Deposit
from bakery_app.sales.models import SalesHeader, SalesRow
from bakery_app.sales.sales_schema import SalesHeaderSchema, SalesRowSchema
from bakery_app.pullout.models import PullOutHeader
from bakery_app.pullout.po_schema import PullOutHeaderSchema
from bakery_app.inventory_count.models import FinalInvCount, FinalInvCountRow
from bakery_app.inventory_count.inv_count_schema import FinalCountSchema
from bakery_app.branches.models import Warehouses
from bakery_app.items.models import PriceListRow
from bakery_app.users.models import User

from .reports_schema import CashTransSchema, SalesTransSchema, FinalInvCountSchema

reports = Blueprint('reports', __name__)


# Cash Flow Report
@reports.route('/api/report/cs')
@token_required
def cash_flow_report(curr_user):
    try:
        branch = curr_user.branch
        from_date = request.args.get('from_date')
        to_date = request.args.get('to_date')
        cashier_id = request.args.get('cashier_id')
        sales_type = request.args.get('sales_type')
        payment_type = request.args.get('payment_type')
        query_cash_trans = """
            Declare @branch varchar(100)
            Declare @cashier_id varchar(100)
            Declare @from_date varchar(100)
            Declare @to_date varchar(100)
            Declare @sales_type varchar(50)
            Declare @payment_type varchar(50)
            
            SET @branch = '{}'
            SET @from_date = '{}'
            SET @to_date = '{}'
            SET @cashier_id = '{}'
            SET @sales_type = '{}'
            SET @payment_type = '{}'
            
            
            
            SELECT SUM(ISNULL(CASE WHEN a1.transtype IN ('DEPS', 'CASH')
                                THEN a1.amount END, 0)) [TotalCashOnHand],
                    -- Cash Sales
                    SUM(ISNULL(CASE WHEN a3.transtype = 'CASH' and a1.transtype = 'CASH' 
                        THEN a1.amount END, 0)) [CashSales], 
                    -- AR Cash(Payment to Cash)
                    SUM(ISNULL(CASE WHEN a3.transtype IN ('AR Sales') and a1.transtype = 'CASH' 
                        and a1.objtype = 4 THEN a1.amount END, 0)) [ARCash],
                    -- AR Agent Cash(Payment to Cash)
                    SUM(ISNULL(CASE WHEN a3.transtype IN ('Agent AR Sales') and a1.transtype = 'CASH' 
                        and a1.objtype = 4 THEN a1.amount END, 0)) [ARAgentCash],
                    -- Add to OnHand Cash
                    SUM(ISNULL(CASE WHEN a1.objtype = 6 and a1.transtype = 'DEPS' THEN a1.amount END, 0)) [DepositCash],
                    -- Payment From Deposit
                    SUM(ISNULL(CASE WHEN a1.objtype = 4 and a1.transtype = 'FDEPS' THEN a1.amount END, 0)) [FromDep],
                    --Payment From Bank Deposit 
                    SUM(ISNULL(CASE WHEN a1.objtype = 4 and a1.transtype = 'BDEP' THEN a1.amount END, 0)) [BankDep],
                    --Payment From Electronic Payment
                    SUM(ISNULL(CASE WHEN a1.objtype = 4 and a1.transtype = 'EPAY' THEN a1.amount END, 0)) [EPAY]  
            
            FROM tblcashtrans a1 LEFT JOIN
            tblpayment a2 on a1.trans_id = a2.id and a1.objtype = a2.objtype LEFT JOIN 
            tblsales a3 on a2.base_id = a3.id
            WHERE (@from_date IS NULL OR CAST(a1.date_created as DATE) >= @from_date)
                    AND (@to_date IS NULL OR CAST(a1.date_created as DATE) <= @to_date)
                    AND (CAST(a1.created_by AS VARCHAR(MAX)) IN (SELECT a1.id FROM bakery_db.dbo.[tbluser] a1 
                            WHERE (@branch = '' OR a1.branch = @branch)))
                    AND (@cashier_id = '' OR a1.created_by = @cashier_id)
                    AND (@sales_type = '' OR a3.transtype = @sales_type)
                    AND (@payment_type = '' OR a1.transtype = @payment_type)
            """.format(branch, from_date, to_date, cashier_id, sales_type, payment_type)

        query_rows = """
            Declare @branch varchar(100)
            Declare @from_date varchar(100)
            Declare @to_date varchar(100)
            Declare @sales_type varchar(50)
            Declare @payment_type varchar(50)
    
            SET @branch = '{}'
            SET @from_date = '{}'
            SET @to_date = '{}'
            SET @sales_type = '{}'
            SET @payment_type = '{}'
   
            select a1.reference, CAST(a1.transdate as DATE)[transdate], a1.amount, 
                CASE WHEN a1.objtype = 4 THEN '/api/payment/details/' + CAST(a2.id as varchar(30))
                WHEN a1.objtype = 6 THEN '/api/deposit/details/' + CAST(a1.trans_id as varchar(30))
                WHEN a1.objtype = 7 THEN '/api/cashout/details/' + CAST(a1.trans_id as varchar(30)) END [url],
                a4.description [PaymentType],
                a3.transtype [SalesType]
                FROM tblcashtrans a1 LEFT JOIN
                tblpayment a2 on a1.trans_id = a2.id and a1.objtype = a2.objtype LEFT JOIN
                tblsales a3 on a2.base_id = a3.id LEFT JOIN
                tblpaymenttype a4 on a1.transtype = a4.code
            WHERE 
                (@from_date IS NULL OR CAST(a1.date_created as DATE) >= @from_date)
                AND (@to_date IS NULL OR CAST(a1.date_created as DATE) <= @to_date)
                AND( (CAST(a3.created_by AS VARCHAR(MAX)) IN (SELECT a1.id FROM bakery_db.dbo.[tbluser] a1 
                        WHERE (@branch IS NULL OR a1.branch = @branch)))
                OR 
                    (CAST(a1.created_by AS VARCHAR(MAX)) IN (SELECT a1.id FROM bakery_db.dbo.[tbluser] a1 
                        WHERE (@branch IS NULL OR a1.branch = @branch))))
                AND (@payment_type = '' OR a1.transtype = @payment_type)
                AND (@sales_type = '' OR a3.transtype = @sales_type)
        """.format(branch, from_date, to_date, sales_type, payment_type)

        exec_cash_trans = db.engine.execute(query_cash_trans)
        exec_rows = db.engine.execute(query_rows)

        result_cash_trans_dict = [dict(row) for row in exec_cash_trans]
        result_rows_dict = [dict(row) for row in exec_rows]

        return ResponseMessage(True, data={
            'cash_trans': result_cash_trans_dict,
            'sales_rows': result_rows_dict}
                               ).resp()

    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500
    except Exception as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500


# Sales Report
@reports.route('/api/sales/report')
@token_required
def sales_report(curr_user):
    try:
        sale_filt = []
        user_filt = [('branch', '==', curr_user.branch)]
        date = ''
        data = request.args.to_dict()
        for k, v in data.items():
            if k == 'date':
                date = v
            elif k == 'user_id':
                if v:
                    user_filt.append(('id', '==', v))
            elif k == 'whse':
                if v:
                    user_filt.append((k, "==", v))
            else:
                if v:
                    sale_filt.append((k, '==', v))

        sales_filters = BaseQuery.create_query_filter(SalesHeader, filters={'and': sale_filt})
        user_filters = BaseQuery.create_query_filter(User, filters={'and': user_filt})

        cash_case = case([(SalesHeader.transtype == 'CASH', SalesHeader.doctotal)])
        ar_case = case([(SalesHeader.transtype == 'AR Sales', SalesHeader.doctotal)])
        ar_agent_case = case([(SalesHeader.transtype == 'Agent AR Sales', SalesHeader.doctotal)])

        sales_header = db.session.query(
            func.sum(SalesHeader.gross).label('gross'),
            func.sum(cash_case).label('cashsales'),
            func.sum(ar_case).label('arsales'),
            func.sum(ar_agent_case).label('agentsales'),
            func.sum(SalesHeader.disc_amount).label('disc_amount')
        ).outerjoin(User, SalesHeader.created_by == User.id
                    ).filter(
            and_(func.cast(SalesHeader.transdate, DATE) == date,
                 SalesHeader.confirm,
                 SalesHeader.docstatus != 'N',
                 *sales_filters,
                 *user_filters
                 )
        ).first()

        sales_row = db.session.query(
            SalesHeader.id,
            SalesHeader.transnumber,
            SalesHeader.transdate,
            SalesHeader.cust_code,
            SalesHeader.reference,
            SalesHeader.gross,
            SalesHeader.doctotal,
            SalesHeader.transtype,
            User.username.label('user')
        ).outerjoin(User, SalesHeader.created_by == User.id
                    ).filter(
            and_(func.cast(SalesHeader.transdate, DATE) == date,
                 SalesHeader.confirm,
                 SalesHeader.docstatus != 'N',
                 *sales_filters,
                 *user_filters
                 )
        ).all()

        header_schema = SalesHeaderSchema()
        row_schema = SalesHeaderSchema(many=True, exclude=("salesrow",))
        header_result = header_schema.dump(sales_header)
        row_result = row_schema.dump(sales_row)
        return ResponseMessage(True, data={"header": header_result, "row": row_result}).resp()

    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500
    except Exception as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500
    finally:
        db.session.close()


@reports.route('/api/report/pullout')
@token_required
def pullout_report(curr_user):
    try:
        date = request.args.get('date')
        pull_out = PullOutHeader.query.filter(func.cast(PullOutHeader.transdate, DATE) == date).all()
        po_schema = PullOutHeaderSchema(many=True)
        result = po_schema.dump(pull_out)
        return ResponseMessage(True, count=len(result), data=result).resp()

    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500
    except Exception as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500
    finally:
        db.session.close()


@reports.route('/api/report/final_count')
@token_required
def final_count_report(curr_user):
    data = request.args.to_dict()
    
    transdate = ''
    filt = []
    for k, v in data.items():
        if k == 'whsecode':
            if v:
                filt.append((k, "==", v))
            else:
                filt.append(k, "==", curr_user.whse)
        elif k == 'transdate':
            if v:
                transdate = v
        else:
            if v:
                filt.append(k, "==", v)

    try:
        final_count = FinalInvCount.query. \
            filter(func.cast(FinalInvCount.transdate, DATE) == transdate,
                    FinalInvCountRow.whsecode == curr_user.whse,).first()
        if not final_count:
            raise Exception("No final count transaction!")
        fc_schema = FinalCountSchema()
        result = fc_schema.dump(final_count)
        return ResponseMessage(True, data=result).resp()
        
    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500
    except Exception as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500
    finally:
        db.session.close()


@reports.route('/api/report/final_report')
@token_required
def final_report(curr_user):
    try:
        data = request.args.to_dict()
        transdate = ''
        user_filt = [
            ('branch', '==', curr_user.branch),
        ]
        cash_filt = []
        sales_filt = []
        for k, v in data.items():
            if k == 'transdate':
                if v:
                    transdate = v
            # elif k == 'whsecode':
            #     if not curr_user.is_admin():
            #         sales_filt.append(('whsecode', "==", curr_user.whse))
            #     else:
            #         sales_filt.append(('whsecode', "==", v))
            else:
                if v:
                    sales_filt.append((k, "==", v))

        user_filters = BaseQuery.create_query_filter(User, filters={'and': user_filt})
        sales_filters = BaseQuery.create_query_filter(SalesHeader, filters={'and': sales_filt})

        # Payment Cases

        cash_trans = CashTransaction
        pay_trans = PayTransHeader
        sales_trans = SalesHeader

        cash_on_hand_case = case([(cash_trans.transtype.in_(['CASH', 'DEPS']), cash_trans.amount)])
        cash_sales_case = case([(and_(cash_trans.transtype == 'CASH', 
                                        sales_trans.transtype == 'CASH'), cash_trans.amount)])
        ar_cash_case = case([(and_(cash_trans.transtype == 'CASH',  
                                        sales_trans.transtype == 'AR Sales'), cash_trans.amount)])
        ar_agent_cash_case = case([(and_(cash_trans.transtype == 'CASH', 
                                            sales_trans.transtype == 'Agent AR Sales'), cash_trans.amount)])
        deposit_case = case([(cash_trans.transtype == 'DEPS', cash_trans.amount)])
        used_dep_case = case([(cash_trans.transtype == 'FDEPS', cash_trans.amount)])
        bank_dep_case = case([(cash_trans.transtype == 'BDEP', cash_trans.amount)])
        epay_case = case([(cash_trans.transtype == 'EPAY', cash_trans.amount)])

        cash_header = db.session.query(
                func.sum(cash_on_hand_case).label('total_cash_on_hand'),
                func.sum(cash_sales_case).label('cash_sales'),
                func.sum(ar_cash_case).label('ar_cash_sales'),
                func.sum(ar_agent_cash_case).label('ar_agent_sales'),
                func.sum(deposit_case).label('deposit'),
                func.sum(used_dep_case).label('used_dep'),
                func.sum(bank_dep_case).label('bank_dep'),
                func.sum(epay_case).label('epay')). \
            select_from(cash_trans). \
            join(User, cash_trans.created_by == User.id). \
            outerjoin(pay_trans, pay_trans.id == cash_trans.trans_id). \
            outerjoin(sales_trans, pay_trans.base_id == sales_trans.id).\
            filter(and_(cast(cash_trans.transdate, DATE) == transdate,
                        *user_filters
                        ))


        # Sales Type Cash Case
        gross_cash_case = case([(SalesHeader.transtype == 'CASH', SalesHeader.doctotal)])
        disc_cash_case = case([(SalesHeader.transtype == 'CASH', SalesHeader.disc_amount)])
        net_cash_case = case([(SalesHeader.transtype == 'CASH', SalesHeader.doctotal)])

        # Sales Type AR Sales Case
        gross_ar_case = case([(SalesHeader.transtype == 'AR Sales', SalesHeader.doctotal)])
        disc_ar_case = case([(SalesHeader.transtype == 'AR Sales', SalesHeader.disc_amount)])
        net_ar_case = case([(SalesHeader.transtype == 'AR Sales', SalesHeader.doctotal)])

        # Sales Type Agent AR Sales Case
        gross_ar_agent_case = case([(SalesHeader.transtype == 'Agent AR Sales', SalesHeader.doctotal)])
        disc_ar_agent_case = case([(SalesHeader.transtype == 'Agent AR Sales', SalesHeader.disc_amount)])
        net_ar_agent_case = case([(SalesHeader.transtype == 'Agent AR Sales', SalesHeader.doctotal)])

        
        # Sales Total and Transaction
        sales_header = db.session.query(
            func.sum(SalesHeader.gross).label('gross'),
            func.sum(SalesHeader.gross).label('net_sales'),
            func.sum(SalesHeader.disc_amount).label('disc_amount'),
            
            func.sum(gross_cash_case).label('gross_cash_sales'),
            func.sum(disc_cash_case).label('disc_cash_sales'),
            func.sum(net_cash_case).label('net_cash_sales'),

            func.sum(gross_ar_case).label('gross_ar_sales'),
            func.sum(disc_ar_case).label('disc_ar_sales'),
            func.sum(net_ar_case).label('net_ar_sales'),
            
            func.sum(gross_ar_agent_case).label('gross_agent_sales'),
            func.sum(disc_ar_agent_case).label('disc_agent_sales'),
            func.sum(net_ar_agent_case).label('net_agent_sales'))\
                .outerjoin(User, SalesHeader.created_by == User.id)\
                .filter(and_(
                        func.cast(SalesHeader.transdate, DATE) == transdate,
                        SalesHeader.confirm == True,
                        SalesHeader.docstatus != 'N',
                        *sales_filters,
                        *user_filters
                        ))

        # Item Variance Count
        fc_header = FinalInvCount
        fc_row = FinalInvCountRow
        variance = (fc_row.ending_final_count + fc_row.po_final_count - fc_row.quantity)
        final_count_query = db.session.query(
                fc_row.item_code,
                fc_row.ending_final_count.label('actual_good'),
                fc_row.po_final_count.label('actual_pullout'),
                fc_row.quantity.label('system_bal'),
                variance.label('variance'),
                PriceListRow.price,
                (PriceListRow.price * variance).label('total_amount')
                ). \
            select_from(fc_header). \
            join(fc_row, fc_row.finalcount_id == fc_header.id). \
            outerjoin(Warehouses, fc_row.whsecode == Warehouses.whsecode). \
            outerjoin(PriceListRow, and_(PriceListRow.pricelist_id == Warehouses.pricelist,
                                        PriceListRow.item_code == fc_row.item_code)). \
            filter(cast(fc_header.transdate, DATE) == transdate)
            


        

        # sales_cash = db.session.query(
        #             func.cast(SalesHeader.transdate, DATE),
        #             func.sum(SalesHeader.gross).label('gross'),
        #             func.sum(SalesHeader.disc_amount).label('disc_amount'),
        #             func.sum(SalesHeader.doctotal).label('doctotal'))\
        #         .outerjoin(User, SalesHeader.created_by == User.id)\
        #         .filter(and_(
        #                     func.cast(SalesHeader.transdate, DATE) >= transdate,
        #                     SalesHeader.confirm,
        #                     SalesHeader.docstatus != 'N',
        #                     SalesHeader.transtype == 'CASH',
        #                     *sales_filters,
        #                     *user_filters))\
        #         .group_by(SalesHeader.transdate).all()

        # sales_ar = db.session.query(
        #             SalesHeader.reference,
        #             SalesHeader.transdate,
        #             SalesHeader.cust_code,
        #             SalesHeader.gross,
        #             SalesHeader.disc_amount,
        #             SalesHeader.doctotal)\
        #         .outerjoin(User, SalesHeader.created_by == User.id)\
        #         .filter(and_(
        #                     func.cast(SalesHeader.transdate, DATE) >= transdate,
        #                     SalesHeader.confirm,
        #                     SalesHeader.docstatus != 'N',
        #                     SalesHeader.transtype == 'AR Sales',
        #                     *sales_filters,
        #                     *user_filters)).all()

        # sales_ar_agent = db.session.query(
        #             func.cast(SalesHeader.transdate, DATE),
        #             func.sum(SalesHeader.gross).label('gross'),
        #             func.sum(SalesHeader.disc_amount).label('disc_amount'),
        #             func.sum(SalesHeader.doctotal).label('doctotal'))\
        #         .outerjoin(User, SalesHeader.created_by == User.id)\
        #         .filter(and_(
        #                     func.cast(SalesHeader.transdate, DATE) >= transdate,
        #                     SalesHeader.confirm,
        #                     SalesHeader.docstatus != 'N',
        #                     SalesHeader.transtype == 'Agent AR Sales',
        #                     *sales_filters,
        #                     *user_filters)\
        #         .group_by(SalesHeader.transdate)).all()
        
        cash_schema = CashTransSchema(many=True)
        cash_result = cash_schema.dump(cash_header)
        sales_schema = SalesTransSchema(many=True)
        sales_result = sales_schema.dump(sales_header)
        final_inv_schema = FinalInvCountSchema(many=True)
        final_inv_result = final_inv_schema.dump(final_count_query)
        return ResponseMessage(True, data={'cash': cash_result, 
                                        'sales': sales_result, 
                                        'final_inv': final_inv_result
                                        }).resp()
        

        
    except (pyodbc.IntegrityError, exc.IntegrityError) as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500
    except Exception as err:
        return ResponseMessage(False, message=f"{err}").resp(), 500
    finally:
        db.session.close()
        
        