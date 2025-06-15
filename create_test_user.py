#!/usr/bin/env python3
"""
Create a test business user with active license for testing
"""

from app import app, db
from models import User, License, Settings, Product, Payment
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
import logging
import uuid

def create_test_business():
    """Create test business user with active license and sample data"""
    with app.app_context():
        try:
            test_email = 'testbusiness@example.com'
            existing_user = User.get(test_email)
            
            if existing_user:
                logging.info("Test business user already exists")
                return existing_user
            
            # Create test business user
            test_password = generate_password_hash('test123')
            test_user = User(
                email=test_email,
                business_name='Test Coffee Shop',
                phone='+254700123456',
                password_hash=test_password,
                role='admin'
            )
            test_user.save()
            logging.info(f"Created test business user: {test_email}")
            
            # Create active license (30 days from now)
            license_obj = License(
                business_id=test_user.business_id,
                status='active',
                expiry_date=datetime.now() + timedelta(days=30)
            )
            license_obj.save()
            logging.info(f"Created active license for test business")
            
            # Create business settings
            settings = Settings(
                business_id=test_user.business_id,
                business_name='Test Coffee Shop',
                paybill='123456',
                footer_text='Test Coffee Shop - Fresh Coffee Daily'
            )
            settings.save()
            logging.info(f"Created settings for test business")
            
            # Create sample products
            sample_products = [
                Product(test_user.business_id, 'Coffee', 150.00, 'Beverages', 50),
                Product(test_user.business_id, 'Tea', 100.00, 'Beverages', 30),
                Product(test_user.business_id, 'Sandwich', 250.00, 'Food', 20),
                Product(test_user.business_id, 'Cake', 300.00, 'Food', 15),
                Product(test_user.business_id, 'Water', 50.00, 'Beverages', 100)
            ]
            
            Product.save_all(test_user.business_id, sample_products)
            logging.info(f"Created {len(sample_products)} sample products")
            
            # Create a confirmed payment record to show payment history
            payment = Payment(
                business_id=test_user.business_id,
                mpesa_code='QX12345678',
                phone_number='+254700123456',
                amount=3000,
                status='confirmed'
            )
            payments = [payment]
            Payment.save_all(test_user.business_id, payments)
            logging.info(f"Created sample payment record")
            
            return test_user
            
        except Exception as e:
            logging.error(f"Error creating test business: {e}")
            return None

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    test_user = create_test_business()
    if test_user:
        print("✓ Test business initialization completed successfully")
        print(f"✓ Email: testbusiness@example.com")
        print(f"✓ Password: test123")
        print(f"✓ Business Name: Test Coffee Shop")
        print(f"✓ License Status: Active (30 days)")
        print(f"✓ Sample products created")
        print(f"✓ Payment history added")
        print("\n--- How to test ---")
        print("1. Go to /login")
        print("2. Login with: testbusiness@example.com / test123")
        print("3. You'll be redirected to dashboard")
        print("4. Test all features: Products, POS, Reports, Settings")
    else:
        print("✗ Failed to initialize test business")