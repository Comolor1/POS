from datetime import datetime, timedelta
from app import db
from models import User, Payment
from models_extended import GlobalSettings

def get_all_businesses():
    """Get all businesses for superadmin panel"""
    return User.query.all()

def get_all_payments():
    """Get all payments across all businesses"""
    return Payment.query.all()

def calculate_total_revenue():
    """Calculate total revenue from confirmed payments"""
    confirmed_payments = Payment.query.filter_by(status='confirmed').all()
    return sum(payment.amount for payment in confirmed_payments)

def format_currency(amount):
    """Format amount as Kenyan Shilling"""
    return f"KES {amount:,.2f}"

def get_date_range_filter(start_date=None, end_date=None):
    """Get date range for filtering reports"""
    if not start_date:
        start_date = datetime.now().replace(day=1).date()  # First day of current month
    if not end_date:
        end_date = datetime.now().date()
    
    return start_date, end_date

def calculate_daily_sales(sales, target_date=None):
    """Calculate sales for a specific date"""
    if not target_date:
        target_date = datetime.now().date()
    
    daily_sales = []
    total_amount = 0
    
    for sale in sales:
        # Handle both datetime objects and string dates
        if isinstance(sale.created_at, datetime):
            sale_date = sale.created_at.date()
        else:
            sale_date = datetime.fromisoformat(str(sale.created_at)).date()
        
        if sale_date == target_date:
            daily_sales.append(sale)
            total_amount += float(sale.total)
    
    return daily_sales, total_amount

def calculate_monthly_sales(sales, year=None, month=None):
    """Calculate sales for a specific month"""
    if not year:
        year = datetime.now().year
    if not month:
        month = datetime.now().month
    
    monthly_sales = []
    total_amount = 0
    
    for sale in sales:
        # Handle both datetime objects and string dates
        if isinstance(sale.created_at, datetime):
            sale_date = sale.created_at
        else:
            sale_date = datetime.fromisoformat(str(sale.created_at))
        
        if sale_date.year == year and sale_date.month == month:
            monthly_sales.append(sale)
            total_amount += float(sale.total)
    
    return monthly_sales, total_amount
