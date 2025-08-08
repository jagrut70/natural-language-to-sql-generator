"""
Few-Shot Learning Module
Provides example queries and patterns to improve SQL generation accuracy
"""

import json
import logging
from typing import Dict, List, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


class FewShotLearning:
    """Manages few-shot learning examples for NL2SQL"""
    
    def __init__(self, examples_file: Optional[str] = None):
        """
        Initialize few-shot learning with examples
        
        Args:
            examples_file: Path to JSON file containing example queries
        """
        self.examples = []
        self.patterns = {}
        
        if examples_file:
            self.load_examples(examples_file)
        else:
            self._load_default_examples()
    
    def _load_default_examples(self):
        """Load default few-shot learning examples"""
        self.examples = [
            {
                "natural_language": "Show me all users",
                "sql": "SELECT * FROM users",
                "category": "basic_select",
                "difficulty": "easy"
            },
            {
                "natural_language": "Find users who signed up last month",
                "sql": "SELECT * FROM users WHERE created_at >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month') AND created_at < DATE_TRUNC('month', CURRENT_DATE)",
                "category": "date_filtering",
                "difficulty": "medium"
            },
            {
                "natural_language": "Count the number of orders per customer",
                "sql": "SELECT customer_id, COUNT(*) as order_count FROM orders GROUP BY customer_id",
                "category": "aggregation",
                "difficulty": "medium"
            },
            {
                "natural_language": "Get the top 10 customers by total order value",
                "sql": "SELECT customer_id, SUM(order_total) as total_value FROM orders GROUP BY customer_id ORDER BY total_value DESC LIMIT 10",
                "category": "aggregation_ordering",
                "difficulty": "hard"
            },
            {
                "natural_language": "Show me products and their categories",
                "sql": "SELECT p.name, c.name as category_name FROM products p JOIN categories c ON p.category_id = c.id",
                "category": "joins",
                "difficulty": "medium"
            },
            {
                "natural_language": "Find customers who have placed more than 5 orders",
                "sql": "SELECT customer_id FROM orders GROUP BY customer_id HAVING COUNT(*) > 5",
                "category": "having_clause",
                "difficulty": "hard"
            },
            {
                "natural_language": "Get the average order value by month",
                "sql": "SELECT DATE_TRUNC('month', order_date) as month, AVG(order_total) as avg_order_value FROM orders GROUP BY DATE_TRUNC('month', order_date) ORDER BY month",
                "category": "date_aggregation",
                "difficulty": "hard"
            },
            {
                "natural_language": "Find products that are out of stock",
                "sql": "SELECT * FROM products WHERE stock_quantity = 0",
                "category": "condition_filtering",
                "difficulty": "easy"
            },
            {
                "natural_language": "Show me the most expensive product in each category",
                "sql": "SELECT p.name, p.price, c.name as category FROM products p JOIN categories c ON p.category_id = c.id WHERE p.price = (SELECT MAX(price) FROM products WHERE category_id = p.category_id)",
                "category": "subqueries",
                "difficulty": "hard"
            },
            {
                "natural_language": "Get customers who haven't placed any orders",
                "sql": "SELECT * FROM customers WHERE id NOT IN (SELECT DISTINCT customer_id FROM orders)",
                "category": "not_in_subquery",
                "difficulty": "hard"
            }
        ]
        
        # Define common patterns
        self.patterns = {
            "count": {
                "keywords": ["count", "number of", "how many", "total"],
                "sql_template": "SELECT COUNT(*) FROM {table}",
                "description": "Counting records"
            },
            "sum": {
                "keywords": ["sum", "total", "sum of", "add up"],
                "sql_template": "SELECT SUM({column}) FROM {table}",
                "description": "Summing values"
            },
            "average": {
                "keywords": ["average", "avg", "mean", "average of"],
                "sql_template": "SELECT AVG({column}) FROM {table}",
                "description": "Calculating averages"
            },
            "group_by": {
                "keywords": ["per", "by", "group by", "for each"],
                "sql_template": "SELECT {columns} FROM {table} GROUP BY {group_columns}",
                "description": "Grouping results"
            },
            "order_by": {
                "keywords": ["order by", "sort by", "highest", "lowest", "top", "bottom"],
                "sql_template": "SELECT {columns} FROM {table} ORDER BY {order_column} {direction}",
                "description": "Ordering results"
            },
            "date_filter": {
                "keywords": ["today", "yesterday", "last week", "last month", "this year"],
                "sql_template": "SELECT {columns} FROM {table} WHERE {date_column} {condition}",
                "description": "Date-based filtering"
            }
        }
    
    def load_examples(self, file_path: str) -> bool:
        """
        Load examples from a JSON file
        
        Args:
            file_path: Path to the JSON file
            
        Returns:
            bool: True if loaded successfully, False otherwise
        """
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                self.examples = data.get('examples', [])
                self.patterns = data.get('patterns', {})
            logger.info(f"Loaded {len(self.examples)} examples from {file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to load examples from {file_path}: {e}")
            return False
    
    def save_examples(self, file_path: str) -> bool:
        """
        Save examples to a JSON file
        
        Args:
            file_path: Path to save the JSON file
            
        Returns:
            bool: True if saved successfully, False otherwise
        """
        try:
            data = {
                'examples': self.examples,
                'patterns': self.patterns
            }
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved {len(self.examples)} examples to {file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save examples to {file_path}: {e}")
            return False
    
    def add_example(self, natural_language: str, sql: str, category: str = "custom", difficulty: str = "medium"):
        """
        Add a new example to the few-shot learning set
        
        Args:
            natural_language: Natural language query
            sql: Corresponding SQL query
            category: Category of the query
            difficulty: Difficulty level (easy, medium, hard)
        """
        example = {
            "natural_language": natural_language,
            "sql": sql,
            "category": category,
            "difficulty": difficulty
        }
        self.examples.append(example)
        logger.info(f"Added new example: {natural_language}")
    
    def get_examples_by_category(self, category: str) -> List[Dict]:
        """
        Get examples filtered by category
        
        Args:
            category: Category to filter by
            
        Returns:
            List[Dict]: List of examples in the specified category
        """
        return [ex for ex in self.examples if ex.get('category') == category]
    
    def get_examples_by_difficulty(self, difficulty: str) -> List[Dict]:
        """
        Get examples filtered by difficulty
        
        Args:
            difficulty: Difficulty level to filter by
            
        Returns:
            List[Dict]: List of examples with the specified difficulty
        """
        return [ex for ex in self.examples if ex.get('difficulty') == difficulty]
    
    def get_similar_examples(self, query: str, limit: int = 3) -> List[Dict]:
        """
        Find examples similar to the given query
        
        Args:
            query: Natural language query to find similar examples for
            limit: Maximum number of similar examples to return
            
        Returns:
            List[Dict]: List of similar examples
        """
        # Simple keyword-based similarity
        query_lower = query.lower()
        similarities = []
        
        for example in self.examples:
            example_text = example['natural_language'].lower()
            common_words = set(query_lower.split()) & set(example_text.split())
            similarity_score = len(common_words) / max(len(query_lower.split()), len(example_text.split()))
            
            if similarity_score > 0.1:  # Threshold for similarity
                similarities.append((similarity_score, example))
        
        # Sort by similarity score and return top results
        similarities.sort(key=lambda x: x[0], reverse=True)
        return [ex for _, ex in similarities[:limit]]
    
    def get_patterns_for_query(self, query: str) -> List[Dict]:
        """
        Identify patterns that match the given query
        
        Args:
            query: Natural language query
            
        Returns:
            List[Dict]: List of matching patterns
        """
        query_lower = query.lower()
        matching_patterns = []
        
        for pattern_name, pattern_info in self.patterns.items():
            for keyword in pattern_info.get('keywords', []):
                if keyword in query_lower:
                    matching_patterns.append({
                        'name': pattern_name,
                        'info': pattern_info,
                        'matched_keyword': keyword
                    })
                    break
        
        return matching_patterns
    
    def format_examples_for_prompt(self, examples: List[Dict]) -> str:
        """
        Format examples for use in prompts
        
        Args:
            examples: List of example dictionaries
            
        Returns:
            str: Formatted examples string
        """
        if not examples:
            return ""
        
        formatted = "Example queries:\n\n"
        
        for i, example in enumerate(examples, 1):
            formatted += f"Example {i}:\n"
            formatted += f"Natural Language: {example['natural_language']}\n"
            formatted += f"SQL: {example['sql']}\n\n"
        
        return formatted
    
    def get_training_data(self) -> Tuple[List[str], List[str]]:
        """
        Get training data for model fine-tuning
        
        Returns:
            Tuple[List[str], List[str]]: Natural language queries and corresponding SQL
        """
        nl_queries = [ex['natural_language'] for ex in self.examples]
        sql_queries = [ex['sql'] for ex in self.examples]
        return nl_queries, sql_queries
    
    def validate_example(self, natural_language: str, sql: str) -> bool:
        """
        Validate if an example is properly formatted
        
        Args:
            natural_language: Natural language query
            sql: SQL query
            
        Returns:
            bool: True if valid, False otherwise
        """
        if not natural_language or not sql:
            return False
        
        # Basic SQL validation
        sql_upper = sql.upper()
        if not any(keyword in sql_upper for keyword in ['SELECT', 'FROM']):
            return False
        
        return True
    
    def get_statistics(self) -> Dict:
        """
        Get statistics about the few-shot learning examples
        
        Returns:
            Dict: Statistics about examples and patterns
        """
        categories = {}
        difficulties = {}
        
        for example in self.examples:
            category = example.get('category', 'unknown')
            difficulty = example.get('difficulty', 'unknown')
            
            categories[category] = categories.get(category, 0) + 1
            difficulties[difficulty] = difficulties.get(difficulty, 0) + 1
        
        return {
            'total_examples': len(self.examples),
            'total_patterns': len(self.patterns),
            'categories': categories,
            'difficulties': difficulties
        }
