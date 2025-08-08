#!/usr/bin/env python3
"""
Test script for NL2SQL functionality
"""

import os
import sys
import asyncio
import requests
import json
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_api_health():
    """Test if the API is running"""
    try:
        response = requests.get("http://localhost:8000/health")
        if response.status_code == 200:
            print("✅ API Health Check: PASSED")
            return True
        else:
            print("❌ API Health Check: FAILED")
            return False
    except Exception as e:
        print(f"❌ API Health Check: FAILED - {e}")
        return False

def test_streamlit_health():
    """Test if Streamlit is running"""
    try:
        response = requests.get("http://localhost:8501")
        if response.status_code == 200:
            print("✅ Streamlit Health Check: PASSED")
            return True
        else:
            print("❌ Streamlit Health Check: FAILED")
            return False
    except Exception as e:
        print(f"❌ Streamlit Health Check: FAILED - {e}")
        return False

def test_database_connection():
    """Test database connection and setup"""
    try:
        from app.utils.helpers import create_sample_database
        
        # Use a test database URL (you can modify this)
        database_url = "postgresql://jagrutvaghasiya@localhost:5432/nl2sql_test"
        
        print(f"🔧 Setting up test database: {database_url}")
        success = create_sample_database(database_url)
        
        if success:
            print("✅ Database Setup: PASSED")
            return database_url
        else:
            print("❌ Database Setup: FAILED")
            return None
    except Exception as e:
        print(f"❌ Database Setup: FAILED - {e}")
        print("💡 You may need to set up PostgreSQL first:")
        print("   Option 1: Docker: docker run --name postgres -e POSTGRES_PASSWORD=password -e POSTGRES_DB=nl2sql_test -p 5432:5432 -d postgres:15")
        print("   Option 2: Local: brew install postgresql && brew services start postgresql")
        return None

def test_nl2sql_generation(database_url):
    """Test NL2SQL generation with sample queries"""
    test_queries = [
        "Show me all users",
        "Find products that cost more than $50",
        "Count the number of orders per customer",
        "Get the top 5 most expensive products",
        "Show me users who have placed orders"
    ]
    
    print("\n🧪 Testing NL2SQL Generation:")
    print("=" * 50)
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{i}. Testing: '{query}'")
        
        try:
            # Test via API
            response = requests.post(
                "http://localhost:8000/generate-sql",
                json={
                    "natural_language_query": query,
                    "database_url": database_url
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                sql_query = result.get("sql_query", "")
                print(f"   ✅ Generated SQL: {sql_query[:100]}...")
                
                # Test execution if SQL was generated
                if sql_query:
                    exec_response = requests.post(
                        "http://localhost:8000/execute-sql",
                        json={
                            "sql_query": sql_query,
                            "database_url": database_url
                        }
                    )
                    
                    if exec_response.status_code == 200:
                        exec_result = exec_response.json()
                        row_count = len(exec_result.get("results", []))
                        print(f"   ✅ Executed successfully: {row_count} rows returned")
                    else:
                        print(f"   ⚠️  Execution failed: {exec_response.text}")
            else:
                print(f"   ❌ Generation failed: {response.text}")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")

def test_schema_extraction(database_url):
    """Test schema extraction functionality"""
    print("\n🔍 Testing Schema Extraction:")
    print("=" * 50)
    
    try:
        response = requests.post(
            "http://localhost:8000/get-schema",
            json={"database_url": database_url}
        )
        
        if response.status_code == 200:
            schema = response.json()
            tables = schema.get("tables", [])
            print(f"✅ Schema extracted: {len(tables)} tables found")
            
            for table in tables[:3]:  # Show first 3 tables
                print(f"   📋 Table: {table['name']} ({len(table['columns'])} columns)")
        else:
            print(f"❌ Schema extraction failed: {response.text}")
            
    except Exception as e:
        print(f"❌ Schema extraction error: {e}")

def test_few_shot_learning():
    """Test few-shot learning functionality"""
    print("\n🎯 Testing Few-Shot Learning:")
    print("=" * 50)
    
    try:
        response = requests.get("http://localhost:8000/examples")
        
        if response.status_code == 200:
            examples = response.json()
            print(f"✅ Few-shot examples loaded: {len(examples)} examples available")
            
            # Show a few examples
            for i, example in enumerate(examples[:3], 1):
                print(f"   {i}. '{example['natural_language']}' → '{example['sql']}'")
        else:
            print(f"❌ Few-shot learning failed: {response.text}")
            
    except Exception as e:
        print(f"❌ Few-shot learning error: {e}")

def main():
    """Main test function"""
    print("🚀 NL2SQL Functionality Test Suite")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test 1: Health checks
    print("\n1️⃣  Health Checks:")
    print("-" * 30)
    api_healthy = test_api_health()
    streamlit_healthy = test_streamlit_health()
    
    if not (api_healthy and streamlit_healthy):
        print("\n❌ Health checks failed. Please ensure both servers are running:")
        print("   - API: source nl2sql_env/bin/activate && python -m uvicorn app.api:app --reload --port 8000")
        print("   - Streamlit: source nl2sql_env/bin/activate && streamlit run app/streamlit_app.py --server.headless true --server.port 8501")
        return
    
    # Test 2: Database setup
    print("\n2️⃣  Database Setup:")
    print("-" * 30)
    database_url = test_database_connection()
    
    if not database_url:
        print("\n⚠️  Database setup failed. You can still test the web interface manually.")
        print("   Open http://localhost:8501 in your browser to test the UI.")
        return
    
    # Test 3: Schema extraction
    test_schema_extraction(database_url)
    
    # Test 4: Few-shot learning
    test_few_shot_learning()
    
    # Test 5: NL2SQL generation
    test_nl2sql_generation(database_url)
    
    print("\n🎉 Test Suite Completed!")
    print("=" * 60)
    print("\n📋 Next Steps:")
    print("   1. Open http://localhost:8501 in your browser")
    print("   2. Enter the database URL: " + database_url)
    print("   3. Try natural language queries like:")
    print("      - 'Show me all users'")
    print("      - 'Find expensive products'")
    print("      - 'Count orders by status'")
    print("\n   4. Check the API docs at http://localhost:8000/docs")

if __name__ == "__main__":
    main()
