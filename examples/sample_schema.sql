-- Sample Database Schema for NL2SQL System
-- This schema provides a comprehensive example for testing the NL2SQL system

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    first_name VARCHAR(50),
    last_name VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    last_login TIMESTAMP,
    profile_picture_url VARCHAR(255)
);

-- Create categories table
CREATE TABLE IF NOT EXISTS categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    parent_category_id INTEGER REFERENCES categories(id),
    is_active BOOLEAN DEFAULT TRUE
);

-- Create products table
CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    price DECIMAL(10,2) NOT NULL,
    category_id INTEGER REFERENCES categories(id),
    stock_quantity INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sku VARCHAR(50) UNIQUE,
    weight DECIMAL(8,2),
    dimensions VARCHAR(50)
);

-- Create orders table
CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    order_total DECIMAL(10,2) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    shipping_address TEXT,
    billing_address TEXT,
    payment_method VARCHAR(50),
    tracking_number VARCHAR(100)
);

-- Create order_items table
CREATE TABLE IF NOT EXISTS order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES orders(id),
    product_id INTEGER REFERENCES products(id),
    quantity INTEGER NOT NULL,
    unit_price DECIMAL(10,2) NOT NULL,
    discount_amount DECIMAL(10,2) DEFAULT 0
);

-- Create reviews table
CREATE TABLE IF NOT EXISTS reviews (
    id SERIAL PRIMARY KEY,
    product_id INTEGER REFERENCES products(id),
    user_id INTEGER REFERENCES users(id),
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_verified_purchase BOOLEAN DEFAULT FALSE
);

-- Create inventory table
CREATE TABLE IF NOT EXISTS inventory (
    id SERIAL PRIMARY KEY,
    product_id INTEGER REFERENCES products(id),
    warehouse_id INTEGER,
    quantity INTEGER NOT NULL,
    reserved_quantity INTEGER DEFAULT 0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create promotions table
CREATE TABLE IF NOT EXISTS promotions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    discount_percentage DECIMAL(5,2),
    discount_amount DECIMAL(10,2),
    start_date DATE,
    end_date DATE,
    is_active BOOLEAN DEFAULT TRUE,
    minimum_order_amount DECIMAL(10,2)
);

-- Create order_promotions table (many-to-many relationship)
CREATE TABLE IF NOT EXISTS order_promotions (
    order_id INTEGER REFERENCES orders(id),
    promotion_id INTEGER REFERENCES promotions(id),
    discount_applied DECIMAL(10,2),
    PRIMARY KEY (order_id, promotion_id)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at);
CREATE INDEX IF NOT EXISTS idx_products_category_id ON products(category_id);
CREATE INDEX IF NOT EXISTS idx_products_price ON products(price);
CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id);
CREATE INDEX IF NOT EXISTS idx_orders_order_date ON orders(order_date);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_order_items_product_id ON order_items(product_id);
CREATE INDEX IF NOT EXISTS idx_reviews_product_id ON reviews(product_id);
CREATE INDEX IF NOT EXISTS idx_reviews_rating ON reviews(rating);

-- Create views for common queries
CREATE OR REPLACE VIEW product_summary AS
SELECT 
    p.id,
    p.name,
    p.price,
    c.name as category_name,
    p.stock_quantity,
    COUNT(r.id) as review_count,
    AVG(r.rating) as average_rating
FROM products p
LEFT JOIN categories c ON p.category_id = c.id
LEFT JOIN reviews r ON p.id = r.product_id
GROUP BY p.id, p.name, p.price, c.name, p.stock_quantity;

CREATE OR REPLACE VIEW user_order_summary AS
SELECT 
    u.id,
    u.username,
    u.email,
    COUNT(o.id) as total_orders,
    SUM(o.order_total) as total_spent,
    AVG(o.order_total) as average_order_value,
    MAX(o.order_date) as last_order_date
FROM users u
LEFT JOIN orders o ON u.id = o.user_id
GROUP BY u.id, u.username, u.email;

-- Sample data insertion
-- Users
INSERT INTO users (username, email, first_name, last_name) VALUES
('john_doe', 'john@example.com', 'John', 'Doe'),
('jane_smith', 'jane@example.com', 'Jane', 'Smith'),
('bob_wilson', 'bob@example.com', 'Bob', 'Wilson'),
('alice_brown', 'alice@example.com', 'Alice', 'Brown'),
('charlie_davis', 'charlie@example.com', 'Charlie', 'Davis'),
('diana_miller', 'diana@example.com', 'Diana', 'Miller'),
('edward_garcia', 'edward@example.com', 'Edward', 'Garcia'),
('fiona_rodriguez', 'fiona@example.com', 'Fiona', 'Rodriguez')
ON CONFLICT (username) DO NOTHING;

-- Categories
INSERT INTO categories (name, description) VALUES
('Electronics', 'Electronic devices and accessories'),
('Clothing', 'Apparel and fashion items'),
('Books', 'Books and publications'),
('Home & Garden', 'Home improvement and garden items'),
('Sports', 'Sports equipment and accessories'),
('Toys & Games', 'Toys and entertainment items'),
('Health & Beauty', 'Health and beauty products'),
('Automotive', 'Automotive parts and accessories')
ON CONFLICT (id) DO NOTHING;

-- Products
INSERT INTO products (name, description, price, category_id, stock_quantity, sku) VALUES
('Laptop Pro', 'High-performance laptop with latest specs', 1299.99, 1, 50, 'LAP001'),
('Smartphone X', 'Latest smartphone with advanced features', 899.99, 1, 100, 'PHN001'),
('Wireless Headphones', 'Noise-cancelling wireless headphones', 199.99, 1, 75, 'AUD001'),
('Cotton T-Shirt', 'Comfortable cotton t-shirt', 24.99, 2, 200, 'TSH001'),
('Denim Jeans', 'Classic blue denim jeans', 59.99, 2, 150, 'JNS001'),
('Programming Book', 'Learn Python programming from scratch', 39.99, 3, 80, 'BOK001'),
('Garden Tool Set', 'Complete garden maintenance tool set', 89.99, 4, 30, 'GRD001'),
('Basketball', 'Professional basketball for indoor/outdoor use', 29.99, 5, 60, 'SPT001'),
('Board Game', 'Family-friendly board game', 34.99, 6, 45, 'TOY001'),
('Face Cream', 'Anti-aging face cream', 49.99, 7, 90, 'BEA001'),
('Car Air Freshener', 'Long-lasting car air freshener', 12.99, 8, 120, 'AUT001')
ON CONFLICT (id) DO NOTHING;

-- Orders
INSERT INTO orders (user_id, order_total, status) VALUES
(1, 1324.98, 'completed'),
(2, 84.98, 'completed'),
(3, 129.98, 'pending'),
(4, 89.99, 'completed'),
(5, 29.99, 'shipped'),
(6, 159.98, 'completed'),
(7, 74.98, 'pending'),
(8, 199.98, 'completed')
ON CONFLICT (id) DO NOTHING;

-- Order Items
INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES
(1, 1, 1, 1299.99),
(1, 4, 1, 24.99),
(2, 4, 2, 24.99),
(2, 5, 1, 59.99),
(3, 6, 2, 39.99),
(3, 7, 1, 89.99),
(4, 7, 1, 89.99),
(5, 8, 1, 29.99),
(6, 2, 1, 899.99),
(6, 3, 1, 199.99),
(7, 9, 1, 34.99),
(7, 10, 1, 49.99),
(8, 11, 1, 12.99),
(8, 1, 1, 1299.99)
ON CONFLICT (id) DO NOTHING;

-- Reviews
INSERT INTO reviews (product_id, user_id, rating, comment, is_verified_purchase) VALUES
(1, 1, 5, 'Excellent laptop, very fast!', TRUE),
(1, 8, 4, 'Great performance, good value', TRUE),
(2, 6, 5, 'Amazing camera quality', TRUE),
(3, 6, 4, 'Good sound quality, comfortable', TRUE),
(4, 2, 5, 'Perfect fit and very comfortable', TRUE),
(4, 1, 4, 'Good quality cotton', TRUE),
(5, 2, 3, 'Decent jeans, runs a bit small', TRUE),
(6, 3, 5, 'Excellent book for beginners', TRUE),
(7, 4, 4, 'Good quality tools', TRUE),
(8, 5, 5, 'Perfect for outdoor games', TRUE)
ON CONFLICT (id) DO NOTHING;

-- Promotions
INSERT INTO promotions (name, description, discount_percentage, start_date, end_date, minimum_order_amount) VALUES
('Summer Sale', '20% off on all electronics', 20.00, '2024-06-01', '2024-08-31', 100.00),
('New Customer Discount', '10% off for new customers', 10.00, '2024-01-01', '2024-12-31', 50.00),
('Bulk Purchase', '15% off on orders over $200', 15.00, '2024-01-01', '2024-12-31', 200.00)
ON CONFLICT (id) DO NOTHING;
