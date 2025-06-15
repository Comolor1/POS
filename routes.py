from flask import render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import json
import uuid

from app import app, db
from models import User, Product, Sale, License, Payment, Settings
from models_extended import Customer, Expense, BusinessUser, GlobalSettings, AuditLog
from auth import check_license_required, role_required, superadmin_required, check_business_blocked
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
            if email == 'admin@comolor.com' or user.role == 'superadmin':
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
    if not settings:
        settings = Settings(current_user.business_id, business_name=current_user.business_name)
        settings.save()
    
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
                if user:
                    user.password_hash = generate_password_hash(new_password)
                    user.save()
                    flash('Password changed successfully!', 'success')
        
        return redirect(url_for('settings'))
    
    # Get license info
    license_obj = License.get(current_user.business_id)
    
    return render_template('settings.html', settings=settings, license=license_obj)

@app.route('/admin')
def admin_panel():
    if not current_user.is_authenticated or (current_user.email != 'admin@comolor.com' and current_user.role != 'superadmin'):
        flash('Access denied. Superadmin only.', 'error')
        return redirect(url_for('login'))
    
    return redirect(url_for('admin_dashboard'))

# Old admin_dashboard function removed to avoid conflicts

@app.route('/admin/confirm-payment', methods=['POST'])
@login_required
def confirm_payment():
    if current_user.email != 'admin@comolor.com' and current_user.role != 'superadmin':
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

@app.route('/customers', methods=['GET', 'POST'])
@login_required
@check_license_required
@role_required(['admin', 'manager'])
def customers():
    from models_extended import Customer
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add':
            name = request.form['name'].strip()
            email = request.form.get('email', '').strip()
            phone = request.form.get('phone', '').strip()
            address = request.form.get('address', '').strip()
            
            customer = Customer(
                business_id=current_user.business_id,
                name=name,
                email=email if email else None,
                phone=phone if phone else None,
                address=address if address else None
            )
            customer.save()
            
            flash('Customer added successfully!', 'success')
    
    customers = Customer.get_all(current_user.business_id)
    
    return render_template('customers.html', customers=customers)

@app.route('/expenses', methods=['GET', 'POST'])
@login_required
@check_license_required
@role_required(['admin', 'manager'])
def expenses():
    from models_extended import Expense
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add':
            category = request.form['category'].strip()
            description = request.form['description'].strip()
            amount = float(request.form['amount'])
            expense_date = request.form.get('expense_date')
            
            # Parse date
            if expense_date:
                expense_date = datetime.strptime(expense_date, '%Y-%m-%d').date()
            
            expense = Expense(
                business_id=current_user.business_id,
                category=category,
                description=description,
                amount=amount,
                date=expense_date
            )
            expense.save()
            
            flash('Expense added successfully!', 'success')
    
    expenses = Expense.get_all(current_user.business_id)
    
    # Calculate totals by category
    category_totals = {}
    for expense in expenses:
        if expense.category not in category_totals:
            category_totals[expense.category] = 0
        category_totals[expense.category] += float(expense.amount)
    
    total_expenses = sum(float(e.amount) for e in expenses)
    
    return render_template('expenses.html', 
                         expenses=expenses, 
                         category_totals=category_totals,
                         total_expenses=total_expenses)

@app.route('/users', methods=['GET', 'POST'])
@login_required
@check_license_required
@role_required(['admin'])
def users():
    from models_extended import BusinessUser
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add':
            name = request.form['name'].strip()
            email = request.form['email'].lower().strip()
            password = request.form['password']
            role = request.form['role']
            
            # Check if user already exists
            if BusinessUser.get_by_email(email):
                flash('Email already exists. Please choose a different email.', 'error')
            else:
                password_hash = generate_password_hash(password)
                user = BusinessUser(
                    business_id=current_user.business_id,
                    name=name,
                    email=email,
                    password_hash=password_hash,
                    role=role
                )
                user.save()
                flash('User added successfully!', 'success')
        
        elif action == 'deactivate':
            user_id = request.form['user_id']
            users = BusinessUser.get_all(current_user.business_id)
            for user in users:
                if user.user_id == user_id:
                    user.deactivate()
                    flash('User deactivated successfully!', 'success')
                    break
    
    business_users = BusinessUser.get_all(current_user.business_id)
    
    return render_template('users.html', users=business_users)

# ========== SUPERADMIN ROUTES ==========

@app.route('/admin')
@superadmin_required
def superadmin_dashboard():
    """Main superadmin dashboard"""
    # Get all businesses with their license info
    businesses = get_all_businesses()
    
    # Get payment statistics
    all_payments = get_all_payments()
    pending_payments = [p for p in all_payments if p.status == 'pending']
    confirmed_payments = [p for p in all_payments if p.status == 'confirmed']
    
    # Calculate statistics
    active_licenses = 0
    expired_licenses = 0
    blocked_businesses = 0
    
    for business in businesses:
        if business.is_blocked:
            blocked_businesses += 1
        
        license_obj = License.get(business.business_id)
        if license_obj and license_obj.is_active():
            active_licenses += 1
        else:
            expired_licenses += 1
    
    total_revenue = calculate_total_revenue()
    
    # Get global settings
    global_settings = GlobalSettings.get()
    
    # Get recent audit logs
    recent_logs = AuditLog.get_all(limit=10)
    
    stats = {
        'total_businesses': len(businesses),
        'active_licenses': active_licenses,
        'expired_licenses': expired_licenses,
        'blocked_businesses': blocked_businesses,
        'pending_payments': len(pending_payments),
        'confirmed_payments': len(confirmed_payments),
        'total_revenue': total_revenue
    }
    
    return render_template('admin_dashboard.html', 
                         businesses=businesses,
                         payments=all_payments,
                         stats=stats,
                         global_settings=global_settings,
                         recent_logs=recent_logs)

@app.route('/admin/businesses')
@superadmin_required
def admin_businesses():
    """View and manage all businesses"""
    businesses = get_all_businesses()
    
    # Add license info to each business
    for business in businesses:
        license_obj = License.get(business.business_id)
        business.license_status = 'Active' if license_obj and license_obj.is_active() else 'Expired'
        business.license_expiry = license_obj.expiry_date if license_obj else None
    
    return render_template('admin_businesses.html', businesses=businesses)

@app.route('/admin/business/<business_id>/toggle-block', methods=['POST'])
@superadmin_required
def toggle_business_block(business_id):
    """Block or unblock a business"""
    user = User.query.filter_by(business_id=business_id).first()
    if user:
        user.is_blocked = not user.is_blocked
        db.session.commit()
        
        action = 'blocked' if user.is_blocked else 'unblocked'
        
        # Log the action
        log = AuditLog(
            admin_email=current_user.email,
            action=f'Business {action}',
            target_business_id=business_id,
            details=f'Business "{user.business_name}" was {action}'
        )
        log.save()
        
        flash(f'Business {action} successfully!', 'success')
    else:
        flash('Business not found.', 'error')
    
    return redirect(url_for('admin_businesses'))

@app.route('/admin/payments')
@superadmin_required
def admin_payments():
    """View all payments and process them"""
    all_payments = get_all_payments()
    
    # Group payments by status
    pending_payments = [p for p in all_payments if p.status == 'pending']
    confirmed_payments = [p for p in all_payments if p.status == 'confirmed']
    rejected_payments = [p for p in all_payments if p.status == 'rejected']
    
    return render_template('admin_payments.html',
                         pending_payments=pending_payments,
                         confirmed_payments=confirmed_payments,
                         rejected_payments=rejected_payments)

@app.route('/admin/payment/<payment_id>/process', methods=['POST'])
@superadmin_required
def process_payment(payment_id):
    """Confirm or reject a payment"""
    action = request.form['action']  # 'confirm' or 'reject'
    
    # Find the payment across all businesses
    all_payments = get_all_payments()
    payment_found = None
    target_business_id = None
    
    for payment in all_payments:
        if payment.payment_id == payment_id:
            payment_found = payment
            target_business_id = payment.business_id
            break
    
    if payment_found:
        # Update payment status
        payments = Payment.get_all(target_business_id)
        for payment in payments:
            if payment.payment_id == payment_id:
                payment.status = 'confirmed' if action == 'confirm' else 'rejected'
                break
        
        Payment.save_all(target_business_id, payments)
        
        # If confirmed, update license
        if action == 'confirm':
            license_obj = License.get(target_business_id)
            if not license_obj:
                license_obj = License(target_business_id)
            
            license_obj.status = 'active'
            license_obj.expiry_date = datetime.now() + timedelta(days=30)
            license_obj.save()
        
        # Log the action
        user = User.query.filter_by(business_id=target_business_id).first()
        business_name = user.business_name if user else 'Unknown'
        
        log = AuditLog(
            admin_email=current_user.email,
            action=f'Payment {action}ed',
            target_business_id=target_business_id,
            details=f'Payment {payment_id} for "{business_name}" was {action}ed. Amount: KES {payment_found.amount}'
        )
        log.save()
        
        flash(f'Payment {action}ed successfully!', 'success')
    else:
        flash('Payment not found.', 'error')
    
    return redirect(url_for('admin_payments'))

@app.route('/admin/settings', methods=['GET', 'POST'])
@superadmin_required
def admin_settings():
    """Manage global system settings"""
    global_settings = GlobalSettings.get()
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'update_pricing':
            new_price = float(request.form['license_price'])
            old_price = float(global_settings.license_price)
            global_settings.license_price = new_price
            global_settings.save()
            
            # Log the change
            log = AuditLog(
                admin_email=current_user.email,
                action='License price updated',
                details=f'License price changed from KES {old_price} to KES {new_price}'
            )
            log.save()
            
            flash('License price updated successfully!', 'success')
            
        elif action == 'update_till':
            new_till = request.form['till_number'].strip()
            old_till = global_settings.till_number
            global_settings.till_number = new_till
            global_settings.save()
            
            # Log the change
            log = AuditLog(
                admin_email=current_user.email,
                action='Till number updated',
                details=f'Till number changed from {old_till} to {new_till}'
            )
            log.save()
            
            flash('Till number updated successfully!', 'success')
            
        elif action == 'update_terms':
            new_terms = request.form['terms_content']
            global_settings.terms_content = new_terms
            global_settings.save()
            
            # Log the change
            log = AuditLog(
                admin_email=current_user.email,
                action='Terms & Conditions updated',
                details='Terms and conditions content was updated'
            )
            log.save()
            
            flash('Terms & Conditions updated successfully!', 'success')
    
    return render_template('admin_settings.html', global_settings=global_settings)

@app.route('/admin/reports')
@superadmin_required
def admin_reports():
    """View comprehensive system reports"""
    # Get all businesses and their data
    businesses = get_all_businesses()
    all_payments = get_all_payments()
    
    # Calculate monthly revenue for the last 12 months
    monthly_revenue = {}
    for i in range(12):
        month_date = datetime.now() - timedelta(days=30*i)
        month_key = month_date.strftime('%Y-%m')
        monthly_revenue[month_key] = 0
    
    for payment in all_payments:
        if payment.status == 'confirmed':
            payment_month = payment.created_at.strftime('%Y-%m')
            if payment_month in monthly_revenue:
                monthly_revenue[payment_month] += float(payment.amount)
    
    # Business registration trends
    registration_trends = {}
    for business in businesses:
        reg_month = business.created_at.strftime('%Y-%m')
        if reg_month not in registration_trends:
            registration_trends[reg_month] = 0
        registration_trends[reg_month] += 1
    
    # License status distribution
    license_stats = {'active': 0, 'expired': 0, 'pending': 0}
    for business in businesses:
        license_obj = License.get(business.business_id)
        if license_obj:
            if license_obj.is_active():
                license_stats['active'] += 1
            else:
                license_stats['expired'] += 1
        else:
            license_stats['pending'] += 1
    
    total_revenue = calculate_total_revenue()
    
    return render_template('admin_reports.html',
                         businesses=businesses,
                         monthly_revenue=monthly_revenue,
                         registration_trends=registration_trends,
                         license_stats=license_stats,
                         total_revenue=total_revenue)

@app.route('/admin/audit-logs')
@superadmin_required
def admin_audit_logs():
    """View system audit logs"""
    page = request.args.get('page', 1, type=int)
    per_page = 50
    
    logs = AuditLog.query.order_by(AuditLog.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('admin_audit_logs.html', logs=logs)

@app.route('/admin/export-businesses')
@superadmin_required
def export_businesses():
    """Export business data as CSV"""
    import csv
    from io import StringIO
    from flask import make_response
    
    businesses = get_all_businesses()
    
    output = StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['Business Name', 'Email', 'Phone', 'Business ID', 'Created Date', 'License Status', 'Is Blocked'])
    
    # Write data
    for business in businesses:
        license_obj = License.get(business.business_id)
        license_status = 'Active' if license_obj and license_obj.is_active() else 'Expired'
        
        writer.writerow([
            business.business_name,
            business.email,
            business.phone,
            business.business_id,
            business.created_at.strftime('%Y-%m-%d'),
            license_status,
            'Yes' if business.is_blocked else 'No'
        ])
    
    output.seek(0)
    
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename=businesses_{datetime.now().strftime("%Y%m%d")}.csv'
    
    # Log the export
    log = AuditLog(
        admin_email=current_user.email,
        action='Business data exported',
        details=f'Exported data for {len(businesses)} businesses'
    )
    log.save()
    
    return response

@app.route('/admin/business/<business_id>/details')
@superadmin_required
def business_details(business_id):
    """View detailed information about a specific business"""
    user = User.query.filter_by(business_id=business_id).first_or_404()
    license_obj = License.get(business_id)
    payments = Payment.get_all(business_id)
    
    # Get business metrics
    products = Product.get_all(business_id)
    sales = Sale.get_all(business_id)
    
    # Calculate basic stats
    total_sales = sum(float(sale.total) for sale in sales)
    total_products = len(products)
    
    business_data = {
        'user': user,
        'license': license_obj,
        'payments': payments,
        'total_sales': total_sales,
        'total_products': total_products,
        'sales_count': len(sales)
    }
    
    return render_template('admin_business_details.html', business=business_data)
