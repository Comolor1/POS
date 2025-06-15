from datetime import datetime, timedelta
from flask_login import UserMixin
from app import db
import uuid
import json

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    business_name = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='admin')
    business_id = db.Column(db.String(36), nullable=False, unique=True, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    products = db.relationship('Product', backref='business_owner', lazy=True, cascade='all, delete-orphan')
    sales = db.relationship('Sale', backref='business_owner', lazy=True, cascade='all, delete-orphan')
    payments = db.relationship('Payment', backref='business_owner', lazy=True, cascade='all, delete-orphan')
    license_info = db.relationship('License', backref='business_owner', lazy=True, uselist=False, cascade='all, delete-orphan')
    settings = db.relationship('Settings', backref='business_owner', lazy=True, uselist=False, cascade='all, delete-orphan')
    
    def __init__(self, email, business_name, phone, password_hash, role='admin', business_id=None):
        self.email = email
        self.business_name = business_name
        self.phone = phone
        self.password_hash = password_hash
        self.role = role
        self.business_id = business_id or str(uuid.uuid4())
    
    def update_password(self, new_password_hash):
        self.password_hash = new_password_hash
        db.session.commit()
    
    def update_business_info(self, business_name=None, phone=None):
        if business_name:
            self.business_name = business_name
        if phone:
            self.phone = phone
        db.session.commit()
    
    def get_id(self):
        return self.email
    
    @staticmethod
    def get(email):
        return User.query.filter_by(email=email).first()
    
    def save(self):
        existing_user = User.query.filter_by(email=self.email).first()
        if not existing_user:
            db.session.add(self)
        else:
            # Update existing user
            existing_user.business_name = self.business_name
            existing_user.phone = self.phone
            existing_user.password_hash = self.password_hash
            existing_user.role = self.role
        db.session.commit()

class Product(db.Model):
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.String(36), nullable=False, unique=True, index=True)
    business_id = db.Column(db.String(36), db.ForeignKey('users.business_id'), nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    category = db.Column(db.String(100))
    stock_quantity = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    def __init__(self, business_id, name, price, category, stock_quantity=0, product_id=None):
        self.product_id = product_id or str(uuid.uuid4())
        self.business_id = business_id
        self.name = name
        self.price = float(price)
        self.category = category
        self.stock_quantity = int(stock_quantity)
    
    @staticmethod
    def get_all(business_id):
        return Product.query.filter_by(business_id=business_id).all()
    
    @staticmethod
    def save_all(business_id, products):
        for product in products:
            existing = Product.query.filter_by(product_id=product.product_id).first()
            if existing:
                existing.name = product.name
                existing.price = product.price
                existing.category = product.category
                existing.stock_quantity = product.stock_quantity
            else:
                db.session.add(product)
        db.session.commit()

class Sale(db.Model):
    __tablename__ = 'sales'
    
    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.String(36), nullable=False, unique=True, index=True)
    business_id = db.Column(db.String(36), db.ForeignKey('users.business_id'), nullable=False, index=True)
    items = db.Column(db.Text, nullable=False)  # JSON string
    total = db.Column(db.Numeric(10, 2), nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)
    mpesa_ref = db.Column(db.String(100))
    customer_name = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    def __init__(self, business_id, items, total, payment_method, mpesa_ref=None, customer_name=None, sale_id=None):
        self.sale_id = sale_id or str(uuid.uuid4())
        self.business_id = business_id
        self.items = json.dumps(items) if isinstance(items, (list, dict)) else items
        self.total = float(total)
        self.payment_method = payment_method
        self.mpesa_ref = mpesa_ref
        self.customer_name = customer_name
    
    @property
    def items_list(self):
        return json.loads(self.items) if self.items else []
    
    @staticmethod
    def get_all(business_id):
        return Sale.query.filter_by(business_id=business_id).all()
    
    @staticmethod
    def save_all(business_id, sales):
        for sale in sales:
            existing = Sale.query.filter_by(sale_id=sale.sale_id).first()
            if not existing:
                db.session.add(sale)
        db.session.commit()

class License(db.Model):
    __tablename__ = 'licenses'
    
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.String(36), db.ForeignKey('users.business_id'), nullable=False, unique=True, index=True)
    status = db.Column(db.String(20), nullable=False, default='pending')
    expiry_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    def __init__(self, business_id, status='pending', expiry_date=None):
        self.business_id = business_id
        self.status = status
        self.expiry_date = expiry_date
    
    @staticmethod
    def get(business_id):
        return License.query.filter_by(business_id=business_id).first()
    
    def save(self):
        existing = License.query.filter_by(business_id=self.business_id).first()
        if existing:
            existing.status = self.status
            existing.expiry_date = self.expiry_date
        else:
            db.session.add(self)
        db.session.commit()
    
    def is_active(self):
        if self.status != 'active':
            return False
        if self.expiry_date and datetime.utcnow() > self.expiry_date:
            return False
        return True

class Payment(db.Model):
    __tablename__ = 'payments'
    
    id = db.Column(db.Integer, primary_key=True)
    payment_id = db.Column(db.String(36), nullable=False, unique=True, index=True)
    business_id = db.Column(db.String(36), db.ForeignKey('users.business_id'), nullable=False, index=True)
    mpesa_code = db.Column(db.String(100), nullable=False)
    phone_number = db.Column(db.String(20), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False, default=3000)
    status = db.Column(db.String(20), nullable=False, default='pending')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    def __init__(self, business_id, mpesa_code, phone_number, amount=3000, status='pending', payment_id=None):
        self.payment_id = payment_id or str(uuid.uuid4())
        self.business_id = business_id
        self.mpesa_code = mpesa_code
        self.phone_number = phone_number
        self.amount = float(amount)
        self.status = status
    
    @staticmethod
    def get_all(business_id):
        return Payment.query.filter_by(business_id=business_id).all()
    
    @staticmethod
    def save_all(business_id, payments):
        for payment in payments:
            existing = Payment.query.filter_by(payment_id=payment.payment_id).first()
            if not existing:
                db.session.add(payment)
        db.session.commit()

class Settings(db.Model):
    __tablename__ = 'settings'
    
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.String(36), db.ForeignKey('users.business_id'), nullable=False, unique=True, index=True)
    business_name = db.Column(db.String(200))
    logo_url = db.Column(db.String(500))
    paybill = db.Column(db.String(20))
    footer_text = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    def __init__(self, business_id, business_name=None, logo_url=None, paybill=None, footer_text=None):
        self.business_id = business_id
        self.business_name = business_name
        self.logo_url = logo_url
        self.paybill = paybill
        self.footer_text = footer_text
    
    @staticmethod
    def get(business_id):
        return Settings.query.filter_by(business_id=business_id).first()
    
    def save(self):
        existing = Settings.query.filter_by(business_id=self.business_id).first()
        if existing:
            existing.business_name = self.business_name
            existing.logo_url = self.logo_url
            existing.paybill = self.paybill
            existing.footer_text = self.footer_text
        else:
            db.session.add(self)
        db.session.commit()