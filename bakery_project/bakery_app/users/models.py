
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
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False, unique=True)
    fullname = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(200), nullable=False)
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.now)
    branch = db.Column(db.String(50)) # branch code
    whse = db.Column(db.String(100)) # whsecode
    admin = db.Column(db.Boolean, default=False)
    sales = db.Column(db.Boolean, default=False)
    cashier = db.Column(db.Boolean, default=False)
    manager = db.Column(db.Boolean, default=False)
    own_stock = db.Column(db.Boolean, default=False)
    can_add_sap = db.Column(db.Boolean, default=False)
    transfer = db.Column(db.Boolean, default=False)
    receive = db.Column(db.Boolean, default=False)
    void = db.Column(db.Boolean, default=False)

    def hash_password(self, password):
        self.password  = bcrypt.generate_password_hash(password).decode('utf-8')

    def verify_password(self, password):
        return bcrypt.check_password_hash(self.password, password)

    def generate_auth_token(self, expires_sec=21600):
        # 30days token expiration
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

    def is_own_stock(self):
        return self.own_stock

    def is_can_add_sap(self):
        return self.can_add_sap

    def can_transfer(self):
        return self.transfer
        
    def can_receive(self):
        return self.receive
        
    def can_void(self):
        return self.void
    
    @staticmethod
    def verify_auth_token(token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            user_id = s.loads(token)['user_id']
        except SignatureExpired:
            return None # valid token, but expired
        except BadSignature:
            return None # invalid token
        except:
            return None
        return User.query.get(user_id)

    def __repr__(self):
        return f"User('{self.username}', '{self.fullname}')"


class UserSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = User
        ordered = True
        load_instance = True