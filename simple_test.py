#!/usr/bin/env python3
"""
Simple test script for NL2SQL functionality without T5 model
"""

import os
import sys
import requests
import json
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_web_interface():
    """Test the web interface directly"""
    print("🌐 Testing Web Interface:")
    print("=" * 50)
    
    try:
        response = requests.get("http://localhost:8501")
        if response.status_code == 200:
            print("✅ Streamlit Web Interface: ACCESSIBLE")
            print("   📍 URL: http://localhost:8501")
            print("   💡 Open this URL in your browser to test the UI")
            return True
        else:
            print(f"❌ Streamlit Web Interface: FAILED (Status: {response.status_code})")
            return False
    except Exception as e:
        print(f"❌ Streamlit Web Interface: FAILED - {e}")
        return False

def test_api_endpoints():
    """Test API endpoints without model initialization"""
    print("\n🔌 Testing API Endpoints:")
    print("=" * 50)
    
    # Test health endpoint
    try:
        response = requests.get("http://localhost:8000/health")
        if response.status_code == 200:
            print("✅ Health Endpoint: WORKING")
            health_data = response.json()
            print(f"   📊 Status: {health_data.get('status', 'unknown')}")
            print(f"   🤖 Generator Initialized: {health_data.get('generator_initialized', False)}")
        else:
            print(f"❌ Health Endpoint: FAILED (Status: {response.status_code})")
    except Exception as e:
        print(f"❌ Health Endpoint: FAILED - {e}")
    
    # Test examples endpoint
    try:
        response = requests.get("http://localhost:8000/examples")
        if response.status_code == 200:
            examples = response.json()
            print(f"✅ Examples Endpoint: WORKING ({len(examples)} examples)")
            for i, example in enumerate(examples[:2], 1):
                print(f"   {i}. '{example['natural_language']}' → '{example['sql']}'")
        else:
            print(f"❌ Examples Endpoint: FAILED (Status: {response.status_code})")
    except Exception as e:
        print(f"❌ Examples Endpoint: FAILED - {e}")
    
    # Test API documentation
    try:
        response = requests.get("http://localhost:8000/docs")
        if response.status_code == 200:
            print("✅ API Documentation: ACCESSIBLE")
            print("   📍 URL: http://localhost:8000/docs")
        else:
            print(f"❌ API Documentation: FAILED (Status: {response.status_code})")
    except Exception as e:
        print(f"❌ API Documentation: FAILED - {e}")

def test_database_functionality():
    """Test database functionality"""
    print("\n🗄️  Testing Database Functionality:")
    print("=" * 50)
    
    database_url = "postgresql://jagrutvaghasiya@localhost:5432/nl2sql_test"
    
    # Test database connection
    try:
        from app.utils.helpers import create_sample_database
        success = create_sample_database(database_url)
        if success:
            print("✅ Database Setup: SUCCESSFUL")
            print(f"   📍 Database URL: {database_url}")
            print("   📋 Sample tables created: users, categories, products, orders, order_items")
            return database_url
        else:
            print("❌ Database Setup: FAILED")
            return None
    except Exception as e:
        print(f"❌ Database Setup: FAILED - {e}")
        return None

def test_schema_extraction(database_url):
    """Test schema extraction"""
    print("\n🔍 Testing Schema Extraction:")
    print("=" * 50)
    
    try:
        from app.core.schema_extractor import SchemaExtractor
        extractor = SchemaExtractor(database_url)
        schema = extractor.get_database_schema()
        
        if schema:
            print("✅ Schema Extraction: SUCCESSFUL")
            tables = extractor.get_all_tables()
            print(f"   📊 Tables found: {len(tables)}")
            print(f"   📋 Tables: {', '.join(tables)}")
            
            # Show details for first table
            if tables:
                first_table = tables[0]
                table_schema = extractor.get_table_schema(first_table)
                if table_schema:
                    columns = table_schema.get('columns', [])
                    print(f"   📋 Sample table '{first_table}': {len(columns)} columns")
                    for col in columns[:3]:
                        print(f"      - {col['name']}: {col['type']}")
        else:
            print("❌ Schema Extraction: FAILED")
    except Exception as e:
        print(f"❌ Schema Extraction: FAILED - {e}")

def test_few_shot_learning():
    """Test few-shot learning functionality"""
    print("\n🎯 Testing Few-Shot Learning:")
    print("=" * 50)
    
    try:
        from app.core.few_shot_learning import FewShotLearning
        fsl = FewShotLearning()
        
        # Get all examples
        examples = fsl.examples
        
        if examples:
            print(f"✅ Few-Shot Learning: SUCCESSFUL ({len(examples)} examples)")
            for i, example in enumerate(examples[:3], 1):
                print(f"   {i}. '{example['natural_language']}' → '{example['sql']}'")
            
            # Test getting examples by category
            basic_examples = fsl.get_examples_by_category("basic_select")
            print(f"   📊 Basic select examples: {len(basic_examples)}")
            
            # Test getting examples by difficulty
            easy_examples = fsl.get_examples_by_difficulty("easy")
            print(f"   📊 Easy examples: {len(easy_examples)}")
        else:
            print("❌ Few-Shot Learning: FAILED")
    except Exception as e:
        print(f"❌ Few-Shot Learning: FAILED - {e}")

def test_query_validation():
    """Test query validation functionality"""
    print("\n✅ Testing Query Validation:")
    print("=" * 50)
    
    try:
        from app.core.query_validator import QueryValidator
        
        validator = QueryValidator()
        
        # Test valid SQL
        valid_sql = "SELECT * FROM users WHERE id = 1"
        result = validator.validate_query(valid_sql)
        print(f"✅ Valid SQL Test: {'PASSED' if result['is_valid'] else 'FAILED'}")
        
        # Test invalid SQL
        invalid_sql = "SELECT * FROM users WHERE id = 1; DROP TABLE users;"
        result = validator.validate_query(invalid_sql)
        print(f"✅ Invalid SQL Test: {'PASSED' if not result['is_valid'] else 'FAILED'}")
        
        # Test security validation
        dangerous_sql = "DROP TABLE users"
        result = validator.validate_query(dangerous_sql)
        print(f"✅ Security Validation: {'PASSED' if not result['is_valid'] else 'FAILED'}")
        
        # Test read-only validation
        read_only_result = validator.is_read_only("SELECT * FROM users")
        print(f"✅ Read-Only Validation: {'PASSED' if read_only_result else 'FAILED'}")
        
    except Exception as e:
        print(f"❌ Query Validation: FAILED - {e}")

def main():
    """Main test function"""
    print("🚀 NL2SQL Simple Functionality Test")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test 1: Web interface
    test_web_interface()
    
    # Test 2: API endpoints
    test_api_endpoints()
    
    # Test 3: Database functionality
    database_url = test_database_functionality()
    
    if database_url:
        # Test 4: Schema extraction
        test_schema_extraction(database_url)
    
    # Test 5: Few-shot learning
    test_few_shot_learning()
    
    # Test 6: Query validation
    test_query_validation()
    
    print("\n🎉 Simple Test Suite Completed!")
    print("=" * 60)
    print("\n📋 How to Test the Full Functionality:")
    print("   1. 🌐 Open the web interface: http://localhost:8501")
    print("   2. 📊 Enter database URL: postgresql://jagrutvaghasiya@localhost:5432/nl2sql_test")
    print("   3. 🔧 Install missing dependencies:")
    print("      pip install sentencepiece")
    print("      # or use a different model that doesn't require sentencepiece")
    print("   4. 🧪 Try natural language queries:")
    print("      - 'Show me all users'")
    print("      - 'Find products that cost more than $50'")
    print("      - 'Count orders by status'")
    print("\n   5. 📚 Check API docs: http://localhost:8000/docs")
    print("\n💡 Note: The T5 model requires sentencepiece which needs to be installed separately.")
    print("   For now, you can test the UI and database functionality!")

if __name__ == "__main__":
    main()
