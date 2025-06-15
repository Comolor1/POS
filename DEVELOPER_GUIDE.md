# Comolor POS - Complete Developer Guide

## Table of Contents
1. [System Architecture](#system-architecture)
2. [Installation & Setup](#installation--setup)
3. [Database Configuration](#database-configuration)
4. [Authentication System](#authentication-system)
5. [Role-Based Access Control](#role-based-access-control)
6. [API Development](#api-development)
7. [Testing](#testing)
8. [Deployment](#deployment)

## System Architecture

### Technology Stack
- **Backend**: Python Flask
- **Database**: PostgreSQL
- **Authentication**: Flask-Login
- **ORM**: SQLAlchemy
- **Frontend**: HTML5, CSS3, Bootstrap 5, JavaScript
- **Payment**: M-PESA Integration
- **Server**: Gunicorn WSGI

### Project Structure
```
comolor-pos/
├── app.py                 # Flask application factory
├── main.py               # Application entry point
├── models.py             # Database models
├── routes.py             # Route handlers
├── auth.py               # Authentication decorators
├── utils.py              # Utility functions
├── static/
│   ├── css/             # Stylesheets
│   ├── js/              # JavaScript files
│   └── img/             # Images
├── templates/           # Jinja2 templates
└── migrations/          # Database migrations
```

## Installation & Setup

### Prerequisites
- Python 3.11+
- PostgreSQL database
- Git

### Environment Setup
1. Clone the repository
2. Install dependencies:
```bash
pip install flask flask-sqlalchemy flask-migrate flask-login
pip install psycopg2-binary gunicorn werkzeug
```

3. Set environment variables:
```bash
export DATABASE_URL="postgresql://user:password@localhost/comolor_pos"
export SESSION_SECRET="your-secret-key-here"
```

### Database Initialization
```bash
# Initialize migration repository
flask db init

# Create initial migration
flask db migrate -m "Initial migration"

# Apply migrations
flask db upgrade
```

## Database Configuration

### Models Overview

#### User Model
```python
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    business_name = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default='admin')
    business_id = db.Column(db.String(36), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
```

#### Product Model
```python
class Product(db.Model):
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.String(36), unique=True, nullable=False)
    business_id = db.Column(db.String(36), db.ForeignKey('users.business_id'))
    name = db.Column(db.String(200), nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    category = db.Column(db.String(100))
    stock_quantity = db.Column(db.Integer, default=0)
```

### Database Operations
```python
# Create new product
product = Product(
    business_id=current_user.business_id,
    name="Product Name",
    price=10.99,
    category="Electronics",
    stock_quantity=50
)
db.session.add(product)
db.session.commit()

# Query products
products = Product.query.filter_by(business_id=business_id).all()

# Update product
product = Product.query.filter_by(product_id=product_id).first()
product.price = 15.99
db.session.commit()
```

## Authentication System

### User Registration
```python
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        business_name = request.form['business_name']
        phone = request.form['phone']
        
        # Check if user exists
        if User.get(email):
            flash('Email already registered')
            return redirect(url_for('register'))
        
        # Create new user
        password_hash = generate_password_hash(password)
        user = User(email, business_name, phone, password_hash)
        user.save()
        
        return redirect(url_for('login'))
    
    return render_template('register.html')
```

### Login Process
```python
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        user = User.get(email)
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        
        flash('Invalid credentials')
    
    return render_template('login.html')
```

## Role-Based Access Control

### Role Hierarchy
1. **Superadmin**: System-wide access, manages all businesses
2. **Admin**: Business owner, full business access
3. **Manager**: Product management, POS access, reports
4. **Cashier**: POS access only

### Access Control Decorators
```python
def role_required(roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('login'))
            
            if current_user.role not in roles:
                abort(403)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Usage
@app.route('/admin/panel')
@login_required
@role_required(['superadmin'])
def admin_panel():
    return render_template('admin_panel.html')
```

### License Check Decorator
```python
def check_license_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.role == 'superadmin':
            return f(*args, **kwargs)
        
        license_info = License.get(current_user.business_id)
        if not license_info or not license_info.is_active():
            return redirect(url_for('pay_license'))
        
        return f(*args, **kwargs)
    return decorated_function
```

## API Development

### POS Sale Processing
```python
@app.route('/process_sale', methods=['POST'])
@login_required
@role_required(['admin', 'manager', 'cashier'])
@check_license_required
def process_sale():
    data = request.get_json()
    
    # Validate cart items
    cart_items = data.get('items', [])
    if not cart_items:
        return jsonify({'success': False, 'message': 'Cart is empty'})
    
    # Calculate total
    total = sum(item['price'] * item['quantity'] for item in cart_items)
    
    # Create sale record
    sale = Sale(
        business_id=current_user.business_id,
        items=cart_items,
        total=total,
        payment_method=data.get('payment_method', 'cash'),
        mpesa_ref=data.get('mpesa_ref'),
        customer_name=data.get('customer_name')
    )
    
    # Update stock quantities
    for item in cart_items:
        product = Product.query.filter_by(
            product_id=item['product_id'],
            business_id=current_user.business_id
        ).first()
        
        if product:
            product.stock_quantity -= item['quantity']
    
    db.session.add(sale)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'sale_id': sale.sale_id,
        'receipt_url': url_for('receipt', sale_id=sale.sale_id)
    })
```

### Product Management API
```python
@app.route('/api/products', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'manager'])
def api_products():
    if request.method == 'POST':
        data = request.get_json()
        
        product = Product(
            business_id=current_user.business_id,
            name=data['name'],
            price=data['price'],
            category=data.get('category', ''),
            stock_quantity=data.get('stock_quantity', 0)
        )
        
        db.session.add(product)
        db.session.commit()
        
        return jsonify({'success': True, 'product_id': product.product_id})
    
    # GET request
    products = Product.query.filter_by(business_id=current_user.business_id).all()
    return jsonify([{
        'product_id': p.product_id,
        'name': p.name,
        'price': float(p.price),
        'category': p.category,
        'stock_quantity': p.stock_quantity
    } for p in products])
```

## Testing

### Unit Tests Example
```python
import unittest
from app import app, db
from models import User, Product

class TestPOSSystem(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app = app.test_client()
        
        with app.app_context():
            db.create_all()
    
    def tearDown(self):
        with app.app_context():
            db.drop_all()
    
    def test_user_registration(self):
        response = self.app.post('/register', data={
            'email': 'test@example.com',
            'password': 'password123',
            'business_name': 'Test Business',
            'phone': '0700000000'
        })
        self.assertEqual(response.status_code, 302)
    
    def test_product_creation(self):
        # Login first
        with app.app_context():
            user = User('test@example.com', 'Test Business', '0700000000', 'hash')
            db.session.add(user)
            db.session.commit()
        
        # Test product creation
        with self.app.session_transaction() as sess:
            sess['user_id'] = 'test@example.com'
        
        response = self.app.post('/api/products', 
            json={
                'name': 'Test Product',
                'price': 10.99,
                'category': 'Test',
                'stock_quantity': 100
            },
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)

if __name__ == '__main__':
    unittest.main()
```

### Manual Testing Checklist
- [ ] User registration with valid/invalid data
- [ ] Login with correct/incorrect credentials
- [ ] Role-based access control
- [ ] Product CRUD operations
- [ ] POS sale processing
- [ ] Receipt generation
- [ ] License payment flow
- [ ] Admin panel functionality

## Deployment

### Production Configuration
```python
# config.py
import os

class ProductionConfig:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }
```

### Gunicorn Configuration
```bash
# gunicorn.conf.py
bind = "0.0.0.0:5000"
workers = 4
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2
max_requests = 1000
max_requests_jitter = 100
```

### Docker Deployment
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["gunicorn", "--config", "gunicorn.conf.py", "main:app"]
```

### Environment Variables for Production
```bash
export SECRET_KEY="your-production-secret-key"
export DATABASE_URL="postgresql://user:password@host:port/database"
export FLASK_ENV="production"
export MPESA_CONSUMER_KEY="your-mpesa-consumer-key"
export MPESA_CONSUMER_SECRET="your-mpesa-consumer-secret"
```

## Development Best Practices

### Code Style
- Follow PEP 8 guidelines
- Use meaningful variable names
- Add docstrings to functions
- Keep functions small and focused

### Security
- Always validate user input
- Use parameterized queries
- Implement proper error handling
- Log security events

### Performance
- Use database indexes
- Implement pagination for large datasets
- Cache frequently accessed data
- Optimize database queries

### Error Handling
```python
@app.errorhandler(404)
def not_found(error):
    return render_template('error.html', error='Page not found'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('error.html', error='Internal server error'), 500
```

This guide provides comprehensive coverage of the Comolor POS system development. For specific implementation details, refer to the actual code files in the project.