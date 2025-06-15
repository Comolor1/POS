import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from werkzeug.middleware.proxy_fix import ProxyFix
from sqlalchemy.orm import DeclarativeBase

# Setup logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default_secret_key_for_development")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure database
database_url = os.environ.get("DATABASE_URL")
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url or "sqlite:///comolor_pos.db"
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize database
db = SQLAlchemy(model_class=Base)
db.init_app(app)
migrate = Migrate(app, db)

# Setup Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

# Create database tables and initialize superadmin
with app.app_context():
    # Import models to ensure they're registered
    import models
    db.create_all()
    
    # Create superadmin user if it doesn't exist
    from werkzeug.security import generate_password_hash
    superadmin_email = 'admin@comolor.com'
    superadmin = models.User.get(superadmin_email)
    
    if not superadmin:
        # Create superadmin account
        superadmin_password = generate_password_hash('admin123')
        superadmin = models.User(
            email=superadmin_email,
            business_name='Comolor POS Admin',
            phone='+254700000000',
            password_hash=superadmin_password,
            role='superadmin'
        )
        superadmin.save()
        
        # Create active license for superadmin (never expires)
        license_obj = models.License(
            business_id=superadmin.business_id,
            status='active',
            expiry_date=None
        )
        license_obj.save()
        
        # Create settings for superadmin
        settings = models.Settings(
            business_id=superadmin.business_id,
            business_name='Comolor POS Admin',
            footer_text='Comolor POS - Point of Sale System'
        )
        settings.save()
        
        print("Superadmin account created: admin@comolor.com / admin123")

# Import routes after app creation to avoid circular imports
from routes import *
from auth import *
