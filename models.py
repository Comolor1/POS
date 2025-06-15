from datetime import datetime, timedelta
from flask_login import UserMixin
from replit import db
import json
import uuid

class User(UserMixin):
    def __init__(self, email, business_name, phone, password_hash, role='admin', business_id=None):
        self.email = email
        self.business_name = business_name
        self.phone = phone
        self.password_hash = password_hash
        self.role = role
        self.business_id = business_id or str(uuid.uuid4())
        self.created_at = datetime.now().isoformat()
    
    def get_id(self):
        return self.email
    
    @staticmethod
    def get(email):
        user_data = db.get(f"users:{email}")
        if user_data:
            data = json.loads(user_data)
            user = User(
                email=data['email'],
                business_name=data['business_name'],
                phone=data['phone'],
                password_hash=data['password_hash'],
                role=data.get('role', 'admin'),
                business_id=data.get('business_id')
            )
            user.created_at = data.get('created_at')
            return user
        return None
    
    def save(self):
        user_data = {
            'email': self.email,
            'business_name': self.business_name,
            'phone': self.phone,
            'password_hash': self.password_hash,
            'role': self.role,
            'business_id': self.business_id,
            'created_at': self.created_at
        }
        db[f"users:{self.email}"] = json.dumps(user_data)
        
        # Also save business info
        business_data = {
            'id': self.business_id,
            'name': self.business_name,
            'owner_email': self.email,
            'phone': self.phone,
            'created_at': self.created_at
        }
        db[f"business:{self.business_id}"] = json.dumps(business_data)

class Product:
    def __init__(self, business_id, name, price, category, stock_quantity=0, product_id=None):
        self.product_id = product_id or str(uuid.uuid4())
        self.business_id = business_id
        self.name = name
        self.price = float(price)
        self.category = category
        self.stock_quantity = int(stock_quantity)
        self.created_at = datetime.now().isoformat()
    
    @staticmethod
    def get_all(business_id):
        products_data = db.get(f"products:{business_id}")
        if products_data:
            products_list = json.loads(products_data)
            return [Product(
                business_id=p['business_id'],
                name=p['name'],
                price=p['price'],
                category=p['category'],
                stock_quantity=p['stock_quantity'],
                product_id=p['product_id']
            ) for p in products_list]
        return []
    
    @staticmethod
    def save_all(business_id, products):
        products_data = []
        for product in products:
            products_data.append({
                'product_id': product.product_id,
                'business_id': product.business_id,
                'name': product.name,
                'price': product.price,
                'category': product.category,
                'stock_quantity': product.stock_quantity,
                'created_at': product.created_at
            })
        db[f"products:{business_id}"] = json.dumps(products_data)

class Sale:
    def __init__(self, business_id, items, total, payment_method, mpesa_ref=None, customer_name=None, sale_id=None):
        self.sale_id = sale_id or str(uuid.uuid4())
        self.business_id = business_id
        self.items = items  # List of {'product_id', 'name', 'price', 'quantity'}
        self.total = float(total)
        self.payment_method = payment_method
        self.mpesa_ref = mpesa_ref
        self.customer_name = customer_name
        self.created_at = datetime.now().isoformat()
    
    @staticmethod
    def get_all(business_id):
        sales_data = db.get(f"sales:{business_id}")
        if sales_data:
            sales_list = json.loads(sales_data)
            return [Sale(
                business_id=s['business_id'],
                items=s['items'],
                total=s['total'],
                payment_method=s['payment_method'],
                mpesa_ref=s.get('mpesa_ref'),
                customer_name=s.get('customer_name'),
                sale_id=s['sale_id']
            ) for s in sales_list]
        return []
    
    @staticmethod
    def save_all(business_id, sales):
        sales_data = []
        for sale in sales:
            sales_data.append({
                'sale_id': sale.sale_id,
                'business_id': sale.business_id,
                'items': sale.items,
                'total': sale.total,
                'payment_method': sale.payment_method,
                'mpesa_ref': sale.mpesa_ref,
                'customer_name': sale.customer_name,
                'created_at': sale.created_at
            })
        db[f"sales:{business_id}"] = json.dumps(sales_data)

class License:
    def __init__(self, business_id, status='pending', expiry_date=None):
        self.business_id = business_id
        self.status = status  # 'pending', 'active', 'expired'
        self.expiry_date = expiry_date
        self.created_at = datetime.now().isoformat()
    
    @staticmethod
    def get(business_id):
        license_data = db.get(f"licenses:{business_id}")
        if license_data:
            data = json.loads(license_data)
            license_obj = License(
                business_id=data['business_id'],
                status=data['status'],
                expiry_date=data.get('expiry_date')
            )
            license_obj.created_at = data.get('created_at')
            return license_obj
        return None
    
    def save(self):
        license_data = {
            'business_id': self.business_id,
            'status': self.status,
            'expiry_date': self.expiry_date,
            'created_at': self.created_at
        }
        db[f"licenses:{self.business_id}"] = json.dumps(license_data)
    
    def is_active(self):
        if self.status != 'active':
            return False
        if self.expiry_date:
            expiry = datetime.fromisoformat(self.expiry_date)
            return datetime.now() < expiry
        return False

class Payment:
    def __init__(self, business_id, mpesa_code, phone_number, amount=3000, status='pending', payment_id=None):
        self.payment_id = payment_id or str(uuid.uuid4())
        self.business_id = business_id
        self.mpesa_code = mpesa_code
        self.phone_number = phone_number
        self.amount = float(amount)
        self.status = status  # 'pending', 'confirmed', 'rejected'
        self.created_at = datetime.now().isoformat()
    
    @staticmethod
    def get_all(business_id):
        payments_data = db.get(f"payments:{business_id}")
        if payments_data:
            payments_list = json.loads(payments_data)
            return [Payment(
                business_id=p['business_id'],
                mpesa_code=p['mpesa_code'],
                phone_number=p['phone_number'],
                amount=p['amount'],
                status=p['status'],
                payment_id=p['payment_id']
            ) for p in payments_list]
        return []
    
    @staticmethod
    def save_all(business_id, payments):
        payments_data = []
        for payment in payments:
            payments_data.append({
                'payment_id': payment.payment_id,
                'business_id': payment.business_id,
                'mpesa_code': payment.mpesa_code,
                'phone_number': payment.phone_number,
                'amount': payment.amount,
                'status': payment.status,
                'created_at': payment.created_at
            })
        db[f"payments:{business_id}"] = json.dumps(payments_data)

class Settings:
    def __init__(self, business_id, business_name=None, logo_url=None, paybill=None, footer_text=None):
        self.business_id = business_id
        self.business_name = business_name
        self.logo_url = logo_url
        self.paybill = paybill
        self.footer_text = footer_text or "Thank you for your business!"
    
    @staticmethod
    def get(business_id):
        settings_data = db.get(f"settings:{business_id}")
        if settings_data:
            data = json.loads(settings_data)
            return Settings(
                business_id=data['business_id'],
                business_name=data.get('business_name'),
                logo_url=data.get('logo_url'),
                paybill=data.get('paybill'),
                footer_text=data.get('footer_text')
            )
        return Settings(business_id)
    
    def save(self):
        settings_data = {
            'business_id': self.business_id,
            'business_name': self.business_name,
            'logo_url': self.logo_url,
            'paybill': self.paybill,
            'footer_text': self.footer_text
        }
        db[f"settings:{self.business_id}"] = json.dumps(settings_data)
