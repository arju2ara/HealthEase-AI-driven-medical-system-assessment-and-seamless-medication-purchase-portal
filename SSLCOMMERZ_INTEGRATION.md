# SSLCommerz Payment Gateway Integration

This document provides a complete guide for the SSLCommerz payment gateway integration in the HealthEase project.

## Overview

The SSLCommerz integration allows customers to pay for their medicine orders using:
- Credit/Debit Cards
- Mobile Banking (bKash, Nagad, Rocket, etc.)
- Internet Banking
- Cash on Delivery (COD)

## Files Created/Modified

### New Files:
1. `sslcommerz_config.py` - Configuration settings
2. `sslcommerz_payment.py` - Payment handler class
3. `database_update.sql` - Database schema updates
4. `templates/payment_success.html` - Success page
5. `templates/payment_fail.html` - Failure page
6. `templates/pages/payment_management.html` - Admin payment management
7. `SSLCOMMERZ_INTEGRATION.md` - This guide

### Modified Files:
1. `app.py` - Added payment routes and SSLCommerz import
2. `templates/order_product.html` - Added payment method selection
3. `requirements.txt` - Added requests library

## Setup Instructions

### 1. Database Setup
Run the following SQL commands in your MySQL database:

```sql
-- Update orders table to add payment fields
ALTER TABLE orders 
ADD COLUMN payment_status VARCHAR(20) DEFAULT 'pending',
ADD COLUMN payment_method VARCHAR(50) DEFAULT NULL,
ADD COLUMN transaction_id VARCHAR(100) DEFAULT NULL,
ADD COLUMN sslcommerz_tran_id VARCHAR(100) DEFAULT NULL,
ADD COLUMN sslcommerz_val_id VARCHAR(100) DEFAULT NULL,
ADD COLUMN bank_tran_id VARCHAR(100) DEFAULT NULL,
ADD COLUMN payment_date TIMESTAMP NULL;

-- Create payment_logs table to track payment attempts
CREATE TABLE IF NOT EXISTS payment_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT,
    tran_id VARCHAR(100),
    amount DECIMAL(10,2),
    status VARCHAR(20),
    response_data TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders(id)
);
```

### 2. SSLCommerz Account Setup
1. Register at [SSLCommerz Developer Portal](https://developer.sslcommerz.com/)
2. Get your Store ID and Store Password
3. Update `sslcommerz_config.py` with your credentials:

```python
SSLCOMMERZ_STORE_ID = 'your_store_id'
SSLCOMMERZ_STORE_PASSWORD = 'your_store_password'
```

### 3. Environment Configuration
For production, update the URLs in `sslcommerz_config.py`:

```python
# Change from sandbox to live
SSLCOMMERZ_BASE_URL = SSLCOMMERZ_LIVE_URL

# Update URLs to your domain
SSLCOMMERZ_SUCCESS_URL = 'https://yourdomain.com/payment/success'
SSLCOMMERZ_FAIL_URL = 'https://yourdomain.com/payment/fail'
SSLCOMMERZ_CANCEL_URL = 'https://yourdomain.com/payment/cancel'
SSLCOMMERZ_IPN_URL = 'https://yourdomain.com/payment/ipn'
```

## Payment Flow

### 1. Customer Order Process:
1. Customer selects a product
2. Clicks "Order Now"
3. Fills order form with payment method selection
4. Submits form to `/payment/process`
5. System creates order and redirects to SSLCommerz
6. Customer completes payment on SSLCommerz
7. SSLCommerz redirects back to success/fail page

### 2. Payment Methods:
- **SSLCommerz**: Redirects to payment gateway
- **Cash on Delivery**: Marks order as paid immediately

### 3. Payment Status:
- `pending`: Order created, payment not completed
- `paid`: Payment successful
- `failed`: Payment failed

## Admin Features

### Payment Management Dashboard:
- Access via `/payment_management` (admin only)
- View payment statistics
- Monitor all transactions
- Track payment status

### Payment Statistics:
- Total payments
- Successful payments
- Pending payments
- Failed payments

## Testing

### Sandbox Testing:
1. Use test credentials from SSLCommerz
2. Test with sandbox payment methods
3. Verify payment flow end-to-end

### Test Cards (Sandbox):
- Card Number: 4111111111111111
- Expiry: Any future date
- CVV: Any 3 digits

## Security Features

### Hash Verification:
- SSLCommerz sends hash for verification
- System validates hash before processing
- Prevents payment tampering

### IPN (Instant Payment Notification):
- SSLCommerz sends payment status to `/payment/ipn`
- Ensures payment confirmation even if user closes browser
- Logs all payment attempts

## Error Handling

### Common Issues:
1. **Network Errors**: Retry mechanism
2. **Invalid Hash**: Payment rejected
3. **Missing Fields**: Form validation
4. **Database Errors**: Transaction rollback

### Debugging:
- Check payment logs in database
- Monitor SSLCommerz dashboard
- Review application logs

## Production Checklist

- [ ] Update SSLCommerz credentials to live
- [ ] Change URLs to production domain
- [ ] Test all payment methods
- [ ] Configure SSL certificate
- [ ] Set up monitoring
- [ ] Backup payment logs
- [ ] Train admin staff

## Support

For SSLCommerz support:
- Email: support@sslcommerz.com
- Phone: +880 2 988 0315
- Documentation: https://developer.sslcommerz.com/

## API Endpoints

### Customer Endpoints:
- `POST /payment/process` - Process payment
- `GET /payment/success` - Payment success page
- `GET /payment/fail` - Payment failure page
- `GET /payment/cancel` - Payment cancellation

### Admin Endpoints:
- `GET /payment_management` - Payment dashboard
- `POST /payment/ipn` - Instant payment notification

## File Structure

```
├── sslcommerz_config.py          # Configuration
├── sslcommerz_payment.py         # Payment handler
├── database_update.sql           # Database schema
├── templates/
│   ├── payment_success.html     # Success page
│   ├── payment_fail.html        # Failure page
│   └── pages/
│       └── payment_management.html  # Admin dashboard
└── SSLCOMMERZ_INTEGRATION.md    # This guide
```

## Troubleshooting

### Payment Not Processing:
1. Check SSLCommerz credentials
2. Verify network connectivity
3. Check database connection
4. Review application logs

### Payment Success but Order Not Updated:
1. Check IPN URL accessibility
2. Verify hash calculation
3. Check database permissions
4. Review payment logs

### Admin Dashboard Issues:
1. Check admin authentication
2. Verify database queries
3. Check template rendering
4. Review error logs 