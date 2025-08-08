"""
Mock NL2SQL Generator
Provides basic NL2SQL functionality for demonstration without requiring T5 model
"""

import logging
import re
from typing import Dict, List, Optional, Tuple
from .schema_extractor import SchemaExtractor
from .few_shot_learning import FewShotLearning
from .query_validator import QueryValidator

logger = logging.getLogger(__name__)


class MockNL2SQLGenerator:
    """Mock NL2SQL generator for demonstration purposes"""
    
    def __init__(self, database_url: str):
        """
        Initialize mock NL2SQL generator
        
        Args:
            database_url: Database connection URL
        """
        self.database_url = database_url
        self.schema_extractor = SchemaExtractor(database_url)
        self.few_shot_learning = FewShotLearning()
        self.query_validator = QueryValidator()
        self.is_initialized = False
        
        # Initialize components
        try:
            if self.schema_extractor.connect():
                self.is_initialized = True
                logger.info("Mock NL2SQL generator initialized successfully")
            else:
                logger.error("Failed to connect to database")
        except Exception as e:
            logger.error(f"Error initializing mock NL2SQL generator: {e}")
    
    def generate_sql(self, natural_language_query: str) -> Dict:
        """
        Generate SQL from natural language query using pattern matching
        
        Args:
            natural_language_query: Natural language query
            
        Returns:
            Dict: Generated SQL and metadata
        """
        if not self.is_initialized:
            return {
                "sql_query": "",
                "confidence": 0.0,
                "explanation": "Generator not initialized. Please connect to database first.",
                "tables_used": [],
                "columns_used": []
            }
        
        try:
            # Get database schema
            schema = self.schema_extractor.get_database_schema()
            tables = self.schema_extractor.get_all_tables()
            
            # Get relevant examples
            examples = self.few_shot_learning.get_similar_examples(natural_language_query, limit=3)
            
            # Generate SQL using pattern matching
            sql_query = self._pattern_match_sql(natural_language_query, tables, schema)
            
            # Validate the generated SQL
            validation_result = self.query_validator.validate_query(sql_query, schema)
            
            # Extract tables and columns used
            tables_used = validation_result.get('tables_used', [])
            columns_used = validation_result.get('columns_used', [])
            
            # Calculate confidence based on validation
            confidence = 0.8 if validation_result['is_valid'] else 0.3
            
            return {
                "sql_query": sql_query,
                "confidence": confidence,
                "explanation": f"Generated using pattern matching. {len(examples)} similar examples found.",
                "tables_used": tables_used,
                "columns_used": columns_used,
                "validation": validation_result
            }
            
        except Exception as e:
            logger.error(f"Error generating SQL: {e}")
            return {
                "sql_query": "",
                "confidence": 0.0,
                "explanation": f"Error generating SQL: {str(e)}",
                "tables_used": [],
                "columns_used": []
            }
    
    def _pattern_match_sql(self, query: str, tables: List[str], schema: Dict) -> str:
        """
        Generate SQL using pattern matching rules
        
        Args:
            query: Natural language query
            tables: Available tables
            schema: Database schema
            
        Returns:
            str: Generated SQL query
        """
        query_lower = query.lower()
        
        # Pattern 1: Show all records from a table
        if any(word in query_lower for word in ["show me all", "get all", "list all", "display all"]):
            for table in tables:
                if table in query_lower:
                    return f"SELECT * FROM {table}"
            # Default to users if no specific table mentioned
            if "users" in tables:
                return "SELECT * FROM users"
        
        # Pattern 2: Count records
        if any(word in query_lower for word in ["count", "number of", "how many", "total"]):
            for table in tables:
                if table in query_lower:
                    return f"SELECT COUNT(*) FROM {table}"
            if "users" in tables:
                return "SELECT COUNT(*) FROM users"
        
        # Pattern 3: Find records with conditions
        if any(word in query_lower for word in ["find", "get", "show", "display"]):
            # Look for price conditions
            if "price" in query_lower or "cost" in query_lower:
                if "products" in tables:
                    # Extract price value if mentioned
                    price_match = re.search(r'(\d+)', query)
                    if price_match:
                        price = price_match.group(1)
                        if "more than" in query_lower or "greater than" in query_lower:
                            return f"SELECT * FROM products WHERE price > {price}"
                        elif "less than" in query_lower or "under" in query_lower:
                            return f"SELECT * FROM products WHERE price < {price}"
                        else:
                            return f"SELECT * FROM products WHERE price = {price}"
                    else:
                        return "SELECT * FROM products ORDER BY price DESC"
            
            # Look for user conditions
            if "user" in query_lower:
                if "users" in tables:
                    return "SELECT * FROM users"
        
        # Pattern 4: Top N records
        if "top" in query_lower:
            # Extract number
            number_match = re.search(r'top\s+(\d+)', query_lower)
            if number_match:
                limit = number_match.group(1)
                if "products" in tables and ("expensive" in query_lower or "price" in query_lower):
                    return f"SELECT * FROM products ORDER BY price DESC LIMIT {limit}"
                elif "users" in tables:
                    return f"SELECT * FROM users LIMIT {limit}"
        
        # Pattern 5: Orders and customers
        if "order" in query_lower:
            if "orders" in tables:
                if "customer" in query_lower:
                    return "SELECT o.*, u.username FROM orders o JOIN users u ON o.user_id = u.id"
                else:
                    return "SELECT * FROM orders"
        
        # Pattern 6: Products and categories
        if "product" in query_lower and "categor" in query_lower:
            if "products" in tables and "categories" in tables:
                return "SELECT p.name, p.price, c.name as category FROM products p JOIN categories c ON p.category_id = c.id"
        
        # Default fallback
        if "users" in tables:
            return "SELECT * FROM users LIMIT 10"
        elif tables:
            return f"SELECT * FROM {tables[0]} LIMIT 10"
        else:
            return "SELECT 1"
    
    def execute_sql(self, sql_query: str) -> Dict:
        """
        Execute SQL query and return results
        
        Args:
            sql_query: SQL query to execute
            
        Returns:
            Dict: Query results and metadata
        """
        if not self.is_initialized:
            return {
                "results": [],
                "row_count": 0,
                "error": "Generator not initialized. Please connect to database first.",
                "execution_time": 0.0
            }
        
        try:
            # Validate the query first
            validation_result = self.query_validator.validate_query(sql_query)
            if not validation_result['is_valid']:
                return {
                    "results": [],
                    "row_count": 0,
                    "error": f"Invalid SQL query: {'; '.join(validation_result['errors'])}",
                    "execution_time": 0.0
                }
            
            # Execute the query
            from sqlalchemy import create_engine, text
            engine = create_engine(self.database_url)
            
            import time
            start_time = time.time()
            
            with engine.connect() as connection:
                result = connection.execute(text(sql_query))
                rows = result.fetchall()
                
                # Convert to list of dictionaries
                if rows:
                    columns = result.keys()
                    results = [dict(zip(columns, row)) for row in rows]
                else:
                    results = []
                
                execution_time = time.time() - start_time
                
                return {
                    "results": results,
                    "row_count": len(results),
                    "error": None,
                    "execution_time": execution_time
                }
                
        except Exception as e:
            logger.error(f"Error executing SQL: {e}")
            return {
                "results": [],
                "row_count": 0,
                "error": f"Error executing SQL: {str(e)}",
                "execution_time": 0.0
            }
    
    def get_schema(self) -> Dict:
        """
        Get database schema information
        
        Returns:
            Dict: Database schema
        """
        if not self.is_initialized:
            return {"error": "Generator not initialized"}
        
        try:
            # Get raw schema and convert to serializable format
            raw_schema = self.schema_extractor.get_database_schema()
            tables = self.schema_extractor.get_all_tables()
            
            # Convert to serializable format
            serializable_schema = {
                "tables": {},
                "relationships": [],
                "summary": {
                    "table_count": len(tables),
                    "tables": tables
                }
            }
            
            # Add table information
            for table_name in tables:
                table_info = self.schema_extractor.get_table_schema(table_name)
                if table_info:
                    # Convert columns to serializable format
                    columns = []
                    for col in table_info.get('columns', []):
                        columns.append({
                            'name': col.get('name', ''),
                            'type': str(col.get('type', '')),
                            'nullable': col.get('nullable', True),
                            'default': str(col.get('default', '')) if col.get('default') is not None else None
                        })
                    
                    serializable_schema["tables"][table_name] = {
                        "columns": columns,
                        "primary_keys": table_info.get('primary_keys', []),
                        "foreign_keys": table_info.get('foreign_keys', []),
                        "indexes": table_info.get('indexes', [])
                    }
            
            return serializable_schema
            
        except Exception as e:
            logger.error(f"Error getting schema: {e}")
            return {"error": str(e)}
    
    def get_examples(self) -> List[Dict]:
        """
        Get few-shot learning examples
        
        Returns:
            List[Dict]: Example queries
        """
        return self.few_shot_learning.examples
    
    def add_example(self, natural_language: str, sql: str, category: str = "custom", difficulty: str = "medium"):
        """
        Add a new example to few-shot learning
        
        Args:
            natural_language: Natural language query
            sql: Corresponding SQL query
            category: Example category
            difficulty: Example difficulty
        """
        self.few_shot_learning.add_example(natural_language, sql, category, difficulty)
    
    def get_statistics(self) -> Dict:
        """
        Get system statistics
        
        Returns:
            Dict: System statistics
        """
        if not self.is_initialized:
            return {"error": "Generator not initialized"}
        
        try:
            tables = self.schema_extractor.get_all_tables()
            examples = self.few_shot_learning.examples
            
            return {
                "tables_count": len(tables),
                "tables": tables,
                "examples_count": len(examples),
                "is_initialized": self.is_initialized,
                "generator_type": "mock"
            }
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {"error": str(e)}
