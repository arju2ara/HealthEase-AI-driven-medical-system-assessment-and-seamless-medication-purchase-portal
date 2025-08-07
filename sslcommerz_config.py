# SSLCommerz Configuration
import os

# SSLCommerz API Configuration
SSLCOMMERZ_STORE_ID = 'testbox'  # Replace with your actual store ID
SSLCOMMERZ_STORE_PASSWORD = 'qwerty'  # Replace with your actual store password

# API URLs
SSLCOMMERZ_SANDBOX_URL = 'https://sandbox.sslcommerz.com'
SSLCOMMERZ_LIVE_URL = 'https://securepay.sslcommerz.com'

# Use sandbox for testing, change to LIVE_URL for production
SSLCOMMERZ_BASE_URL = SSLCOMMERZ_SANDBOX_URL

# Success and Failure URLs
SSLCOMMERZ_SUCCESS_URL = 'http://127.0.0.1:5000/payment/success'
SSLCOMMERZ_FAIL_URL = 'http://127.0.0.1:5000/payment/fail'
SSLCOMMERZ_CANCEL_URL = 'http://127.0.0.1:5000/payment/cancel'
SSLCOMMERZ_IPN_URL = 'http://127.0.0.1:5000/payment/ipn'

# Currency
SSLCOMMERZ_CURRENCY = 'BDT'

# Language
SSLCOMMERZ_LANGUAGE = 'EN' 