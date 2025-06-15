# Comolor POS System

## Overview

Comolor POS is a complete web-based Point of Sale system designed specifically for Kenyan small businesses. The system operates on a monthly licensing model (KES 3,000/month) with M-PESA integration for payments. It provides comprehensive business management features including inventory management, sales processing, receipt printing, reporting, and multi-user access with role-based permissions.

## System Architecture

### Technology Stack
- **Backend**: Python Flask with Gunicorn WSGI server
- **Database**: PostgreSQL with SQLAlchemy ORM and Flask-Migrate
- **Authentication**: Flask-Login with role-based access control
- **Frontend**: HTML5, CSS3, Bootstrap 5, JavaScript
- **Payment Integration**: M-PESA Till number system
- **Deployment**: Replit autoscale with proxy middleware

### Database Architecture
The system uses PostgreSQL as the primary database with the following key design decisions:
- **Multi-tenancy**: Each business is isolated by `business_id` for data security
- **User Management**: Supports multiple user roles (superadmin, admin, manager, cashier)
- **License Tracking**: Integrated license expiry and payment verification system
- **Extensible Models**: Separated core models from extended features for modularity

## Key Components

### Authentication & Authorization
- **Flask-Login**: Session-based authentication with user loader
- **Role-based Access**: Decorators for role verification (`@role_required`)
- **License Verification**: Middleware to check active licenses (`@check_license_required`)
- **Business Isolation**: All data queries filtered by business_id

### Core Business Logic
- **Product Management**: Full CRUD operations with category support
- **Sales Processing**: POS interface with cart functionality and receipt generation
- **Customer Management**: Customer database with purchase history
- **Expense Tracking**: Business expense categorization and reporting
- **Reporting**: Sales analytics with date filtering and chart visualization

### License Management
- **Payment Verification**: Manual admin verification of M-PESA transactions
- **Expiry Tracking**: Automatic license expiration with grace periods
- **Access Control**: System lockout when license expires
- **Renewal Process**: Streamlined payment and verification workflow

## Data Flow

### User Registration Flow
1. User fills registration form with business details
2. Terms & Conditions acceptance required (checkbox validation)
3. Account creation with unique business_id generation
4. Redirect to license payment page
5. System access restricted until license payment verified

### Sales Transaction Flow
1. POS interface loads products for business
2. Cashier adds items to cart with quantity management
3. Payment method selection (cash/M-PESA)
4. Transaction processing with inventory updates
5. Receipt generation and printing capability
6. Sales data storage for reporting

### License Verification Flow
1. Payment made via M-PESA to Till Number 123456
2. User submits transaction code through system
3. Superadmin manually verifies payment
4. License activated for 30-day period
5. Automatic expiry notifications and access restriction

## External Dependencies

### Payment System
- **M-PESA Integration**: Till number 123456 for license payments
- **Manual Verification**: Admin-controlled payment confirmation process
- **No Refund Policy**: Implemented in terms and conditions

### Frontend Libraries
- **Bootstrap 5**: Responsive UI framework
- **Font Awesome**: Icon library for consistent UI elements
- **Chart.js**: Data visualization for reports and analytics

### Python Packages
- **Flask**: Web application framework
- **SQLAlchemy**: Database ORM with relationship management
- **Flask-Migrate**: Database migration management
- **Werkzeug**: Security utilities for password hashing
- **Gunicorn**: Production WSGI server

## Deployment Strategy

### Environment Configuration
- **Database**: PostgreSQL with connection pooling and auto-reconnection
- **Session Management**: Secure session keys with proxy middleware support
- **Port Configuration**: External port 80 mapping to internal port 5000
- **Auto-scaling**: Configured for automatic scaling based on demand

### Production Considerations
- **Security**: Password hashing, session management, role-based access
- **Performance**: Database connection pooling, efficient queries with indexes
- **Reliability**: Health checks, database ping verification, error handling
- **Monitoring**: Logging configuration for debugging and system monitoring

## M-PESA Till Integration

### Business Till Number Configuration
- **Settings Integration**: Businesses can configure their M-PESA Till Number in business settings
- **Till Number Display**: Customer-facing till numbers shown in POS payment modal and receipts
- **Validation**: Till number validation and setup prompts for new businesses

### POS M-PESA Payment Flow
- **Payment Modal**: Interactive M-PESA payment confirmation dialog
- **Customer Details**: Collection of customer name, phone number, and M-PESA receipt code
- **Payment Validation**: Real-time validation of phone numbers and receipt codes
- **Transaction Recording**: Automatic creation of M-PESA transaction records linked to sales

### M-PESA Transaction Management
- **Transaction History**: Dedicated page for viewing all M-PESA transactions
- **Payment Matching**: Automatic linking of M-PESA payments to sales receipts
- **Status Tracking**: Confirmed, pending, and failed transaction status management
- **Receipt Integration**: M-PESA details displayed on printed and digital receipts

### Receipt System Enhancement
- **M-PESA Details**: Receipt code, till number, and customer information on receipts
- **Payment Method Indicators**: Clear distinction between cash and M-PESA payments
- **Customer Information**: Optional customer name display on receipts

## Changelog

```
Changelog:
- June 15, 2025. Initial setup
- June 15, 2025. Fixed redirect loops in authentication system
- June 15, 2025. Added logo upload functionality and receipt preview system
- June 15, 2025. Implemented complete M-PESA till integration with payment processing
```

## User Preferences

```
Preferred communication style: Simple, everyday language.
```