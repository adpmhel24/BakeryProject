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
    isAdmin = db.Column(db.Boolean, default=False)
    isManager = db.Column(db.Boolean, default=False)
    isAuditor = db.Column(db.Boolean, default=False)
    isSales = db.Column(db.Boolean, default=False)
    isCashier = db.Column(db.Boolean, default=False)
    isChecker = db.Column(db.Boolean, default=False)
    isCanAddSap = db.Column(db.Boolean, default=False)
    isTransfer = db.Column(db.Boolean, default=False)
    isReceive = db.Column(db.Boolean, default=False)
    isVoid = db.Column(db.Boolean, default=False)
    isDiscount = db.Column(db.Boolean, default=False)
    isAllowEnding = db.Column(db.Boolean, default=False)
    isAllowPullOut = db.Column(db.Boolean, default=False)
    isARSales = db.Column(db.Boolean, default=False)
    isCashSales = db.Column(db.Boolean, default=False)
    isAgentSales = db.Column(db.Boolean, default=False)
    isActive = db.Column(db.Boolean, default=True)

    def hash_password(self, password):
        self.password = bcrypt.generate_password_hash(password).decode('utf-8')

    def verify_password(self, password):
        return bcrypt.check_password_hash(self.password, password)

    def generate_auth_token(self, expires_sec=172800):
        # 2days token expiration
        s = Serializer(current_app.config['SECRET_KEY'], expires_sec)
        return s.dumps({'user_id': self.id}).decode('utf-8')

    def is_admin(self):
        return self.isAdmin

    def is_manager(self):
        return self.isManager

    def is_sales(self):
        return self.isSales

    def is_cashier(self):
        return self.isCashier

    def is_checker(self):
        return self.isChecker

    def is_can_add_sap(self):
        return self.isCanAddSap

    def can_transfer(self):
        return self.isTransfer

    def can_receive(self):
        return self.isReceive

    def can_void(self):
        return self.isVoid

    def can_discount(self):
        return self.isDiscount

    def is_auditor(self):
        return self.isAuditor

    def is_ar_sales(self):
        return self.isARSales
    
    def is_cash_sales(self):
        return self.isCashSales

    def is_agent_sales(self):
        return self.isAgentSales

    def is_allow_ending(self):
        return self.isAllowEnding

    def is_allow_pullout(self):
        return self.isAllowPullOut

    def is_active(self):
        return self.isActive

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
