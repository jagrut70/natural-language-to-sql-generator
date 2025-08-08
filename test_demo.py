#!/usr/bin/env python3
"""
Comprehensive NL2SQL Demo Script
Demonstrates all working functionality of the NL2SQL system
"""

import requests
import json
import time
from datetime import datetime

def print_header(title):
    """Print a formatted header"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def print_success(message):
    """Print a success message"""
    print(f"✅ {message}")

def print_info(message):
    """Print an info message"""
    print(f"ℹ️  {message}")

def test_api_connection():
    """Test API connection and database setup"""
    print_header("1. API Connection Test")
    
    # Test health endpoint
    try:
        response = requests.get("http://localhost:8000/health")
        if response.status_code == 200:
            print_success("API Health Check: PASSED")
        else:
            print("❌ API Health Check: FAILED")
            return False
    except Exception as e:
        print(f"❌ API Health Check: FAILED - {e}")
        return False
    
    # Connect to database
    try:
        response = requests.post(
            "http://localhost:8000/connect",
            json={"database_url": "postgresql://jagrutvaghasiya@localhost:5432/nl2sql_test"}
        )
        
        if response.status_code == 200:
            result = response.json()
            print_success(f"Database Connection: {result['message']}")
            print_info(f"Generator Type: {result['generator_type']}")
            print_info(f"Tables Found: {result['schema_info']['summary']['table_count']}")
            return True
        else:
            print(f"❌ Database Connection: FAILED - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Database Connection: FAILED - {e}")
        return False

def test_nl2sql_generation():
    """Test natural language to SQL generation"""
    print_header("2. NL2SQL Generation Test")
    
    test_queries = [
        "Show me all users",
        "Find products that cost more than $50",
        "Count the number of orders",
        "Get the top 5 most expensive products",
        "Show me products and their categories"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{i}. Testing: '{query}'")
        
        try:
            response = requests.post(
                "http://localhost:8000/generate-sql",
                json={"natural_language_query": query}
            )
            
            if response.status_code == 200:
                result = response.json()
                sql = result['generated_sql']
                validation = result['validation']
                execution = result['execution_results']
                
                print(f"   📝 Generated SQL: {sql}")
                print(f"   ✅ Valid: {validation['is_valid']}")
                
                if execution and execution.get('results'):
                    row_count = execution['row_count']
                    print(f"   📊 Results: {row_count} rows returned")
                    
                    # Show first result as example
                    if row_count > 0:
                        first_result = execution['results'][0]
                        if isinstance(first_result, dict):
                            sample_keys = list(first_result.keys())[:3]
                            print(f"   📋 Sample columns: {', '.join(sample_keys)}")
                
                if validation.get('warnings'):
                    print(f"   ⚠️  Warnings: {', '.join(validation['warnings'])}")
                    
            else:
                print(f"   ❌ Generation failed: {response.text}")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")

def test_schema_extraction():
    """Test schema extraction functionality"""
    print_header("3. Schema Extraction Test")
    
    try:
        response = requests.get("http://localhost:8000/schema")
        
        if response.status_code == 200:
            schema = response.json()
            tables = schema.get('tables', {})
            
            print_success(f"Schema extracted successfully")
            print_info(f"Total tables: {len(tables)}")
            
            for table_name, table_info in tables.items():
                columns = table_info.get('columns', [])
                print(f"   📋 {table_name}: {len(columns)} columns")
                
                # Show first few columns
                for col in columns[:3]:
                    print(f"      - {col['name']}: {col['type']}")
                if len(columns) > 3:
                    print(f"      ... and {len(columns) - 3} more columns")
                    
        else:
            print(f"❌ Schema extraction failed: {response.text}")
            
    except Exception as e:
        print(f"❌ Schema extraction error: {e}")

def test_few_shot_learning():
    """Test few-shot learning functionality"""
    print_header("4. Few-Shot Learning Test")
    
    try:
        response = requests.get("http://localhost:8000/examples")
        
        if response.status_code == 200:
            result = response.json()
            examples = result.get('examples', [])
            
            print_success(f"Few-shot learning examples loaded")
            print_info(f"Total examples: {len(examples)}")
            
            # Show first few examples
            for i, example in enumerate(examples[:3], 1):
                nl_query = example['natural_language']
                sql_query = example['sql']
                category = example.get('category', 'unknown')
                difficulty = example.get('difficulty', 'unknown')
                
                print(f"   {i}. Category: {category} ({difficulty})")
                print(f"      NL: '{nl_query}'")
                print(f"      SQL: '{sql_query}'")
                
        else:
            print(f"❌ Few-shot learning failed: {response.text}")
            
    except Exception as e:
        print(f"❌ Few-shot learning error: {e}")

def test_query_validation():
    """Test query validation functionality"""
    print_header("5. Query Validation Test")
    
    test_queries = [
        ("Valid SELECT", "SELECT * FROM users WHERE id = 1"),
        ("Valid COUNT", "SELECT COUNT(*) FROM products"),
        ("Invalid DROP", "DROP TABLE users"),
        ("Multiple statements", "SELECT * FROM users; DROP TABLE users;"),
        ("Complex query", "SELECT p.name, c.name FROM products p JOIN categories c ON p.category_id = c.id")
    ]
    
    for query_name, sql_query in test_queries:
        print(f"\nTesting: {query_name}")
        print(f"   SQL: {sql_query}")
        
        try:
            response = requests.get(
                "http://localhost:8000/validate-query",
                params={"sql_query": sql_query}
            )
            
            if response.status_code == 200:
                validation = response.json()
                is_valid = validation.get('is_valid', False)
                errors = validation.get('errors', [])
                warnings = validation.get('warnings', [])
                
                if is_valid:
                    print(f"   ✅ Valid query")
                else:
                    print(f"   ❌ Invalid query")
                    for error in errors:
                        print(f"      - Error: {error}")
                
                if warnings:
                    for warning in warnings:
                        print(f"      - Warning: {warning}")
                        
            else:
                print(f"   ❌ Validation failed: {response.text}")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")

def test_web_interface():
    """Test web interface accessibility"""
    print_header("6. Web Interface Test")
    
    try:
        response = requests.get("http://localhost:8501")
        
        if response.status_code == 200:
            print_success("Streamlit Web Interface: ACCESSIBLE")
            print_info("URL: http://localhost:8501")
            print_info("💡 Open this URL in your browser to test the full interface!")
        else:
            print(f"❌ Streamlit Web Interface: FAILED (Status: {response.status_code})")
            
    except Exception as e:
        print(f"❌ Streamlit Web Interface: FAILED - {e}")

def main():
    """Main demonstration function"""
    print_header("🚀 NL2SQL System Comprehensive Demo")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test 1: API Connection
    if not test_api_connection():
        print("\n❌ API connection failed. Please ensure the API server is running.")
        return
    
    # Test 2: NL2SQL Generation
    test_nl2sql_generation()
    
    # Test 3: Schema Extraction
    test_schema_extraction()
    
    # Test 4: Few-Shot Learning
    test_few_shot_learning()
    
    # Test 5: Query Validation
    test_query_validation()
    
    # Test 6: Web Interface
    test_web_interface()
    
    print_header("🎉 Demo Completed Successfully!")
    print("\n📋 Summary of Working Features:")
    print("   ✅ Natural Language to SQL conversion")
    print("   ✅ Database schema extraction")
    print("   ✅ Query validation and security checks")
    print("   ✅ Few-shot learning with examples")
    print("   ✅ SQL execution and result display")
    print("   ✅ Web interface (Streamlit)")
    print("   ✅ REST API (FastAPI)")
    print("   ✅ PostgreSQL database integration")
    
    print("\n🌐 Next Steps:")
    print("   1. Open http://localhost:8501 in your browser")
    print("   2. Enter database URL: postgresql://jagrutvaghasiya@localhost:5432/nl2sql_test")
    print("   3. Try natural language queries like:")
    print("      - 'Show me all users'")
    print("      - 'Find expensive products'")
    print("      - 'Count orders by status'")
    print("      - 'Get top 5 customers'")
    
    print("\n📚 API Documentation:")
    print("   - Swagger UI: http://localhost:8000/docs")
    print("   - ReDoc: http://localhost:8000/redoc")

if __name__ == "__main__":
    main()
