"""
Database Schema Extractor
Extracts and formats database schema information for NL2SQL processing
"""

import logging
from typing import Dict, List, Optional, Tuple
from sqlalchemy import create_engine, MetaData, inspect, text
from sqlalchemy.exc import SQLAlchemyError
import pandas as pd

logger = logging.getLogger(__name__)


class SchemaExtractor:
    """Extracts database schema information for NL2SQL processing"""
    
    def __init__(self, database_url: str):
        """
        Initialize schema extractor with database connection
        
        Args:
            database_url: SQLAlchemy database URL
        """
        self.database_url = database_url
        self.engine = None
        self.inspector = None
        self.metadata = None
        
    def connect(self) -> bool:
        """
        Establish database connection
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            self.engine = create_engine(self.database_url)
            self.inspector = inspect(self.engine)
            self.metadata = MetaData()
            self.metadata.reflect(bind=self.engine)
            logger.info("Database connection established successfully")
            return True
        except SQLAlchemyError as e:
            logger.error(f"Failed to connect to database: {e}")
            return False
    
    def get_all_tables(self) -> List[str]:
        """
        Get all table names in the database
        
        Returns:
            List[str]: List of table names
        """
        if not self.inspector:
            return []
        return self.inspector.get_table_names()
    
    def get_table_schema(self, table_name: str) -> Dict:
        """
        Get detailed schema information for a specific table
        
        Args:
            table_name: Name of the table
            
        Returns:
            Dict: Schema information including columns, types, constraints
        """
        if not self.inspector:
            return {}
            
        try:
            columns = self.inspector.get_columns(table_name)
            primary_keys = self.inspector.get_pk_constraint(table_name)
            foreign_keys = self.inspector.get_foreign_keys(table_name)
            indexes = self.inspector.get_indexes(table_name)
            
            schema_info = {
                'table_name': table_name,
                'columns': columns,
                'primary_keys': primary_keys.get('constrained_columns', []),
                'foreign_keys': foreign_keys,
                'indexes': indexes
            }
            
            return schema_info
        except Exception as e:
            logger.error(f"Error extracting schema for table {table_name}: {e}")
            return {}
    
    def get_database_schema(self) -> Dict:
        """
        Get complete database schema information
        
        Returns:
            Dict: Complete database schema
        """
        if not self.connect():
            return {}
            
        schema = {
            'tables': {},
            'relationships': [],
            'summary': {}
        }
        
        tables = self.get_all_tables()
        
        for table in tables:
            table_schema = self.get_table_schema(table)
            if table_schema:
                schema['tables'][table] = table_schema
                
                # Extract relationships
                for fk in table_schema.get('foreign_keys', []):
                    relationship = {
                        'from_table': table,
                        'from_column': fk['constrained_columns'][0],
                        'to_table': fk['referred_table'],
                        'to_column': fk['referred_columns'][0]
                    }
                    schema['relationships'].append(relationship)
        
        # Create summary
        schema['summary'] = {
            'total_tables': len(tables),
            'total_columns': sum(len(table_info.get('columns', [])) 
                               for table_info in schema['tables'].values()),
            'total_relationships': len(schema['relationships'])
        }
        
        return schema
    
    def format_schema_for_prompt(self, schema: Dict) -> str:
        """
        Format schema information for use in NL2SQL prompts
        
        Args:
            schema: Database schema dictionary
            
        Returns:
            str: Formatted schema string for prompts
        """
        if not schema or 'tables' not in schema:
            return "No schema information available"
        
        formatted_schema = "Database Schema:\n\n"
        
        for table_name, table_info in schema['tables'].items():
            formatted_schema += f"Table: {table_name}\n"
            
            for column in table_info.get('columns', []):
                col_name = column['name']
                col_type = column['type']
                nullable = "NULL" if column.get('nullable', True) else "NOT NULL"
                
                formatted_schema += f"  - {col_name}: {col_type} ({nullable})\n"
            
            # Add primary key information
            pk_columns = table_info.get('primary_keys', [])
            if pk_columns:
                formatted_schema += f"  Primary Key: {', '.join(pk_columns)}\n"
            
            # Add foreign key information
            for fk in table_info.get('foreign_keys', []):
                from_col = fk['constrained_columns'][0]
                to_table = fk['referred_table']
                to_col = fk['referred_columns'][0]
                formatted_schema += f"  Foreign Key: {from_col} -> {to_table}.{to_col}\n"
            
            formatted_schema += "\n"
        
        return formatted_schema
    
    def get_sample_data(self, table_name: str, limit: int = 5) -> pd.DataFrame:
        """
        Get sample data from a table for better understanding
        
        Args:
            table_name: Name of the table
            limit: Number of sample rows to retrieve
            
        Returns:
            pd.DataFrame: Sample data from the table
        """
        if not self.engine:
            return pd.DataFrame()
            
        try:
            query = f"SELECT * FROM {table_name} LIMIT {limit}"
            return pd.read_sql(query, self.engine)
        except Exception as e:
            logger.error(f"Error getting sample data for table {table_name}: {e}")
            return pd.DataFrame()
    
    def validate_table_exists(self, table_name: str) -> bool:
        """
        Check if a table exists in the database
        
        Args:
            table_name: Name of the table to check
            
        Returns:
            bool: True if table exists, False otherwise
        """
        if not self.inspector:
            return False
        return table_name in self.get_all_tables()
    
    def get_column_info(self, table_name: str, column_name: str) -> Optional[Dict]:
        """
        Get specific column information
        
        Args:
            table_name: Name of the table
            column_name: Name of the column
            
        Returns:
            Optional[Dict]: Column information or None if not found
        """
        table_schema = self.get_table_schema(table_name)
        if not table_schema:
            return None
            
        for column in table_schema.get('columns', []):
            if column['name'] == column_name:
                return column
                
        return None
