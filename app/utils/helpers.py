"""
Helper utility functions for the NL2SQL system
"""

import re
import logging
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse
import sqlparse
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)


def format_sql(sql_query: str) -> str:
    """
    Format SQL query for better readability
    
    Args:
        sql_query: Raw SQL query
        
    Returns:
        str: Formatted SQL query
    """
    try:
        # Parse and format using sqlparse
        parsed = sqlparse.parse(sql_query)
        formatted = sqlparse.format(
            sql_query,
            reindent=True,
            keyword_case='upper',
            indent_width=2,
            use_space_around_operators=True
        )
        return formatted
    except Exception as e:
        logger.warning(f"Error formatting SQL: {e}")
        return sql_query


def validate_database_url(database_url: str) -> Tuple[bool, str]:
    """
    Validate database connection URL
    
    Args:
        database_url: Database connection URL
        
    Returns:
        Tuple[bool, str]: (is_valid, error_message)
    """
    try:
        # Parse URL
        parsed = urlparse(database_url)
        
        # Check if it's a PostgreSQL URL
        if parsed.scheme not in ['postgresql', 'postgres']:
            return False, "Only PostgreSQL URLs are supported"
        
        # Check if host and database are provided
        if not parsed.hostname:
            return False, "Hostname is required"
        
        if not parsed.path or parsed.path == '/':
            return False, "Database name is required"
        
        # Test connection
        engine = create_engine(database_url)
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        
        return True, "Valid database URL"
        
    except SQLAlchemyError as e:
        return False, f"Database connection failed: {str(e)}"
    except Exception as e:
        return False, f"Invalid URL format: {str(e)}"


def create_sample_database(database_url: str) -> bool:
    """
    Create a sample database with example tables and data
    
    Args:
        database_url: Database connection URL
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        engine = create_engine(database_url)
        
        # Sample schema
        schema_sql = """
        -- Create users table
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            first_name VARCHAR(50),
            last_name VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE
        );
        
        -- Create categories table
        CREATE TABLE IF NOT EXISTS categories (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Create products table
        CREATE TABLE IF NOT EXISTS products (
            id SERIAL PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            description TEXT,
            price DECIMAL(10,2) NOT NULL,
            category_id INTEGER REFERENCES categories(id),
            stock_quantity INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Create orders table
        CREATE TABLE IF NOT EXISTS orders (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            order_total DECIMAL(10,2) NOT NULL,
            status VARCHAR(20) DEFAULT 'pending'
        );
        
        -- Create order_items table
        CREATE TABLE IF NOT EXISTS order_items (
            id SERIAL PRIMARY KEY,
            order_id INTEGER REFERENCES orders(id),
            product_id INTEGER REFERENCES products(id),
            quantity INTEGER NOT NULL,
            unit_price DECIMAL(10,2) NOT NULL
        );
        """
        
        # Sample data
        sample_data_sql = """
        -- Insert sample users
        INSERT INTO users (username, email, first_name, last_name) VALUES
        ('john_doe', 'john@example.com', 'John', 'Doe'),
        ('jane_smith', 'jane@example.com', 'Jane', 'Smith'),
        ('bob_wilson', 'bob@example.com', 'Bob', 'Wilson'),
        ('alice_brown', 'alice@example.com', 'Alice', 'Brown'),
        ('charlie_davis', 'charlie@example.com', 'Charlie', 'Davis')
        ON CONFLICT (username) DO NOTHING;
        
        -- Insert sample categories
        INSERT INTO categories (name, description) VALUES
        ('Electronics', 'Electronic devices and accessories'),
        ('Clothing', 'Apparel and fashion items'),
        ('Books', 'Books and publications'),
        ('Home & Garden', 'Home improvement and garden items'),
        ('Sports', 'Sports equipment and accessories')
        ON CONFLICT (id) DO NOTHING;
        
        -- Insert sample products
        INSERT INTO products (name, description, price, category_id, stock_quantity) VALUES
        ('Laptop', 'High-performance laptop', 999.99, 1, 50),
        ('Smartphone', 'Latest smartphone model', 699.99, 1, 100),
        ('T-Shirt', 'Cotton t-shirt', 19.99, 2, 200),
        ('Jeans', 'Blue denim jeans', 49.99, 2, 150),
        ('Programming Book', 'Learn Python programming', 29.99, 3, 75),
        ('Garden Tool Set', 'Complete garden tool set', 89.99, 4, 30),
        ('Basketball', 'Professional basketball', 24.99, 5, 60)
        ON CONFLICT (id) DO NOTHING;
        
        -- Insert sample orders
        INSERT INTO orders (user_id, order_total, status) VALUES
        (1, 1019.98, 'completed'),
        (2, 69.98, 'completed'),
        (3, 119.98, 'pending'),
        (4, 89.99, 'completed'),
        (5, 24.99, 'shipped')
        ON CONFLICT (id) DO NOTHING;
        
        -- Insert sample order items
        INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES
        (1, 1, 1, 999.99),
        (1, 3, 1, 19.99),
        (2, 3, 2, 19.99),
        (2, 4, 1, 49.99),
        (3, 5, 2, 29.99),
        (3, 6, 1, 89.99),
        (4, 6, 1, 89.99),
        (5, 7, 1, 24.99)
        ON CONFLICT (id) DO NOTHING;
        """
        
        with engine.connect() as connection:
            # Execute schema creation
            for statement in schema_sql.split(';'):
                if statement.strip():
                    connection.execute(text(statement))
            
            # Execute sample data insertion
            for statement in sample_data_sql.split(';'):
                if statement.strip():
                    connection.execute(text(statement))
            
            connection.commit()
        
        logger.info("Sample database created successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error creating sample database: {e}")
        return False


def extract_tables_from_sql(sql_query: str) -> List[str]:
    """
    Extract table names from SQL query
    
    Args:
        sql_query: SQL query to analyze
        
    Returns:
        List[str]: List of table names
    """
    try:
        parsed = sqlparse.parse(sql_query)
        tables = []
        
        for statement in parsed:
            for token in statement.tokens:
                if token.ttype is sqlparse.tokens.Name:
                    tables.append(token.value)
        
        return list(set(tables))
    except Exception as e:
        logger.error(f"Error extracting tables: {e}")
        return []


def extract_columns_from_sql(sql_query: str) -> List[str]:
    """
    Extract column names from SQL query
    
    Args:
        sql_query: SQL query to analyze
        
    Returns:
        List[str]: List of column names
    """
    try:
        parsed = sqlparse.parse(sql_query)
        columns = []
        
        for statement in parsed:
            for token in statement.tokens:
                if hasattr(token, 'tokens'):
                    for subtoken in token.tokens:
                        if subtoken.ttype is sqlparse.tokens.Name:
                            columns.append(subtoken.value)
        
        return list(set(columns))
    except Exception as e:
        logger.error(f"Error extracting columns: {e}")
        return []


def sanitize_sql_input(user_input: str) -> str:
    """
    Sanitize user input to prevent SQL injection
    
    Args:
        user_input: User input string
        
    Returns:
        str: Sanitized input
    """
    # Remove potentially dangerous characters
    dangerous_chars = [';', '--', '/*', '*/', 'xp_', 'sp_']
    
    sanitized = user_input
    for char in dangerous_chars:
        sanitized = sanitized.replace(char, '')
    
    # Remove extra whitespace
    sanitized = re.sub(r'\s+', ' ', sanitized).strip()
    
    return sanitized


def generate_query_summary(sql_query: str, results: List[Dict]) -> Dict:
    """
    Generate a summary of query results
    
    Args:
        sql_query: SQL query that was executed
        results: Query results
        
    Returns:
        Dict: Query summary
    """
    summary = {
        'query_type': 'unknown',
        'row_count': len(results),
        'column_count': 0,
        'columns': [],
        'has_aggregation': False,
        'has_joins': False,
        'has_where': False,
        'has_order_by': False,
        'has_group_by': False
    }
    
    if results:
        summary['column_count'] = len(results[0])
        summary['columns'] = list(results[0].keys())
    
    # Analyze query structure
    sql_upper = sql_query.upper()
    summary['has_aggregation'] = any(
        keyword in sql_upper for keyword in ['COUNT(', 'SUM(', 'AVG(', 'MAX(', 'MIN(']
    )
    summary['has_joins'] = 'JOIN' in sql_upper
    summary['has_where'] = 'WHERE' in sql_upper
    summary['has_order_by'] = 'ORDER BY' in sql_upper
    summary['has_group_by'] = 'GROUP BY' in sql_upper
    
    return summary


def format_results_for_display(results: List[Dict], max_rows: int = 100) -> Dict:
    """
    Format query results for display
    
    Args:
        results: Query results
        max_rows: Maximum number of rows to display
        
    Returns:
        Dict: Formatted results
    """
    if not results:
        return {
            'data': [],
            'total_rows': 0,
            'displayed_rows': 0,
            'columns': [],
            'truncated': False
        }
    
    # Limit results for display
    truncated = len(results) > max_rows
    display_data = results[:max_rows]
    
    return {
        'data': display_data,
        'total_rows': len(results),
        'displayed_rows': len(display_data),
        'columns': list(results[0].keys()) if results else [],
        'truncated': truncated
    }


def validate_natural_language_query(query: str) -> Tuple[bool, str]:
    """
    Validate natural language query
    
    Args:
        query: Natural language query
        
    Returns:
        Tuple[bool, str]: (is_valid, error_message)
    """
    if not query or not query.strip():
        return False, "Query cannot be empty"
    
    if len(query.strip()) < 3:
        return False, "Query is too short"
    
    if len(query) > 1000:
        return False, "Query is too long (max 1000 characters)"
    
    # Check for SQL keywords that might indicate user is trying to write SQL
    sql_keywords = ['SELECT', 'FROM', 'WHERE', 'JOIN', 'GROUP BY', 'ORDER BY']
    query_upper = query.upper()
    
    for keyword in sql_keywords:
        if keyword in query_upper:
            return False, f"Query contains SQL keyword '{keyword}'. Please use natural language."
    
    return True, "Valid query"
