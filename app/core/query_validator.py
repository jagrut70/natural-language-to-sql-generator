"""
Query Validator Module
Validates generated SQL queries for safety, syntax, and correctness
"""

import logging
import re
from typing import Dict, List, Optional, Tuple, Set
import sqlparse
from sqlparse.sql import Token, TokenList, Identifier, IdentifierList
from sqlparse.tokens import Keyword, Name, Punctuation, Whitespace

logger = logging.getLogger(__name__)


class QueryValidator:
    """Validates SQL queries for safety and correctness"""
    
    def __init__(self):
        """Initialize the query validator"""
        self.dangerous_keywords = {
            'DROP', 'DELETE', 'TRUNCATE', 'ALTER', 'CREATE', 'INSERT', 
            'UPDATE', 'GRANT', 'REVOKE', 'EXECUTE', 'EXEC'
        }
        
        self.read_only_keywords = {
            'SELECT', 'SHOW', 'DESCRIBE', 'EXPLAIN', 'WITH'
        }
        
        self.required_keywords = {
            'SELECT'
        }
        
        self.forbidden_patterns = [
            r'DROP\s+TABLE',
            r'DELETE\s+FROM\s+\w+\s+WHERE\s+1\s*=\s*1',
            r'TRUNCATE\s+TABLE',
            r'ALTER\s+TABLE',
            r'CREATE\s+TABLE',
            r'INSERT\s+INTO',
            r'UPDATE\s+\w+\s+SET',
            r';\s*DROP',
            r';\s*DELETE',
            r';\s*TRUNCATE',
            r';\s*ALTER',
            r';\s*CREATE',
            r';\s*INSERT',
            r';\s*UPDATE'
        ]
    
    def validate_query(self, sql_query: str, schema_info: Optional[Dict] = None) -> Dict:
        """
        Comprehensive validation of SQL query
        
        Args:
            sql_query: SQL query to validate
            schema_info: Database schema information for validation
            
        Returns:
            Dict: Validation results with status and details
        """
        validation_result = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'suggestions': [],
            'query_type': 'unknown',
            'tables_used': [],
            'columns_used': []
        }
        
        try:
            # Basic syntax validation
            syntax_result = self._validate_syntax(sql_query)
            if not syntax_result['is_valid']:
                validation_result['is_valid'] = False
                validation_result['errors'].extend(syntax_result['errors'])
                return validation_result
            
            # Security validation
            security_result = self._validate_security(sql_query)
            if not security_result['is_valid']:
                validation_result['is_valid'] = False
                validation_result['errors'].extend(security_result['errors'])
            
            # Extract query information
            query_info = self._extract_query_info(sql_query)
            validation_result['query_type'] = query_info['query_type']
            validation_result['tables_used'] = query_info['tables_used']
            validation_result['columns_used'] = query_info['columns_used']
            
            # Schema validation (if schema provided)
            if schema_info:
                schema_result = self._validate_against_schema(sql_query, schema_info)
                if not schema_result['is_valid']:
                    validation_result['is_valid'] = False
                    validation_result['errors'].extend(schema_result['errors'])
                validation_result['warnings'].extend(schema_result['warnings'])
            
            # Performance validation
            performance_result = self._validate_performance(sql_query)
            validation_result['warnings'].extend(performance_result['warnings'])
            validation_result['suggestions'].extend(performance_result['suggestions'])
            
        except Exception as e:
            validation_result['is_valid'] = False
            validation_result['errors'].append(f"Validation error: {str(e)}")
            logger.error(f"Error during query validation: {e}")
        
        return validation_result
    
    def _validate_syntax(self, sql_query: str) -> Dict:
        """
        Validate SQL syntax using sqlparse
        
        Args:
            sql_query: SQL query to validate
            
        Returns:
            Dict: Syntax validation results
        """
        result = {
            'is_valid': True,
            'errors': []
        }
        
        try:
            # Parse the SQL query
            parsed = sqlparse.parse(sql_query)
            
            if not parsed:
                result['is_valid'] = False
                result['errors'].append("Empty or invalid SQL query")
                return result
            
            # Check if it's a valid SELECT statement
            statement = parsed[0]
            if not self._is_select_statement(statement):
                result['is_valid'] = False
                result['errors'].append("Query must be a SELECT statement")
            
        except Exception as e:
            result['is_valid'] = False
            result['errors'].append(f"Syntax error: {str(e)}")
        
        return result
    
    def _validate_security(self, sql_query: str) -> Dict:
        """
        Validate query for security concerns
        
        Args:
            sql_query: SQL query to validate
            
        Returns:
            Dict: Security validation results
        """
        result = {
            'is_valid': True,
            'errors': []
        }
        
        sql_upper = sql_query.upper()
        
        # Check for dangerous keywords
        for keyword in self.dangerous_keywords:
            if keyword in sql_upper:
                result['is_valid'] = False
                result['errors'].append(f"Dangerous keyword '{keyword}' detected")
        
        # Check for forbidden patterns
        for pattern in self.forbidden_patterns:
            if re.search(pattern, sql_upper, re.IGNORECASE):
                result['is_valid'] = False
                result['errors'].append(f"Forbidden pattern detected: {pattern}")
        
        # Check for multiple statements
        if sql_query.count(';') > 1:
            result['is_valid'] = False
            result['errors'].append("Multiple SQL statements not allowed")
        
        # Check for comments that might hide malicious code
        if '--' in sql_query or '/*' in sql_query:
            result['is_valid'] = False
            result['errors'].append("SQL comments not allowed for security reasons")
        
        return result
    
    def _extract_query_info(self, sql_query: str) -> Dict:
        """
        Extract information about the SQL query
        
        Args:
            sql_query: SQL query to analyze
            
        Returns:
            Dict: Query information
        """
        result = {
            'query_type': 'unknown',
            'tables_used': [],
            'columns_used': []
        }
        
        try:
            parsed = sqlparse.parse(sql_query)
            if not parsed:
                return result
            
            statement = parsed[0]
            
            # Determine query type
            if self._is_select_statement(statement):
                result['query_type'] = 'SELECT'
            
            # Extract tables and columns
            tables, columns = self._extract_tables_and_columns(statement)
            result['tables_used'] = tables
            result['columns_used'] = columns
            
        except Exception as e:
            logger.error(f"Error extracting query info: {e}")
        
        return result
    
    def _validate_against_schema(self, sql_query: str, schema_info: Dict) -> Dict:
        """
        Validate query against database schema
        
        Args:
            sql_query: SQL query to validate
            schema_info: Database schema information
            
        Returns:
            Dict: Schema validation results
        """
        result = {
            'is_valid': True,
            'errors': [],
            'warnings': []
        }
        
        try:
            query_info = self._extract_query_info(sql_query)
            available_tables = set(schema_info.get('tables', {}).keys())
            
            # Check if all tables exist
            for table in query_info['tables_used']:
                if table not in available_tables:
                    result['is_valid'] = False
                    result['errors'].append(f"Table '{table}' does not exist in schema")
            
            # Check if columns exist in tables
            for column_info in query_info['columns_used']:
                table_name = column_info.get('table')
                column_name = column_info.get('column')
                
                if table_name and table_name in schema_info.get('tables', {}):
                    table_schema = schema_info['tables'][table_name]
                    available_columns = {col['name'] for col in table_schema.get('columns', [])}
                    
                    if column_name and column_name not in available_columns:
                        result['warnings'].append(f"Column '{column_name}' not found in table '{table_name}'")
            
        except Exception as e:
            logger.error(f"Error validating against schema: {e}")
            result['warnings'].append(f"Schema validation error: {str(e)}")
        
        return result
    
    def _validate_performance(self, sql_query: str) -> Dict:
        """
        Validate query for performance concerns
        
        Args:
            sql_query: SQL query to validate
            
        Returns:
            Dict: Performance validation results
        """
        result = {
            'warnings': [],
            'suggestions': []
        }
        
        sql_upper = sql_query.upper()
        
        # Check for SELECT * without LIMIT
        if 'SELECT *' in sql_upper and 'LIMIT' not in sql_upper:
            result['warnings'].append("SELECT * without LIMIT may return large datasets")
            result['suggestions'].append("Consider adding LIMIT clause or selecting specific columns")
        
        # Check for missing WHERE clause on large tables
        if 'SELECT' in sql_upper and 'WHERE' not in sql_upper:
            result['suggestions'].append("Consider adding WHERE clause for better performance")
        
        # Check for potential cartesian products
        if sql_upper.count('FROM') > 1 and 'JOIN' not in sql_upper:
            result['warnings'].append("Multiple FROM clauses without JOIN may cause cartesian products")
        
        # Check for ORDER BY without LIMIT
        if 'ORDER BY' in sql_upper and 'LIMIT' not in sql_upper:
            result['suggestions'].append("Consider adding LIMIT with ORDER BY for better performance")
        
        return result
    
    def _is_select_statement(self, statement) -> bool:
        """
        Check if parsed statement is a SELECT statement
        
        Args:
            statement: Parsed SQL statement
            
        Returns:
            bool: True if SELECT statement
        """
        # Check if the first token is SELECT
        if statement.tokens and hasattr(statement.tokens[0], 'value'):
            return statement.tokens[0].value.upper() == 'SELECT'
        
        # Fallback: check all tokens
        for token in statement.tokens:
            if hasattr(token, 'ttype') and token.ttype is Keyword and token.value.upper() == 'SELECT':
                return True
            elif hasattr(token, 'value') and token.value.upper() == 'SELECT':
                return True
        
        return False
    
    def _extract_tables_and_columns(self, statement) -> Tuple[List[str], List[Dict]]:
        """
        Extract table and column information from parsed statement
        
        Args:
            statement: Parsed SQL statement
            
        Returns:
            Tuple[List[str], List[Dict]]: Tables and columns used
        """
        tables = []
        columns = []
        
        def extract_from_tokens(tokens):
            for token in tokens:
                if hasattr(token, 'tokens'):
                    extract_from_tokens(token.tokens)
                elif token.ttype is Name:
                    # This could be a table or column name
                    tables.append(token.value)
                elif isinstance(token, Identifier):
                    # Handle qualified names (table.column)
                    if '.' in token.value:
                        parts = token.value.split('.')
                        if len(parts) == 2:
                            columns.append({
                                'table': parts[0],
                                'column': parts[1]
                            })
                    else:
                        columns.append({
                            'table': None,
                            'column': token.value
                        })
        
        extract_from_tokens(statement.tokens)
        
        return list(set(tables)), columns
    
    def sanitize_query(self, sql_query: str) -> str:
        """
        Sanitize SQL query for safe execution
        
        Args:
            sql_query: SQL query to sanitize
            
        Returns:
            str: Sanitized SQL query
        """
        # Remove comments
        sql_query = re.sub(r'--.*$', '', sql_query, flags=re.MULTILINE)
        sql_query = re.sub(r'/\*.*?\*/', '', sql_query, flags=re.DOTALL)
        
        # Remove extra whitespace
        sql_query = re.sub(r'\s+', ' ', sql_query).strip()
        
        # Ensure single statement
        if ';' in sql_query:
            sql_query = sql_query.split(';')[0].strip()
        
        return sql_query
    
    def is_read_only(self, sql_query: str) -> bool:
        """
        Check if query is read-only
        
        Args:
            sql_query: SQL query to check
            
        Returns:
            bool: True if read-only
        """
        sql_upper = sql_query.upper()
        
        # Check for write operations
        for keyword in self.dangerous_keywords:
            if keyword in sql_upper:
                return False
        
        # Check for read operations
        for keyword in self.read_only_keywords:
            if keyword in sql_upper:
                return True
        
        return False
    
    def get_query_complexity_score(self, sql_query: str) -> int:
        """
        Calculate complexity score for the query
        
        Args:
            sql_query: SQL query to analyze
            
        Returns:
            int: Complexity score (1-10, higher is more complex)
        """
        score = 1
        sql_upper = sql_query.upper()
        
        # Add points for various complexity factors
        if 'JOIN' in sql_upper:
            score += 2
        if 'GROUP BY' in sql_upper:
            score += 1
        if 'HAVING' in sql_upper:
            score += 1
        if 'ORDER BY' in sql_upper:
            score += 1
        if 'LIMIT' in sql_upper:
            score += 1
        if 'WHERE' in sql_upper:
            score += 1
        if 'DISTINCT' in sql_upper:
            score += 1
        if 'UNION' in sql_upper:
            score += 2
        if 'SUBQUERY' in sql_upper or '(' in sql_upper:
            score += 2
        
        return min(score, 10)
