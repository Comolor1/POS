from datetime import datetime
from app import db
import uuid
import json

class Customer(db.Model):
    __tablename__ = 'customers'
    
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.String(36), nullable=False, unique=True, index=True)
    business_id = db.Column(db.String(36), db.ForeignKey('users.business_id'), nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    def __init__(self, business_id, name, email=None, phone=None, address=None, customer_id=None):
        self.customer_id = customer_id or str(uuid.uuid4())
        self.business_id = business_id
        self.name = name
        self.email = email
        self.phone = phone
        self.address = address
    
    @staticmethod
    def get_all(business_id):
        return Customer.query.filter_by(business_id=business_id).all()
    
    def save(self):
        existing = Customer.query.filter_by(customer_id=self.customer_id).first()
        if not existing:
            db.session.add(self)
        db.session.commit()

class Expense(db.Model):
    __tablename__ = 'expenses'
    
    id = db.Column(db.Integer, primary_key=True)
    expense_id = db.Column(db.String(36), nullable=False, unique=True, index=True)
    business_id = db.Column(db.String(36), db.ForeignKey('users.business_id'), nullable=False, index=True)
    category = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(500), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    receipt_url = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    def __init__(self, business_id, category, description, amount, date=None, receipt_url=None, expense_id=None):
        self.expense_id = expense_id or str(uuid.uuid4())
        self.business_id = business_id
        self.category = category
        self.description = description
        self.amount = float(amount)
        self.date = date or datetime.utcnow().date()
        self.receipt_url = receipt_url
    
    @staticmethod
    def get_all(business_id):
        return Expense.query.filter_by(business_id=business_id).all()
    
    def save(self):
        existing = Expense.query.filter_by(expense_id=self.expense_id).first()
        if not existing:
            db.session.add(self)
        db.session.commit()

class BusinessUser(db.Model):
    __tablename__ = 'business_users'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(36), nullable=False, unique=True, index=True)
    business_id = db.Column(db.String(36), db.ForeignKey('users.business_id'), nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='cashier')  # admin, manager, cashier
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    def __init__(self, business_id, name, email, password_hash, role='cashier', user_id=None):
        self.user_id = user_id or str(uuid.uuid4())
        self.business_id = business_id
        self.name = name
        self.email = email
        self.password_hash = password_hash
        self.role = role
    
    @staticmethod
    def get_all(business_id):
        return BusinessUser.query.filter_by(business_id=business_id).all()
    
    @staticmethod
    def get_by_email(email):
        return BusinessUser.query.filter_by(email=email).first()
    
    def save(self):
        existing = BusinessUser.query.filter_by(email=self.email).first()
        if not existing:
            db.session.add(self)
        db.session.commit()
    
    def deactivate(self):
        self.is_active = False
        db.session.commit()

class GlobalSettings(db.Model):
    __tablename__ = 'global_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    license_price = db.Column(db.Numeric(10, 2), nullable=False, default=3000)
    till_number = db.Column(db.String(20), nullable=False, default='123456')
    terms_content = db.Column(db.Text, nullable=False, default='Default terms and conditions')
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    @staticmethod
    def get():
        settings = GlobalSettings.query.first()
        if not settings:
            settings = GlobalSettings()
            db.session.add(settings)
            db.session.commit()
        return settings
    
    def save(self):
        self.updated_at = datetime.utcnow()
        db.session.commit()

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    admin_email = db.Column(db.String(120), nullable=False)
    action = db.Column(db.String(200), nullable=False)
    target_business_id = db.Column(db.String(36))
    details = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    def __init__(self, admin_email, action, target_business_id=None, details=None):
        self.admin_email = admin_email
        self.action = action
        self.target_business_id = target_business_id
        self.details = details
    
    def save(self):
        db.session.add(self)
        db.session.commit()
    
    @staticmethod
    def get_all(limit=100):
        return AuditLog.query.order_by(AuditLog.created_at.desc()).limit(limit).all()