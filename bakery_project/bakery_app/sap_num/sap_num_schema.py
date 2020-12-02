from bakery_app import ma


class ForSAPIPSchema(ma.Schema):
    class Meta:
        ordered = True


    reference = ma.String()
    cust_code = ma.String()
    payment_type = ma.String()
    amount = ma.Number()
    reference2 = ma.String()