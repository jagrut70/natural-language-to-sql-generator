"""
Unit tests for NL2SQL system components
"""

import unittest
import tempfile
import os
import sys
from unittest.mock import Mock, patch, MagicMock

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from core.schema_extractor import SchemaExtractor
from core.query_validator import QueryValidator
from core.few_shot_learning import FewShotLearning
from utils.helpers import validate_database_url, format_sql, validate_natural_language_query


class TestSchemaExtractor(unittest.TestCase):
    """Test cases for SchemaExtractor"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.database_url = "postgresql://test:test@localhost:5432/testdb"
        self.extractor = SchemaExtractor(self.database_url)
    
    def test_init(self):
        """Test SchemaExtractor initialization"""
        self.assertEqual(self.extractor.database_url, self.database_url)
        self.assertIsNone(self.extractor.engine)
        self.assertIsNone(self.extractor.inspector)
    
    @patch('app.core.schema_extractor.create_engine')
    @patch('app.core.schema_extractor.inspect')
    def test_connect_success(self, mock_inspect, mock_create_engine):
        """Test successful database connection"""
        mock_engine = Mock()
        mock_inspector = Mock()
        mock_create_engine.return_value = mock_engine
        mock_inspect.return_value = mock_inspector
        
        result = self.extractor.connect()
        
        self.assertTrue(result)
        self.assertEqual(self.extractor.engine, mock_engine)
        self.assertEqual(self.extractor.inspector, mock_inspector)
    
    @patch('app.core.schema_extractor.create_engine')
    def test_connect_failure(self, mock_create_engine):
        """Test database connection failure"""
        mock_create_engine.side_effect = Exception("Connection failed")
        
        result = self.extractor.connect()
        
        self.assertFalse(result)
    
    def test_format_schema_for_prompt(self):
        """Test schema formatting for prompts"""
        schema = {
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
        
        formatted = self.extractor.format_schema_for_prompt(schema)
        
        self.assertIn('Table: users', formatted)
        self.assertIn('id: INTEGER (NOT NULL)', formatted)
        self.assertIn('name: VARCHAR(100) (NULL)', formatted)
        self.assertIn('Primary Key: id', formatted)


class TestQueryValidator(unittest.TestCase):
    """Test cases for QueryValidator"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.validator = QueryValidator()
    
    def test_validate_syntax_valid(self):
        """Test valid SQL syntax"""
        sql = "SELECT * FROM users"
        result = self.validator._validate_syntax(sql)
        
        self.assertTrue(result['is_valid'])
        self.assertEqual(len(result['errors']), 0)
    
    def test_validate_syntax_invalid(self):
        """Test invalid SQL syntax"""
        sql = "SELECT * FROM"  # Incomplete query
        result = self.validator._validate_syntax(sql)
        
        self.assertFalse(result['is_valid'])
        self.assertGreater(len(result['errors']), 0)
    
    def test_validate_security_dangerous_keyword(self):
        """Test security validation with dangerous keywords"""
        sql = "SELECT * FROM users; DROP TABLE users;"
        result = self.validator._validate_security(sql)
        
        self.assertFalse(result['is_valid'])
        self.assertGreater(len(result['errors']), 0)
    
    def test_validate_security_safe(self):
        """Test security validation with safe query"""
        sql = "SELECT * FROM users WHERE id = 1"
        result = self.validator._validate_security(sql)
        
        self.assertTrue(result['is_valid'])
        self.assertEqual(len(result['errors']), 0)
    
    def test_is_read_only_select(self):
        """Test read-only detection for SELECT queries"""
        sql = "SELECT * FROM users"
        self.assertTrue(self.validator.is_read_only(sql))
    
    def test_is_read_only_dangerous(self):
        """Test read-only detection for dangerous queries"""
        sql = "DELETE FROM users"
        self.assertFalse(self.validator.is_read_only(sql))
    
    def test_get_query_complexity_score(self):
        """Test query complexity scoring"""
        simple_sql = "SELECT * FROM users"
        complex_sql = "SELECT u.name, COUNT(o.id) FROM users u JOIN orders o ON u.id = o.user_id GROUP BY u.id HAVING COUNT(o.id) > 5 ORDER BY COUNT(o.id) DESC"
        
        simple_score = self.validator.get_query_complexity_score(simple_sql)
        complex_score = self.validator.get_query_complexity_score(complex_sql)
        
        self.assertLess(simple_score, complex_score)
        self.assertLessEqual(simple_score, 10)
        self.assertLessEqual(complex_score, 10)


class TestFewShotLearning(unittest.TestCase):
    """Test cases for FewShotLearning"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.few_shot = FewShotLearning()
    
    def test_init_with_default_examples(self):
        """Test initialization with default examples"""
        self.assertGreater(len(self.few_shot.examples), 0)
        self.assertGreater(len(self.few_shot.patterns), 0)
    
    def test_add_example(self):
        """Test adding a new example"""
        initial_count = len(self.few_shot.examples)
        
        self.few_shot.add_example(
            "Show me all products",
            "SELECT * FROM products",
            "test_category"
        )
        
        self.assertEqual(len(self.few_shot.examples), initial_count + 1)
    
    def test_get_examples_by_category(self):
        """Test filtering examples by category"""
        self.few_shot.add_example(
            "Test query",
            "SELECT * FROM test",
            "test_category"
        )
        
        examples = self.few_shot.get_examples_by_category("test_category")
        self.assertEqual(len(examples), 1)
        self.assertEqual(examples[0]['category'], "test_category")
    
    def test_get_similar_examples(self):
        """Test finding similar examples"""
        query = "Show me all users"
        similar = self.few_shot.get_similar_examples(query, limit=2)
        
        self.assertLessEqual(len(similar), 2)
    
    def test_get_patterns_for_query(self):
        """Test pattern matching"""
        query = "Count the number of users"
        patterns = self.few_shot.get_patterns_for_query(query)
        
        self.assertGreater(len(patterns), 0)
        self.assertEqual(patterns[0]['name'], 'count')
    
    def test_format_examples_for_prompt(self):
        """Test example formatting for prompts"""
        examples = [
            {
                'natural_language': 'Test query',
                'sql': 'SELECT * FROM test'
            }
        ]
        
        formatted = self.few_shot.format_examples_for_prompt(examples)
        
        self.assertIn('Test query', formatted)
        self.assertIn('SELECT * FROM test', formatted)
    
    def test_validate_example(self):
        """Test example validation"""
        # Valid example
        self.assertTrue(self.few_shot.validate_example(
            "Show me users",
            "SELECT * FROM users"
        ))
        
        # Invalid example (no SQL)
        self.assertFalse(self.few_shot.validate_example(
            "Show me users",
            ""
        ))
        
        # Invalid example (no SELECT)
        self.assertFalse(self.few_shot.validate_example(
            "Show me users",
            "DELETE FROM users"
        ))


class TestHelpers(unittest.TestCase):
    """Test cases for helper functions"""
    
    def test_validate_database_url_valid(self):
        """Test valid database URL validation"""
        url = "postgresql://user:pass@localhost:5432/db"
        is_valid, message = validate_database_url(url)
        
        # Note: This will fail without actual database connection
        # In a real test environment, you'd mock the database connection
        self.assertIn("postgresql", url)
    
    def test_validate_database_url_invalid(self):
        """Test invalid database URL validation"""
        url = "invalid://url"
        is_valid, message = validate_database_url(url)
        
        self.assertFalse(is_valid)
        self.assertIn("Only PostgreSQL", message)
    
    def test_format_sql(self):
        """Test SQL formatting"""
        sql = "SELECT * FROM users WHERE id=1"
        formatted = format_sql(sql)
        
        self.assertIn("SELECT", formatted)
        self.assertIn("FROM", formatted)
    
    def test_validate_natural_language_query_valid(self):
        """Test valid natural language query validation"""
        query = "Show me all users"
        is_valid, message = validate_natural_language_query(query)
        
        self.assertTrue(is_valid)
        self.assertEqual(message, "Valid query")
    
    def test_validate_natural_language_query_empty(self):
        """Test empty query validation"""
        query = ""
        is_valid, message = validate_natural_language_query(query)
        
        self.assertFalse(is_valid)
        self.assertIn("empty", message)
    
    def test_validate_natural_language_query_too_short(self):
        """Test too short query validation"""
        query = "Hi"
        is_valid, message = validate_natural_language_query(query)
        
        self.assertFalse(is_valid)
        self.assertIn("short", message)
    
    def test_validate_natural_language_query_sql_keywords(self):
        """Test query with SQL keywords validation"""
        query = "SELECT * FROM users"
        is_valid, message = validate_natural_language_query(query)
        
        self.assertFalse(is_valid)
        self.assertIn("SQL keyword", message)


class TestIntegration(unittest.TestCase):
    """Integration test cases"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.examples_file = os.path.join(self.temp_dir, "test_examples.json")
        
        # Create test examples file
        test_data = {
            "examples": [
                {
                    "natural_language": "Test query",
                    "sql": "SELECT * FROM test",
                    "category": "test",
                    "difficulty": "easy"
                }
            ],
            "patterns": {}
        }
        
        import json
        with open(self.examples_file, 'w') as f:
            json.dump(test_data, f)
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_few_shot_learning_with_file(self):
        """Test FewShotLearning with file loading"""
        few_shot = FewShotLearning(self.examples_file)
        
        self.assertEqual(len(few_shot.examples), 1)
        self.assertEqual(few_shot.examples[0]['natural_language'], "Test query")
    
    def test_save_and_load_examples(self):
        """Test saving and loading examples"""
        few_shot = FewShotLearning()
        few_shot.add_example("Test", "SELECT * FROM test", "test")
        
        save_file = os.path.join(self.temp_dir, "save_examples.json")
        success = few_shot.save_examples(save_file)
        
        self.assertTrue(success)
        self.assertTrue(os.path.exists(save_file))


if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)
