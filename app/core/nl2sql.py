"""
Natural Language to SQL Query Generator
Main module that combines LangChain, T5 Transformers, and PostgreSQL for NL2SQL conversion
"""

import logging
import os
from typing import Dict, List, Optional, Tuple, Any
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from langchain_community.llms import HuggingFacePipeline
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from transformers import T5Tokenizer, T5ForConditionalGeneration, pipeline
import torch

from .schema_extractor import SchemaExtractor
from .query_validator import QueryValidator
from .few_shot_learning import FewShotLearning

logger = logging.getLogger(__name__)


class NL2SQLGenerator:
    """Main NL2SQL generator using LangChain and T5 Transformers"""
    
    def __init__(self, 
                 database_url: str,
                 model_name: str = "t5-base",
                 max_tokens: int = 512,
                 temperature: float = 0.7,
                 examples_file: Optional[str] = None):
        """
        Initialize the NL2SQL generator
        
        Args:
            database_url: PostgreSQL database connection URL
            model_name: T5 model name to use
            max_tokens: Maximum tokens for generation
            temperature: Sampling temperature
            examples_file: Path to few-shot learning examples file
        """
        self.database_url = database_url
        self.model_name = model_name
        self.max_tokens = max_tokens
        self.temperature = temperature
        
        # Initialize components
        self.schema_extractor = SchemaExtractor(database_url)
        self.query_validator = QueryValidator()
        self.few_shot_learning = FewShotLearning(examples_file)
        
        # Initialize model
        self.model = None
        self.tokenizer = None
        self.llm_chain = None
        
        # Load model
        self._load_model()
        
        # Extract schema
        self.schema_info = None
        self._extract_schema()
    
    def _load_model(self):
        """Load and initialize the T5 model"""
        try:
            logger.info(f"Loading T5 model: {self.model_name}")
            
            # Load tokenizer and model
            self.tokenizer = T5Tokenizer.from_pretrained(self.model_name)
            self.model = T5ForConditionalGeneration.from_pretrained(self.model_name)
            
            # Create pipeline
            pipe = pipeline(
                "text2text-generation",
                model=self.model,
                tokenizer=self.tokenizer,
                max_length=self.max_tokens,
                temperature=self.temperature,
                do_sample=True,
                top_p=0.95,
                repetition_penalty=1.15
            )
            
            # Create LangChain LLM
            llm = HuggingFacePipeline(pipeline=pipe)
            
            # Create prompt template
            prompt_template = PromptTemplate(
                input_variables=["schema", "examples", "query"],
                template="""
You are a SQL expert. Convert the natural language query to SQL.

Database Schema:
{schema}

{examples}

Natural Language Query: {query}

Generate only the SQL query without any explanation:
"""
            )
            
            # Create LangChain
            self.llm_chain = LLMChain(llm=llm, prompt=prompt_template)
            
            logger.info("Model loaded successfully")
            
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            raise
    
    def _extract_schema(self):
        """Extract database schema information"""
        try:
            logger.info("Extracting database schema")
            self.schema_info = self.schema_extractor.get_database_schema()
            logger.info(f"Schema extracted: {self.schema_info['summary']['total_tables']} tables")
        except Exception as e:
            logger.error(f"Error extracting schema: {e}")
            self.schema_info = {}
    
    def generate_sql(self, 
                    natural_language_query: str,
                    include_examples: bool = True,
                    max_examples: int = 3) -> Dict:
        """
        Generate SQL from natural language query
        
        Args:
            natural_language_query: Natural language query
            include_examples: Whether to include few-shot examples
            max_examples: Maximum number of examples to include
            
        Returns:
            Dict: Generated SQL and metadata
        """
        try:
            logger.info(f"Generating SQL for query: {natural_language_query}")
            
            # Prepare schema information
            schema_text = self.schema_extractor.format_schema_for_prompt(self.schema_info)
            
            # Get similar examples
            examples_text = ""
            if include_examples:
                similar_examples = self.few_shot_learning.get_similar_examples(
                    natural_language_query, max_examples
                )
                examples_text = self.few_shot_learning.format_examples_for_prompt(similar_examples)
            
            # Generate SQL using LangChain
            result = self.llm_chain.run({
                "schema": schema_text,
                "examples": examples_text,
                "query": natural_language_query
            })
            
            # Clean up the generated SQL
            generated_sql = self._clean_generated_sql(result)
            
            # Validate the generated SQL
            validation_result = self.query_validator.validate_query(
                generated_sql, self.schema_info
            )
            
            # Prepare response
            response = {
                "natural_language_query": natural_language_query,
                "generated_sql": generated_sql,
                "validation": validation_result,
                "schema_used": self.schema_info.get('summary', {}),
                "examples_used": len(similar_examples) if include_examples else 0,
                "model_info": {
                    "model_name": self.model_name,
                    "max_tokens": self.max_tokens,
                    "temperature": self.temperature
                }
            }
            
            logger.info(f"SQL generation completed. Valid: {validation_result['is_valid']}")
            return response
            
        except Exception as e:
            logger.error(f"Error generating SQL: {e}")
            return {
                "natural_language_query": natural_language_query,
                "generated_sql": "",
                "error": str(e),
                "validation": {"is_valid": False, "errors": [str(e)]}
            }
    
    def _clean_generated_sql(self, generated_text: str) -> str:
        """
        Clean and format generated SQL text
        
        Args:
            generated_text: Raw generated text from model
            
        Returns:
            str: Cleaned SQL query
        """
        # Remove extra whitespace and newlines
        sql = generated_text.strip()
        
        # Remove common prefixes/suffixes that models might add
        prefixes_to_remove = [
            "SQL:", "Query:", "SELECT", "Here's the SQL query:",
            "The SQL query is:", "Generated SQL:"
        ]
        
        for prefix in prefixes_to_remove:
            if sql.upper().startswith(prefix.upper()):
                sql = sql[len(prefix):].strip()
        
        # Ensure it starts with SELECT
        if not sql.upper().startswith("SELECT"):
            # Try to find SELECT in the text
            select_index = sql.upper().find("SELECT")
            if select_index != -1:
                sql = sql[select_index:]
            else:
                # If no SELECT found, this might be an error
                logger.warning("Generated text doesn't contain SELECT statement")
        
        # Remove trailing punctuation
        sql = sql.rstrip(".;")
        
        return sql
    
    def execute_query(self, sql_query: str, limit: int = 100) -> Dict:
        """
        Execute the generated SQL query and return results
        
        Args:
            sql_query: SQL query to execute
            limit: Maximum number of rows to return
            
        Returns:
            Dict: Query results and metadata
        """
        try:
            # Validate query before execution
            validation_result = self.query_validator.validate_query(sql_query, self.schema_info)
            
            if not validation_result['is_valid']:
                return {
                    "error": "Query validation failed",
                    "validation_errors": validation_result['errors'],
                    "results": None
                }
            
            # Check if query is read-only
            if not self.query_validator.is_read_only(sql_query):
                return {
                    "error": "Only SELECT queries are allowed for security reasons",
                    "results": None
                }
            
            # Add LIMIT if not present and query doesn't have aggregation
            if "LIMIT" not in sql_query.upper() and not any(
                keyword in sql_query.upper() for keyword in ["COUNT(", "SUM(", "AVG(", "MAX(", "MIN("]
            ):
                sql_query += f" LIMIT {limit}"
            
            # Execute query
            engine = create_engine(self.database_url)
            with engine.connect() as connection:
                result = connection.execute(text(sql_query))
                rows = result.fetchall()
                columns = result.keys()
                
                # Convert to DataFrame for easier handling
                df = pd.DataFrame(rows, columns=columns)
                
                return {
                    "results": df.to_dict('records'),
                    "row_count": len(df),
                    "column_count": len(df.columns),
                    "columns": list(df.columns),
                    "sql_executed": sql_query,
                    "validation": validation_result
                }
                
        except SQLAlchemyError as e:
            logger.error(f"Database error executing query: {e}")
            return {
                "error": f"Database error: {str(e)}",
                "results": None,
                "sql_executed": sql_query
            }
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            return {
                "error": f"Execution error: {str(e)}",
                "results": None,
                "sql_executed": sql_query
            }
    
    def generate_and_execute(self, 
                           natural_language_query: str,
                           include_examples: bool = True,
                           max_examples: int = 3,
                           execute_query: bool = True) -> Dict:
        """
        Generate SQL and optionally execute it
        
        Args:
            natural_language_query: Natural language query
            include_examples: Whether to include few-shot examples
            max_examples: Maximum number of examples to include
            execute_query: Whether to execute the generated query
            
        Returns:
            Dict: Complete response with generation and execution results
        """
        # Generate SQL
        generation_result = self.generate_sql(
            natural_language_query, include_examples, max_examples
        )
        
        response = {
            "generation": generation_result,
            "execution": None
        }
        
        # Execute if requested and generation was successful
        if execute_query and generation_result.get("generated_sql") and not generation_result.get("error"):
            execution_result = self.execute_query(generation_result["generated_sql"])
            response["execution"] = execution_result
        
        return response
    
    def add_example(self, natural_language: str, sql: str, category: str = "custom"):
        """
        Add a new example to the few-shot learning set
        
        Args:
            natural_language: Natural language query
            sql: Corresponding SQL query
            category: Category of the example
        """
        self.few_shot_learning.add_example(natural_language, sql, category)
    
    def get_schema_info(self) -> Dict:
        """
        Get current schema information
        
        Returns:
            Dict: Schema information
        """
        return self.schema_info
    
    def refresh_schema(self):
        """Refresh the database schema"""
        self._extract_schema()
    
    def get_statistics(self) -> Dict:
        """
        Get statistics about the NL2SQL system
        
        Returns:
            Dict: System statistics
        """
        few_shot_stats = self.few_shot_learning.get_statistics()
        
        return {
            "model_info": {
                "model_name": self.model_name,
                "max_tokens": self.max_tokens,
                "temperature": self.temperature
            },
            "schema_info": self.schema_info.get('summary', {}),
            "few_shot_learning": few_shot_stats,
            "validation_rules": {
                "dangerous_keywords": len(self.query_validator.dangerous_keywords),
                "read_only_keywords": len(self.query_validator.read_only_keywords)
            }
        }
    
    def update_model_parameters(self, 
                              max_tokens: Optional[int] = None,
                              temperature: Optional[float] = None):
        """
        Update model generation parameters
        
        Args:
            max_tokens: New maximum tokens
            temperature: New temperature
        """
        if max_tokens is not None:
            self.max_tokens = max_tokens
        
        if temperature is not None:
            self.temperature = temperature
        
        # Reload model with new parameters
        self._load_model()
