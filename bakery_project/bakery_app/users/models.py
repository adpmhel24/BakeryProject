from datetime import datetime
from itsdangerous import (TimedJSONWebSignatureSerializer as Serializer,
                          BadSignature, SignatureExpired)
from flask import current_app
from bakery_app import db, ma, login_manager, bcrypt
from flask_login import UserMixin


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(db.Model, UserMixin):
    __tablename__ = "tbluser"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False, unique=True)
    fullname = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(200), nullable=False)
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.now)
    date_updated = db.Column(db.DateTime, default=datetime.now)
    branch = db.Column(db.String(50))  # branch code
    whse = db.Column(db.String(100))  # whsecode
    admin = db.Column(db.Boolean, default=False)
    sales = db.Column(db.Boolean, default=False)
    cashier = db.Column(db.Boolean, default=False)
    manager = db.Column(db.Boolean, default=False)
    can_add_sap = db.Column(db.Boolean, default=False)
    transfer = db.Column(db.Boolean, default=False)
    receive = db.Column(db.Boolean, default=False)
    void = db.Column(db.Boolean, default=False)
    discount = db.Column(db.Boolean, default=False)
    auditor = db.Column(db.Boolean, default=False)
    ar_sales = db.Column(db.Boolean, default=False)
    cash_sales = db.Column(db.Boolean, default=False)
    agent_sales = db.Column(db.Boolean, default=False)
    active = db.Column(db.Boolean, default=True)
    

    def hash_password(self, password):
        self.password = bcrypt.generate_password_hash(password).decode('utf-8')

    def verify_password(self, password):
        return bcrypt.check_password_hash(self.password, password)

    def generate_auth_token(self, expires_sec=172800):
        # 2days token expiration
        s = Serializer(current_app.config['SECRET_KEY'], expires_sec)
        return s.dumps({'user_id': self.id}).decode('utf-8')

    def is_admin(self):
        return self.admin

    def is_manager(self):
        return self.manager

    def is_sales(self):
        return self.sales

    def is_cashier(self):
        return self.cashier

    def is_can_add_sap(self):
        return self.can_add_sap

    def can_transfer(self):
        return self.transfer

    def can_receive(self):
        return self.receive

    def can_void(self):
        return self.void

    def is_active(self):
        return self.void

    def can_discount(self):
        return self.discount

    def is_auditor(self):
        return self.auditor

    def is_ar_sales(self):
        return self.ar_sales
    
    def is_cash_sales(self):
        return self.cash_sales

    def is_agent_sales(self):
        return self.agent_sales

    @staticmethod
    def verify_auth_token(token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            user_id = s.loads(token)['user_id']
        except SignatureExpired:
            return None
        except BadSignature:
            return None
        return User.query.get(user_id)

    def __repr__(self):
        return f"User('{self.username}', '{self.fullname}')"


class UserSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = User
        ordered = True
        load_instance = True
