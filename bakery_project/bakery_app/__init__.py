from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_caching import Cache
from flask_httpauth import HTTPTokenAuth
from flask_marshmallow import Marshmallow
from bakery_app.config import Config
from bakery_app._helpers import CustomJSONEncoder

db = SQLAlchemy()
bcrypt = Bcrypt()
cache = Cache()
ma = Marshmallow()
login_manager = LoginManager()
login_manager.login_view = 'users.login'
login_manager.login_message_category = 'info'
auth = HTTPTokenAuth(scheme='Bearer')

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(Config)
    app.config['JSON_SORT_KEYS'] = False
    app.config['CACHE_TYPE'] = 'simple'
    app.json_encoder = CustomJSONEncoder


    db.init_app(app)
    bcrypt.init_app(app)
    cache.init_app(app)
    login_manager.init_app(app)
    ma.init_app(app)

    from bakery_app.users.routes import users
    from bakery_app.inventory.routes import inventory
    from bakery_app.branches.routes import branches
    from bakery_app.customers.routes import customers
    from bakery_app.sales.routes import sales
    
    app.register_blueprint(users)
    app.register_blueprint(inventory)
    app.register_blueprint(branches)
    app.register_blueprint(customers)
    app.register_blueprint(sales)

    return app
    
