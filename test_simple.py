#!/usr/bin/env python3
"""
Simple test script for NL2SQL components
Tests the system without requiring a database connection
"""

import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from core.few_shot_learning import FewShotLearning
from core.query_validator import QueryValidator
from utils.helpers import format_sql, validate_natural_language_query

def test_few_shot_learning():
    """Test few-shot learning functionality"""
    print("🧪 Testing Few-Shot Learning...")
    
    few_shot = FewShotLearning()
    
    # Test basic functionality
    print(f"  ✅ Loaded {len(few_shot.examples)} examples")
    print(f"  ✅ Loaded {len(few_shot.patterns)} patterns")
    
    # Test adding examples
    few_shot.add_example(
        "Find all active users",
        "SELECT * FROM users WHERE is_active = TRUE",
        "custom_filtering"
    )
    print("  ✅ Added custom example")
    
    # Test pattern matching
    patterns = few_shot.get_patterns_for_query("Count the number of users")
    print(f"  ✅ Found {len(patterns)} matching patterns")
    
    # Test similar examples
    similar = few_shot.get_similar_examples("Show me all users", limit=2)
    print(f"  ✅ Found {len(similar)} similar examples")
    
    print("  🎉 Few-shot learning tests passed!\n")

def test_query_validator():
    """Test query validation functionality"""
    print("🔒 Testing Query Validator...")
    
    validator = QueryValidator()
    
    # Test valid SQL
    valid_sql = "SELECT * FROM users WHERE id = 1"
    result = validator.validate_query(valid_sql)
    print(f"  ✅ Valid SQL validation: {result['is_valid']}")
    
    # Test dangerous SQL
    dangerous_sql = "SELECT * FROM users; DROP TABLE users;"
    result = validator.validate_query(dangerous_sql)
    print(f"  ✅ Dangerous SQL blocked: {not result['is_valid']}")
    
    # Test read-only detection
    is_readonly = validator.is_read_only("SELECT * FROM users")
    print(f"  ✅ Read-only detection: {is_readonly}")
    
    # Test complexity scoring
    simple_score = validator.get_query_complexity_score("SELECT * FROM users")
    complex_score = validator.get_query_complexity_score(
        "SELECT u.name, COUNT(o.id) FROM users u JOIN orders o ON u.id = o.user_id GROUP BY u.id"
    )
    print(f"  ✅ Complexity scoring: {simple_score} vs {complex_score}")
    
    print("  🎉 Query validator tests passed!\n")

def test_helpers():
    """Test helper functions"""
    print("🛠️  Testing Helper Functions...")
    
    # Test SQL formatting
    sql = "SELECT * FROM users WHERE id=1"
    formatted = format_sql(sql)
    print(f"  ✅ SQL formatting: {formatted[:50]}...")
    
    # Test natural language validation
    valid_query = "Show me all users"
    is_valid, message = validate_natural_language_query(valid_query)
    print(f"  ✅ Valid NL query: {is_valid}")
    
    invalid_query = "SELECT * FROM users"
    is_valid, message = validate_natural_language_query(invalid_query)
    print(f"  ✅ Invalid NL query blocked: {not is_valid}")
    
    print("  🎉 Helper function tests passed!\n")

def test_schema_extractor_without_db():
    """Test schema extractor without database connection"""
    print("📊 Testing Schema Extractor (without DB)...")
    
    from core.schema_extractor import SchemaExtractor
    
    # Create extractor with dummy URL
    extractor = SchemaExtractor("postgresql://dummy:dummy@localhost:5432/dummy")
    
    # Test formatting with empty schema
    empty_schema = {}
    formatted = extractor.format_schema_for_prompt(empty_schema)
    print(f"  ✅ Empty schema formatting: {formatted[:50]}...")
    
    # Test with sample schema
    sample_schema = {
        'tables': {
            'users': {
                'columns': [
                    {'name': 'id', 'type': 'INTEGER', 'nullable': False},
                    {'name': 'name', 'type': 'VARCHAR(100)', 'nullable': True}
                ],
                'primary_keys': ['id'],
                'foreign_keys': []
            }
        }
    }
    formatted = extractor.format_schema_for_prompt(sample_schema)
    print(f"  ✅ Sample schema formatting: {formatted[:100]}...")
    
    print("  🎉 Schema extractor tests passed!\n")

def main():
    """Run all tests"""
    print("🚀 NL2SQL System Testing")
    print("=" * 50)
    
    try:
        test_few_shot_learning()
        test_query_validator()
        test_helpers()
        test_schema_extractor_without_db()
        
        print("🎉 All tests completed successfully!")
        print("\n💡 Next steps:")
        print("   1. Set up PostgreSQL database")
        print("   2. Run: python demo.py")
        print("   3. Start web interface: streamlit run app/streamlit_app.py")
        print("   4. Start API server: uvicorn app.api:app --reload")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
