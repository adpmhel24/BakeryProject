from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_caching import Cache
from flask_httpauth import HTTPTokenAuth
from bakery_app.config import Config

db = SQLAlchemy()
bcrypt = Bcrypt()
cache = Cache()
login_manager = LoginManager()
auth = HTTPTokenAuth(scheme='Bearer')

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(Config)
    app.config['JSON_SORT_KEYS'] = False
    app.config['CACHE_TYPE'] = 'simple'


    db.init_app(app)
    bcrypt.init_app(app)
    cache.init_app(app)
    login_manager.init_app(app)

    from bakery_app.inventory.routes import inventory
    
    app.register_blueprint(inventory)

    return app
    
