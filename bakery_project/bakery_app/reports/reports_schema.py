from bakery_app import ma


class CashTransSchema(ma.Schema):
    class Meta:
        ordered = True
        
    total_cash_on_hand = ma.Number()
    cash_sales = ma.Number()
    ar_cash_sales = ma.Number()
    ar_agent_sales = ma.Number()
    deposit = ma.Number()
    used_dep = ma.Number()
    bank_dep = ma.Number()
    epay = ma.Number()

class SalesTransSchema(ma.Schema):
    class Meta:
        ordered = True


    gross  = ma.Number()
    net_sales  = ma.Number()
    disc_amount  = ma.Number()
    gross_cash_sales  = ma.Number()
    disc_cash_sales  = ma.Number()
    net_cash_sales  = ma.Number()
    gross_ar_sales  = ma.Number()
    disc_ar_sales  = ma.Number()
    net_ar_sales  = ma.Number()
    gross_agent_sales  = ma.Number()
    disc_agent_sales  = ma.Number()
    net_agent_sales  = ma.Number()


class FinalInvCountSchema(ma.Schema):
    class Meta:
        ordered = True
    
    item_code = ma.String()
    actual_good = ma.Number()
    actual_pullout = ma.Number()
    system_bal = ma.Number()
    variance = ma.Number()
    price = ma.Number()
    total_amount = ma.Number()