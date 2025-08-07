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