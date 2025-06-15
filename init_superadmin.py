#!/usr/bin/env python3
"""
Initialize superadmin account and global settings
This script should be run once to set up the system
"""

from app import app, db
from models import User, License, Settings
from models_extended import GlobalSettings
from werkzeug.security import generate_password_hash
import logging

def create_superadmin():
    """Create superadmin account if it doesn't exist"""
    with app.app_context():
        try:
            superadmin_email = 'admin@comolor.com'
            existing_user = User.get(superadmin_email)
            
            if existing_user:
                logging.info("Superadmin already exists")
                return existing_user
            
            # Create superadmin account
            superadmin_password = generate_password_hash('admin123')
            superadmin = User(
                email=superadmin_email,
                business_name='Comolor POS Admin',
                phone='+254700000000',
                password_hash=superadmin_password,
                role='superadmin'
            )
            superadmin.save()
            logging.info(f"Created superadmin: {superadmin_email}")
            
            # Create active license for superadmin (never expires)
            license_obj = License(
                business_id=superadmin.business_id,
                status='active',
                expiry_date=None
            )
            license_obj.save()
            logging.info(f"Created permanent license for superadmin")
            
            # Create settings for superadmin
            settings = Settings(
                business_id=superadmin.business_id,
                business_name='Comolor POS Admin',
                footer_text='Comolor POS - Point of Sale System'
            )
            settings.save()
            logging.info(f"Created settings for superadmin")
            
            # Create global settings if they don't exist
            global_settings = GlobalSettings.get()
            if not global_settings:
                global_settings = GlobalSettings()
                global_settings.save()
                logging.info("Created global settings")
            
            return superadmin
            
        except Exception as e:
            logging.error(f"Error creating superadmin: {e}")
            return None

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    superadmin = create_superadmin()
    if superadmin:
        print("✓ Superadmin initialization completed successfully")
        print(f"✓ Email: admin@comolor.com")
        print(f"✓ Password: admin123")
        print(f"✓ Business ID: {superadmin.business_id}")
    else:
        print("✗ Failed to initialize superadmin")