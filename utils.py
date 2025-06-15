from datetime import datetime, timedelta
import json
from replit import db

def get_all_businesses():
    """Get all businesses for superadmin panel"""
    businesses = []
    keys = list(db.keys())
    
    for key in keys:
        if key.startswith('business:'):
            business_data = json.loads(db[key])
            businesses.append(business_data)
    
    return businesses

def get_all_payments():
    """Get all payments across all businesses"""
    all_payments = []
    keys = list(db.keys())
    
    for key in keys:
        if key.startswith('payments:'):
            payments_data = json.loads(db[key])
            all_payments.extend(payments_data)
    
    return all_payments

def calculate_total_revenue():
    """Calculate total revenue from confirmed payments"""
    all_payments = get_all_payments()
    total = sum(payment['amount'] for payment in all_payments if payment['status'] == 'confirmed')
    return total

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
        sale_date = datetime.fromisoformat(sale.created_at).date()
        if sale_date == target_date:
            daily_sales.append(sale)
            total_amount += sale.total
    
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
        sale_date = datetime.fromisoformat(sale.created_at)
        if sale_date.year == year and sale_date.month == month:
            monthly_sales.append(sale)
            total_amount += sale.total
    
    return monthly_sales, total_amount
