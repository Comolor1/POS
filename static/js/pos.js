// Comolor POS - Point of Sale JavaScript

// Cart Management
let cart = [];
let cartTotal = 0;

// Initialize POS when page loads
document.addEventListener('DOMContentLoaded', function() {
    initializePOS();
});

function initializePOS() {
    updateCartDisplay();
    setupEventListeners();
    console.log('POS system initialized');
}

function setupEventListeners() {
    // Payment method change listeners
    const paymentRadios = document.querySelectorAll('input[name="payment_method"]');
    paymentRadios.forEach(radio => {
        radio.addEventListener('change', handlePaymentMethodChange);
    });
    
    // Customer name input
    const customerNameInput = document.getElementById('customer-name');
    if (customerNameInput) {
        customerNameInput.addEventListener('input', debounce(updateCartSummary, 300));
    }
}

function handlePaymentMethodChange(event) {
    const mpesaSection = document.getElementById('mpesa-ref-section');
    if (event.target.value === 'mpesa') {
        mpesaSection.style.display = 'block';
        document.getElementById('mpesa-ref').required = true;
    } else {
        mpesaSection.style.display = 'none';
        document.getElementById('mpesa-ref').required = false;
    }
}

// Add product to cart
function addToCart(productId, productName, productPrice, stockQuantity) {
    // Check if product is out of stock
    if (stockQuantity <= 0) {
        showNotification('Product is out of stock!', 'error');
        return;
    }
    
    // Check if item already exists in cart
    const existingItemIndex = cart.findIndex(item => item.product_id === productId);
    
    if (existingItemIndex > -1) {
        // Check if we can add more (stock limit)
        if (cart[existingItemIndex].quantity >= stockQuantity) {
            showNotification(`Cannot add more. Only ${stockQuantity} in stock.`, 'warning');
            return;
        }
        
        // Increment quantity
        cart[existingItemIndex].quantity += 1;
        showNotification(`${productName} quantity updated`, 'success');
    } else {
        // Add new item to cart
        const cartItem = {
            product_id: productId,
            name: productName,
            price: parseFloat(productPrice),
            quantity: 1,
            stock_quantity: stockQuantity
        };
        
        cart.push(cartItem);
        showNotification(`${productName} added to cart`, 'success');
    }
    
    updateCartDisplay();
    
    // Add visual feedback to product card
    addProductClickFeedback(productId);
}

function addProductClickFeedback(productId) {
    const productCards = document.querySelectorAll('.product-card');
    productCards.forEach(card => {
        if (card.onclick && card.onclick.toString().includes(productId)) {
            card.classList.add('animate__animated', 'animate__pulse');
            setTimeout(() => {
                card.classList.remove('animate__animated', 'animate__pulse');
            }, 600);
        }
    });
}

// Remove item from cart
function removeFromCart(productId) {
    const itemIndex = cart.findIndex(item => item.product_id === productId);
    if (itemIndex > -1) {
        const itemName = cart[itemIndex].name;
        cart.splice(itemIndex, 1);
        updateCartDisplay();
        showNotification(`${itemName} removed from cart`, 'info');
    }
}

// Update item quantity in cart
function updateQuantity(productId, change) {
    const itemIndex = cart.findIndex(item => item.product_id === productId);
    if (itemIndex > -1) {
        const item = cart[itemIndex];
        const newQuantity = item.quantity + change;
        
        if (newQuantity <= 0) {
            removeFromCart(productId);
            return;
        }
        
        if (newQuantity > item.stock_quantity) {
            showNotification(`Cannot exceed stock limit of ${item.stock_quantity}`, 'warning');
            return;
        }
        
        item.quantity = newQuantity;
        updateCartDisplay();
    }
}

// Clear entire cart
function clearCart() {
    if (cart.length === 0) {
        showNotification('Cart is already empty', 'info');
        return;
    }
    
    if (confirm('Are you sure you want to clear the cart?')) {
        cart = [];
        updateCartDisplay();
        showNotification('Cart cleared', 'info');
    }
}

// Update cart display
function updateCartDisplay() {
    const cartItemsContainer = document.getElementById('cart-items');
    const cartCountElement = document.getElementById('cart-count');
    const cartTotalSection = document.getElementById('cart-total-section');
    const emptyCartElement = document.getElementById('empty-cart');
    
    // Update cart count
    cartCountElement.textContent = cart.length;
    
    if (cart.length === 0) {
        // Show empty cart message
        emptyCartElement.style.display = 'block';
        cartTotalSection.style.display = 'none';
        cartItemsContainer.innerHTML = '<div class="text-center text-muted py-4" id="empty-cart"><i class="fas fa-shopping-cart fa-2x mb-3"></i><p>Cart is empty</p><small>Click on products to add them to cart</small></div>';
        return;
    }
    
    // Hide empty cart message and show cart total section
    emptyCartElement.style.display = 'none';
    cartTotalSection.style.display = 'block';
    
    // Calculate total
    cartTotal = cart.reduce((total, item) => total + (item.price * item.quantity), 0);
    
    // Build cart items HTML
    let cartHTML = '';
    cart.forEach(item => {
        const itemTotal = item.price * item.quantity;
        cartHTML += `
            <div class="cart-item" data-product-id="${item.product_id}">
                <div class="d-flex justify-content-between align-items-start mb-2">
                    <div class="flex-grow-1">
                        <h6 class="mb-1">${item.name}</h6>
                        <small class="text-muted">${formatCurrency(item.price)} each</small>
                    </div>
                    <button class="btn btn-sm btn-outline-danger" onclick="removeFromCart('${item.product_id}')" title="Remove item">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div class="d-flex justify-content-between align-items-center">
                    <div class="quantity-controls">
                        <button class="quantity-btn" onclick="updateQuantity('${item.product_id}', -1)" title="Decrease quantity">
                            <i class="fas fa-minus"></i>
                        </button>
                        <span class="mx-2 fw-bold">${item.quantity}</span>
                        <button class="quantity-btn" onclick="updateQuantity('${item.product_id}', 1)" title="Increase quantity">
                            <i class="fas fa-plus"></i>
                        </button>
                    </div>
                    <div class="fw-bold text-success">
                        ${formatCurrency(itemTotal)}
                    </div>
                </div>
                ${item.quantity >= item.stock_quantity ? '<small class="text-warning"><i class="fas fa-exclamation-triangle"></i> Max stock reached</small>' : ''}
            </div>
        `;
    });
    
    cartItemsContainer.innerHTML = cartHTML;
    
    // Update totals
    document.getElementById('cart-subtotal').textContent = formatCurrency(cartTotal);
    document.getElementById('cart-total').textContent = formatCurrency(cartTotal);
}

// Process sale
function processSale() {
    if (cart.length === 0) {
        showNotification('Cannot process empty cart', 'error');
        return;
    }
    
    // Get form values
    const paymentMethod = document.querySelector('input[name="payment_method"]:checked')?.value;
    const mpesaRef = document.getElementById('mpesa-ref')?.value?.trim();
    const customerName = document.getElementById('customer-name')?.value?.trim();
    
    // Validation
    if (!paymentMethod) {
        showNotification('Please select a payment method', 'error');
        return;
    }
    
    if (paymentMethod === 'mpesa' && !mpesaRef) {
        showNotification('Please enter M-PESA reference code', 'error');
        document.getElementById('mpesa-ref').focus();
        return;
    }
    
    // Confirm sale
    const confirmMessage = `Process sale of ${formatCurrency(cartTotal)}?`;
    if (!confirm(confirmMessage)) {
        return;
    }
    
    // Prepare form data
    document.getElementById('form-cart-items').value = JSON.stringify(cart);
    document.getElementById('form-payment-method').value = paymentMethod;
    document.getElementById('form-mpesa-ref').value = mpesaRef || '';
    document.getElementById('form-customer-name').value = customerName || '';
    
    // Show processing state
    const processButton = event.target;
    const originalText = processButton.innerHTML;
    processButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
    processButton.disabled = true;
    
    // Submit form
    setTimeout(() => {
        document.getElementById('sale-form').submit();
    }, 500);
}

// Category filtering
function filterByCategory(category) {
    const items = document.querySelectorAll('.product-item');
    const buttons = document.querySelectorAll('.category-filter');
    
    // Update active button
    buttons.forEach(btn => btn.classList.remove('active'));
    event.target.classList.add('active');
    
    // Filter items with animation
    items.forEach((item, index) => {
        setTimeout(() => {
            if (category === 'all' || item.dataset.category === category) {
                item.style.display = 'block';
                item.classList.add('fade-in');
            } else {
                item.style.display = 'none';
                item.classList.remove('fade-in');
            }
        }, index * 50); // Stagger animation
    });
}

// Format currency
function formatCurrency(amount) {
    return `KES ${parseFloat(amount).toLocaleString('en-KE', { 
        minimumFractionDigits: 2, 
        maximumFractionDigits: 2 
    })}`;
}

// Show notification
function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `alert alert-${getBootstrapAlertClass(type)} alert-dismissible fade show position-fixed`;
    notification.style.cssText = `
        top: 20px;
        right: 20px;
        z-index: 9999;
        min-width: 300px;
        box-shadow: 0 0.5rem 1rem rgba(0, 0, 0, 0.15);
    `;
    
    notification.innerHTML = `
        <i class="fas ${getNotificationIcon(type)} me-2"></i>
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    // Add to page
    document.body.appendChild(notification);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.classList.remove('show');
            setTimeout(() => {
                notification.remove();
            }, 150);
        }
    }, 5000);
}

function getBootstrapAlertClass(type) {
    const classes = {
        'success': 'success',
        'error': 'danger',
        'warning': 'warning',
        'info': 'info'
    };
    return classes[type] || 'info';
}

function getNotificationIcon(type) {
    const icons = {
        'success': 'fa-check-circle',
        'error': 'fa-exclamation-circle',
        'warning': 'fa-exclamation-triangle',
        'info': 'fa-info-circle'
    };
    return icons[type] || 'fa-info-circle';
}

// Debounce function for performance
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Update cart summary (used for customer name changes)
function updateCartSummary() {
    // This function can be extended to recalculate taxes, discounts, etc.
    // For now, it's a placeholder for future enhancements
    console.log('Cart summary updated');
}

// Keyboard shortcuts
document.addEventListener('keydown', function(event) {
    // Escape key to clear cart (with confirmation)
    if (event.key === 'Escape') {
        if (cart.length > 0) {
            clearCart();
        }
    }
    
    // Enter key to process sale (when cart has items)
    if (event.key === 'Enter' && event.ctrlKey) {
        if (cart.length > 0) {
            processSale();
        }
    }
    
    // F1 key for help (future enhancement)
    if (event.key === 'F1') {
        event.preventDefault();
        showNotification('Keyboard shortcuts: ESC=Clear Cart, Ctrl+Enter=Process Sale', 'info');
    }
});

// Handle page unload (warn if cart has items)
window.addEventListener('beforeunload', function(event) {
    if (cart.length > 0) {
        const message = 'You have items in your cart. Are you sure you want to leave?';
        event.returnValue = message;
        return message;
    }
});

// Product search functionality (for future enhancement)
function searchProducts(query) {
    const products = document.querySelectorAll('.product-item');
    const searchTerm = query.toLowerCase();
    
    products.forEach(product => {
        const productName = product.querySelector('.card-title')?.textContent?.toLowerCase() || '';
        const productCategory = product.dataset.category?.toLowerCase() || '';
        
        if (productName.includes(searchTerm) || productCategory.includes(searchTerm)) {
            product.style.display = 'block';
        } else {
            product.style.display = 'none';
        }
    });
}

// Export functions for external use
window.POS = {
    addToCart,
    removeFromCart,
    updateQuantity,
    clearCart,
    processSale,
    filterByCategory,
    searchProducts,
    formatCurrency,
    showNotification,
    getCart: () => cart,
    getCartTotal: () => cartTotal
};

console.log('Comolor POS JavaScript loaded successfully');
