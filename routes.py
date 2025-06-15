from flask import render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import json
import uuid

from app import app
from models import User, Product, Sale, License, Payment, Settings
from auth import check_license_required, role_required
from utils import get_all_businesses, get_all_payments, calculate_total_revenue, format_currency, calculate_daily_sales, calculate_monthly_sales

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].lower().strip()
        password = request.form['password']
        
        user = User.get(email)
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            
            # Check if superadmin
            if email == 'admin@comolor.com':
                return redirect(url_for('admin_panel'))
            
            # Check license for regular users
            license_obj = License.get(user.business_id)
            if not license_obj or not license_obj.is_active():
                flash('Your license has expired. Please renew to access the system.', 'warning')
                return redirect(url_for('pay_license'))
            
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password.', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        business_name = request.form['business_name'].strip()
        email = request.form['email'].lower().strip()
        phone = request.form['phone'].strip()
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        terms_accepted = request.form.get('terms_accepted')
        
        # Validation
        if not terms_accepted:
            flash('You must accept the Terms and Conditions to register.', 'error')
            return render_template('register.html')
        
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('register.html')
        
        if User.get(email):
            flash('Email already exists. Please choose a different email.', 'error')
            return render_template('register.html')
        
        # Create user
        password_hash = generate_password_hash(password)
        user = User(email, business_name, phone, password_hash)
        user.save()
        
        # Create initial license (pending)
        license_obj = License(user.business_id)
        license_obj.save()
        
        # Create initial settings
        settings = Settings(user.business_id, business_name=business_name)
        settings.save()
        
        flash('Registration successful! Please complete payment to activate your license.', 'success')
        login_user(user)
        return redirect(url_for('pay_license'))
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('index'))

@app.route('/terms')
def terms():
    return render_template('terms.html')

@app.route('/pay-license', methods=['GET', 'POST'])
@login_required
def pay_license():
    if current_user.email == 'admin@comolor.com':
        return redirect(url_for('admin_panel'))
    
    if request.method == 'POST':
        mpesa_code = request.form['mpesa_code'].strip().upper()
        phone_number = request.form['phone_number'].strip()
        
        # Get existing payments
        payments = Payment.get_all(current_user.business_id)
        
        # Check if code already exists
        existing_payment = any(p.mpesa_code == mpesa_code for p in payments)
        if existing_payment:
            flash('This M-PESA code has already been submitted.', 'error')
        else:
            # Add new payment
            payment = Payment(current_user.business_id, mpesa_code, phone_number)
            payments.append(payment)
            Payment.save_all(current_user.business_id, payments)
            
            flash('Payment submitted successfully! Awaiting confirmation from admin.', 'success')
    
    # Check current license status
    license_obj = License.get(current_user.business_id)
    payments = Payment.get_all(current_user.business_id)
    
    return render_template('pay_license.html', license=license_obj, payments=payments)

@app.route('/dashboard')
@login_required
@check_license_required
def dashboard():
    if current_user.email == 'admin@comolor.com':
        return redirect(url_for('admin_panel'))
    
    # Get recent sales and basic stats
    sales = Sale.get_all(current_user.business_id)
    products = Product.get_all(current_user.business_id)
    
    # Calculate today's sales
    today_sales, today_total = calculate_daily_sales(sales)
    
    # Calculate this month's sales
    monthly_sales, monthly_total = calculate_monthly_sales(sales)
    
    # Get recent sales (last 5)
    recent_sales = sorted(sales, key=lambda x: x.created_at, reverse=True)[:5]
    
    stats = {
        'total_products': len(products),
        'total_sales': len(sales),
        'today_sales': len(today_sales),
        'today_total': today_total,
        'monthly_total': monthly_total
    }
    
    return render_template('dashboard.html', stats=stats, recent_sales=recent_sales)

@app.route('/products', methods=['GET', 'POST'])
@login_required
@check_license_required
@role_required(['admin', 'manager'])
def products():
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add':
            name = request.form['name'].strip()
            price = float(request.form['price'])
            category = request.form['category'].strip()
            stock_quantity = int(request.form.get('stock_quantity', 0))
            
            products = Product.get_all(current_user.business_id)
            new_product = Product(current_user.business_id, name, price, category, stock_quantity)
            products.append(new_product)
            Product.save_all(current_user.business_id, products)
            
            flash('Product added successfully!', 'success')
        
        elif action == 'edit':
            product_id = request.form['product_id']
            products = Product.get_all(current_user.business_id)
            
            for product in products:
                if product.product_id == product_id:
                    product.name = request.form['name'].strip()
                    product.price = float(request.form['price'])
                    product.category = request.form['category'].strip()
                    product.stock_quantity = int(request.form.get('stock_quantity', 0))
                    break
            
            Product.save_all(current_user.business_id, products)
            flash('Product updated successfully!', 'success')
        
        elif action == 'delete':
            product_id = request.form['product_id']
            products = Product.get_all(current_user.business_id)
            products = [p for p in products if p.product_id != product_id]
            Product.save_all(current_user.business_id, products)
            
            flash('Product deleted successfully!', 'success')
        
        return redirect(url_for('products'))
    
    products = Product.get_all(current_user.business_id)
    categories = list(set(p.category for p in products if p.category))
    
    return render_template('products.html', products=products, categories=categories)

@app.route('/pos')
@login_required
@check_license_required
def pos():
    products = Product.get_all(current_user.business_id)
    categories = list(set(p.category for p in products if p.category))
    
    return render_template('pos.html', products=products, categories=categories)

@app.route('/process-sale', methods=['POST'])
@login_required
@check_license_required
def process_sale():
    cart_items = json.loads(request.form['cart_items'])
    payment_method = request.form['payment_method']
    mpesa_ref = request.form.get('mpesa_ref', '').strip()
    customer_name = request.form.get('customer_name', '').strip()
    
    if not cart_items:
        flash('Cart is empty. Please add items before processing sale.', 'error')
        return redirect(url_for('pos'))
    
    # Calculate total
    total = sum(item['price'] * item['quantity'] for item in cart_items)
    
    # Create sale
    sales = Sale.get_all(current_user.business_id)
    new_sale = Sale(
        current_user.business_id,
        cart_items,
        total,
        payment_method,
        mpesa_ref if payment_method == 'mpesa' else None,
        customer_name if customer_name else None
    )
    sales.append(new_sale)
    Sale.save_all(current_user.business_id, sales)
    
    # Update product stock
    products = Product.get_all(current_user.business_id)
    for item in cart_items:
        for product in products:
            if product.product_id == item['product_id']:
                product.stock_quantity = max(0, product.stock_quantity - item['quantity'])
                break
    Product.save_all(current_user.business_id, products)
    
    flash('Sale processed successfully!', 'success')
    return redirect(url_for('receipt', sale_id=new_sale.sale_id))

@app.route('/receipt/<sale_id>')
@login_required
@check_license_required
def receipt(sale_id):
    sales = Sale.get_all(current_user.business_id)
    sale = next((s for s in sales if s.sale_id == sale_id), None)
    
    if not sale:
        flash('Receipt not found.', 'error')
        return redirect(url_for('pos'))
    
    settings = Settings.get(current_user.business_id)
    return render_template('receipt.html', sale=sale, settings=settings)

@app.route('/reports')
@login_required
@check_license_required
@role_required(['admin', 'manager'])
def reports():
    sales = Sale.get_all(current_user.business_id)
    
    # Filter by date range if provided
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    filtered_sales = sales
    if start_date and end_date:
        start = datetime.strptime(start_date, '%Y-%m-%d').date()
        end = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        filtered_sales = []
        for sale in sales:
            sale_date = datetime.fromisoformat(sale.created_at).date()
            if start <= sale_date <= end:
                filtered_sales.append(sale)
    
    # Calculate totals
    total_sales = len(filtered_sales)
    total_revenue = sum(sale.total for sale in filtered_sales)
    cash_sales = sum(sale.total for sale in filtered_sales if sale.payment_method == 'cash')
    mpesa_sales = sum(sale.total for sale in filtered_sales if sale.payment_method == 'mpesa')
    
    # Group by date
    daily_sales = {}
    for sale in filtered_sales:
        date = datetime.fromisoformat(sale.created_at).date()
        if date not in daily_sales:
            daily_sales[date] = {'count': 0, 'total': 0}
        daily_sales[date]['count'] += 1
        daily_sales[date]['total'] += sale.total
    
    return render_template('reports.html', 
                         sales=filtered_sales,
                         total_sales=total_sales,
                         total_revenue=total_revenue,
                         cash_sales=cash_sales,
                         mpesa_sales=mpesa_sales,
                         daily_sales=daily_sales,
                         start_date=start_date,
                         end_date=end_date)

@app.route('/settings', methods=['GET', 'POST'])
@login_required
@check_license_required
@role_required(['admin'])
def settings():
    settings = Settings.get(current_user.business_id)
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'update_business':
            settings.business_name = request.form['business_name'].strip()
            settings.logo_url = request.form.get('logo_url', '').strip()
            settings.paybill = request.form.get('paybill', '').strip()
            settings.footer_text = request.form.get('footer_text', '').strip()
            settings.save()
            
            flash('Business settings updated successfully!', 'success')
        
        elif action == 'change_password':
            current_password = request.form['current_password']
            new_password = request.form['new_password']
            confirm_password = request.form['confirm_password']
            
            if not check_password_hash(current_user.password_hash, current_password):
                flash('Current password is incorrect.', 'error')
            elif new_password != confirm_password:
                flash('New passwords do not match.', 'error')
            else:
                # Update password
                user = User.get(current_user.email)
                user.password_hash = generate_password_hash(new_password)
                user.save()
                flash('Password changed successfully!', 'success')
        
        return redirect(url_for('settings'))
    
    # Get license info
    license_obj = License.get(current_user.business_id)
    
    return render_template('settings.html', settings=settings, license=license_obj)

@app.route('/admin')
def admin_panel():
    if not current_user.is_authenticated or current_user.email != 'admin@comolor.com':
        flash('Access denied. Superadmin only.', 'error')
        return redirect(url_for('login'))
    
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.email != 'admin@comolor.com':
        flash('Access denied. Superadmin only.', 'error')
        return redirect(url_for('login'))
    
    businesses = get_all_businesses()
    all_payments = get_all_payments()
    total_revenue = calculate_total_revenue()
    
    # Get pending payments
    pending_payments = [p for p in all_payments if p['status'] == 'pending']
    
    # Get license statistics
    active_licenses = 0
    expired_licenses = 0
    
    for business in businesses:
        license_obj = License.get(business['id'])
        if license_obj and license_obj.is_active():
            active_licenses += 1
        else:
            expired_licenses += 1
    
    stats = {
        'total_businesses': len(businesses),
        'active_licenses': active_licenses,
        'expired_licenses': expired_licenses,
        'pending_payments': len(pending_payments),
        'total_revenue': total_revenue
    }
    
    return render_template('admin_panel.html', 
                         businesses=businesses,
                         payments=all_payments,
                         stats=stats)

@app.route('/admin/confirm-payment', methods=['POST'])
@login_required
def confirm_payment():
    if current_user.email != 'admin@comolor.com':
        flash('Access denied.', 'error')
        return redirect(url_for('login'))
    
    payment_id = request.form['payment_id']
    business_id = request.form['business_id']
    action = request.form['action']  # 'confirm' or 'reject'
    
    # Update payment status
    payments = Payment.get_all(business_id)
    for payment in payments:
        if payment.payment_id == payment_id:
            payment.status = 'confirmed' if action == 'confirm' else 'rejected'
            break
    
    Payment.save_all(business_id, payments)
    
    # If confirmed, update license
    if action == 'confirm':
        license_obj = License.get(business_id)
        if not license_obj:
            license_obj = License(business_id)
        
        license_obj.status = 'active'
        license_obj.expiry_date = (datetime.now() + timedelta(days=30)).isoformat()
        license_obj.save()
        
        flash('Payment confirmed and license activated!', 'success')
    else:
        flash('Payment rejected.', 'info')
    
    return redirect(url_for('admin_dashboard'))

# Custom template filters
@app.template_filter('currency')
def currency_filter(amount):
    return format_currency(amount)

@app.template_filter('datetime')
def datetime_filter(date_string):
    if not date_string:
        return ''
    try:
        dt = datetime.fromisoformat(date_string)
        return dt.strftime('%d/%m/%Y %H:%M')
    except:
        return date_string

@app.template_filter('date')
def date_filter(date_string):
    if not date_string:
        return ''
    try:
        dt = datetime.fromisoformat(date_string)
        return dt.strftime('%d/%m/%Y')
    except:
        return date_string
