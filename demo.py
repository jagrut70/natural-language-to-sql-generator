#!/usr/bin/env python3
"""
Demo script for NL2SQL Query Generator
This script demonstrates how to use the NL2SQL system programmatically
"""

import os
import sys
import logging
from typing import List, Dict

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from core.nl2sql import NL2SQLGenerator
from utils.helpers import create_sample_database

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def demo_nl2sql():
    """Demonstrate the NL2SQL system functionality"""
    
    print("🚀 NL2SQL Query Generator Demo")
    print("=" * 50)
    
    # Database configuration
    database_url = "postgresql://postgres:password@localhost:5432/nl2sql_demo"
    
    # Check if we need to create a sample database
    print("\n📊 Setting up database...")
    try:
        # Try to create sample database
        success = create_sample_database(database_url)
        if success:
            print("✅ Sample database created successfully!")
        else:
            print("⚠️  Could not create sample database. Make sure PostgreSQL is running.")
            print("   You can manually create the database using the schema in examples/sample_schema.sql")
            return
    except Exception as e:
        print(f"❌ Error setting up database: {e}")
        print("   Please make sure PostgreSQL is running and accessible.")
        return
    
    # Initialize NL2SQL generator
    print("\n🤖 Initializing NL2SQL generator...")
    try:
        generator = NL2SQLGenerator(
            database_url=database_url,
            model_name="t5-base",
            max_tokens=512,
            temperature=0.7
        )
        print("✅ NL2SQL generator initialized successfully!")
    except Exception as e:
        print(f"❌ Error initializing generator: {e}")
        return
    
    # Display schema information
    print("\n📋 Database Schema:")
    schema_info = generator.get_schema_info()
    summary = schema_info.get('summary', {})
    print(f"   Tables: {summary.get('total_tables', 0)}")
    print(f"   Columns: {summary.get('total_columns', 0)}")
    print(f"   Relationships: {summary.get('total_relationships', 0)}")
    
    # Example queries to test
    example_queries = [
        "Show me all users",
        "Find products that cost more than $50",
        "Count the number of orders per customer",
        "Get the top 5 most expensive products",
        "Show me users who placed orders last month",
        "Find products that are out of stock",
        "Get the average order value by month",
        "Show me products and their categories"
    ]
    
    print(f"\n🔍 Testing {len(example_queries)} example queries...")
    print("=" * 50)
    
    for i, query in enumerate(example_queries, 1):
        print(f"\n{i}. Query: {query}")
        print("-" * 30)
        
        try:
            # Generate SQL
            result = generator.generate_and_execute(
                natural_language_query=query,
                include_examples=True,
                max_examples=3,
                execute_query=True
            )
            
            generation = result.get('generation', {})
            execution = result.get('execution', {})
            
            if generation.get('error'):
                print(f"❌ Generation Error: {generation['error']}")
                continue
            
            # Display generated SQL
            generated_sql = generation.get('generated_sql', '')
            print(f"📝 Generated SQL:")
            print(f"   {generated_sql}")
            
            # Display validation results
            validation = generation.get('validation', {})
            if validation.get('errors'):
                print(f"❌ Validation Errors:")
                for error in validation['errors']:
                    print(f"   - {error}")
            
            if validation.get('warnings'):
                print(f"⚠️  Warnings:")
                for warning in validation['warnings']:
                    print(f"   - {warning}")
            
            # Display execution results
            if execution and not execution.get('error'):
                results = execution.get('results', [])
                row_count = execution.get('row_count', 0)
                print(f"📊 Results: {row_count} rows returned")
                
                if results and len(results) > 0:
                    # Show first few results
                    print("   Sample results:")
                    for j, row in enumerate(results[:3], 1):
                        print(f"   {j}. {row}")
                    
                    if len(results) > 3:
                        print(f"   ... and {len(results) - 3} more rows")
            elif execution and execution.get('error'):
                print(f"❌ Execution Error: {execution['error']}")
            
        except Exception as e:
            print(f"❌ Error processing query: {e}")
        
        print()
    
    # Show system statistics
    print("\n📈 System Statistics:")
    print("=" * 30)
    stats = generator.get_statistics()
    
    print(f"Model: {stats['model_info']['model_name']}")
    print(f"Max Tokens: {stats['model_info']['max_tokens']}")
    print(f"Temperature: {stats['model_info']['temperature']}")
    print(f"Few-shot Examples: {stats['few_shot_learning']['total_examples']}")
    print(f"Patterns: {stats['few_shot_learning']['total_patterns']}")
    
    # Add a custom example
    print("\n➕ Adding a custom example...")
    generator.add_example(
        "Find all active users",
        "SELECT * FROM users WHERE is_active = TRUE",
        "custom_filtering"
    )
    print("✅ Custom example added!")
    
    # Test the custom example
    print("\n🧪 Testing custom example...")
    try:
        result = generator.generate_and_execute(
            "Find all active users",
            include_examples=True,
            max_examples=3,
            execute_query=True
        )
        
        generation = result.get('generation', {})
        if not generation.get('error'):
            print(f"📝 Generated SQL: {generation.get('generated_sql', '')}")
            
            execution = result.get('execution', {})
            if execution and not execution.get('error'):
                row_count = execution.get('row_count', 0)
                print(f"📊 Results: {row_count} active users found")
    
    except Exception as e:
        print(f"❌ Error testing custom example: {e}")
    
    print("\n🎉 Demo completed!")
    print("\n💡 Tips:")
    print("   - You can run the Streamlit app with: streamlit run app/streamlit_app.py")
    print("   - You can start the API server with: uvicorn app.api:app --reload")
    print("   - Check the examples/ directory for more sample queries")
    print("   - Run tests with: python -m pytest tests/")


def demo_api_usage():
    """Demonstrate API usage"""
    print("\n🌐 API Usage Example:")
    print("=" * 30)
    
    api_example = '''
import requests

# Connect to database
response = requests.post("http://localhost:8000/connect", json={
    "database_url": "postgresql://user:pass@localhost:5432/db",
    "model_name": "t5-base"
})

# Generate SQL
response = requests.post("http://localhost:8000/generate-sql", json={
    "natural_language_query": "Show me all users",
    "include_examples": True,
    "max_examples": 3,
    "execute_query": True
})

result = response.json()
print(f"Generated SQL: {result['generated_sql']}")
print(f"Results: {result['execution_results']}")
'''
    
    print(api_example)


if __name__ == "__main__":
    try:
        demo_nl2sql()
        demo_api_usage()
    except KeyboardInterrupt:
        print("\n\n👋 Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        logger.error(f"Demo error: {e}")
