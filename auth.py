from flask import request, redirect, url_for, flash
from flask_login import current_user
from functools import wraps
from models import License
from app import login_manager, app
from models import User

@login_manager.user_loader
def load_user(user_id):
    try:
        # Convert user_id back to integer and query by id
        return User.query.get(int(user_id))
    except (ValueError, TypeError):
        return None

def check_license_required(f):
    """Decorator to check if user has active license"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.is_authenticated:
            # Skip license check for superadmin
            if current_user.email == 'admin@comolor.com' or current_user.role == 'superadmin':
                return f(*args, **kwargs)
            
            # Skip license check if already on pay_license page to prevent redirect loop
            if request.endpoint == 'pay_license':
                return f(*args, **kwargs)
            
            # Check license status
            license_obj = License.get(current_user.business_id)
            if not license_obj or not license_obj.is_active():
                flash('Your license has expired. Renew to access system.', 'error')
                return redirect(url_for('pay_license'))
        
        return f(*args, **kwargs)
    return decorated_function

def role_required(roles):
    """Decorator to check user role"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('login'))
            
            if isinstance(roles, str):
                allowed_roles = [roles]
            else:
                allowed_roles = roles
            
            if current_user.role not in allowed_roles:
                flash('You do not have permission to access this page.', 'error')
                return redirect(url_for('dashboard'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def superadmin_required(f):
    """Decorator to check if user is superadmin"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login'))
        
        # Only allow hardcoded superadmin account
        if current_user.email != 'admin@comolor.com':
            flash('Access denied. Superadmin privileges required.', 'error')
            return redirect(url_for('dashboard'))
        
        return f(*args, **kwargs)
    return decorated_function

def check_business_blocked(f):
    """Decorator to check if business is blocked"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.is_authenticated and current_user.email != 'admin@comolor.com':
            if current_user.is_blocked:
                flash('Your business account has been suspended. Contact support.', 'error')
                return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function
