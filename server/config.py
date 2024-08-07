import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_jwt_extended import JWTManager
from flask_mail import Mail

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'your_secret_key')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URI', 'sqlite:///app.db')  # Correct default value
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'your_jwt_secret_key')
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'flashads9@gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = bool(os.environ.get('MAIL_USE_TLS', True))
    MAIL_USE_SSL = bool(os.environ.get('MAIL_USE_SSL', False))
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', 'flashads9@gmail.com')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '07281534Sa')
    MAIL_DEFAULT_SENDER = (os.environ.get('MAIL_SENDER_NAME', 'Movers App'), os.environ.get('MAIL_DEFAULT_SENDER', 'flashads9@gmail.com'))

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
jwt = JWTManager()
mail = Mail()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)  # Use Config class
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    jwt.init_app(app)
    mail.init_app(app)
    return app
