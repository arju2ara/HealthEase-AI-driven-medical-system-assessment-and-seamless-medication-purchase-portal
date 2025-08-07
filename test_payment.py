#!/usr/bin/env python3
"""
Test script to debug payment processing
"""

import requests
import json

def test_sslcommerz_connection():
    """Test SSLCommerz API connection"""
    try:
        # Test data
        test_data = {
            'store_id': 'testbox',
            'store_passwd': 'qwerty',
            'total_amount': 100.00,
            'currency': 'BDT',
            'tran_id': 'TEST_123456',
            'product_category': 'medicine',
            'cus_name': 'Test User',
            'cus_email': 'test@example.com',
            'cus_add1': 'Test Address',
            'cus_city': 'Dhaka',
            'cus_postcode': '1000',
            'cus_country': 'Bangladesh',
            'cus_phone': '01712345678',
            'ship_name': 'Test User',
            'ship_add1': 'Test Address',
            'ship_city': 'Dhaka',
            'ship_postcode': '1000',
            'ship_country': 'Bangladesh',
            'success_url': 'http://127.0.0.1:5000/payment/success',
            'fail_url': 'http://127.0.0.1:5000/payment/fail',
            'cancel_url': 'http://127.0.0.1:5000/payment/cancel',
            'ipn_url': 'http://127.0.0.1:5000/payment/ipn',
            'multi_card_name': '',
            'num_of_item': 1,
            'product_name': 'Test Medicine',
            'product_category': 'medicine',
            'product_profile': 'general',
            'shipping_method': 'NO',
            'product_amount': 100.00,
            'vat': '0',
            'discount_amount': '0',
            'convenience_fee': '0'
        }
        
        # Make API request to SSLCommerz
        response = requests.post(
            'https://sandbox.sslcommerz.com/gwprocess/v4/api.php',
            data=test_data,
            timeout=30
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"JSON Response: {json.dumps(result, indent=2)}")
            
            if result.get('status') == 'VALID':
                print("✅ SSLCommerz connection successful!")
                return True
            else:
                print(f"❌ SSLCommerz error: {result.get('failedreason', 'Unknown error')}")
                return False
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        return False

if __name__ == "__main__":
    print("Testing SSLCommerz connection...")
    test_sslcommerz_connection() 