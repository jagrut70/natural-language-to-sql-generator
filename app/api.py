"""
FastAPI Backend for NL2SQL System
RESTful API endpoints for natural language to SQL conversion
"""

import os
import logging
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import our NL2SQL components
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Try to import the real NL2SQL generator, fallback to mock if it fails
try:
    from app.core.nl2sql import NL2SQLGenerator
    USE_MOCK_GENERATOR = False
except Exception as e:
    print(f"Warning: T5 model not available: {str(e)}")
    print("Using mock NL2SQL generator for demonstration...")
    from app.core.mock_nl2sql import MockNL2SQLGenerator as NL2SQLGenerator
    USE_MOCK_GENERATOR = True

from app.utils.helpers import validate_database_url, create_sample_database

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="NL2SQL Query Generator API",
    description="A powerful API for converting natural language to SQL queries using AI",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global NL2SQL generator instance
nl2sql_generator: Optional[NL2SQLGenerator] = None

# Pydantic models for request/response
class DatabaseConnectionRequest(BaseModel):
    database_url: str = Field(..., description="PostgreSQL database connection URL")
    model_name: str = Field(default="t5-base", description="T5 model name to use")
    max_tokens: int = Field(default=512, description="Maximum tokens for generation")
    temperature: float = Field(default=0.7, description="Sampling temperature")

class QueryRequest(BaseModel):
    natural_language_query: str = Field(..., description="Natural language query to convert")
    include_examples: bool = Field(default=True, description="Whether to include few-shot examples")
    max_examples: int = Field(default=3, description="Maximum number of examples to include")
    execute_query: bool = Field(default=True, description="Whether to execute the generated query")

class ExampleRequest(BaseModel):
    natural_language: str = Field(..., description="Natural language query")
    sql: str = Field(..., description="Corresponding SQL query")
    category: str = Field(default="custom", description="Category of the example")
    difficulty: str = Field(default="medium", description="Difficulty level")

class ModelUpdateRequest(BaseModel):
    max_tokens: Optional[int] = Field(None, description="New maximum tokens")
    temperature: Optional[float] = Field(None, description="New temperature")

class QueryResponse(BaseModel):
    natural_language_query: str
    generated_sql: str
    validation: Dict[str, Any]
    execution_results: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class SchemaResponse(BaseModel):
    tables: Dict[str, Any]
    relationships: List[Dict[str, Any]]
    summary: Dict[str, Any]

class StatisticsResponse(BaseModel):
    model_info: Dict[str, Any]
    schema_info: Dict[str, Any]
    few_shot_learning: Dict[str, Any]
    validation_rules: Dict[str, Any]

# Dependency to check if generator is initialized
def get_generator():
    if nl2sql_generator is None:
        raise HTTPException(
            status_code=400,
            detail="NL2SQL generator not initialized. Please connect to a database first."
        )
    return nl2sql_generator

@app.on_event("startup")
async def startup_event():
    """Initialize the application on startup"""
    logger.info("Starting NL2SQL API server...")

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "NL2SQL Query Generator API",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "generator_initialized": nl2sql_generator is not None
    }

@app.post("/connect")
async def connect_database(request: DatabaseConnectionRequest):
    """Connect to database and initialize NL2SQL generator"""
    global nl2sql_generator
    
    try:
        # Validate database URL
        is_valid, message = validate_database_url(request.database_url)
        if not is_valid:
            raise HTTPException(status_code=400, detail=message)
        
        # Initialize generator (will use mock if T5 model fails)
        try:
            nl2sql_generator = NL2SQLGenerator(
                database_url=request.database_url,
                model_name=request.model_name,
                max_tokens=request.max_tokens,
                temperature=request.temperature
            )
            generator_type = "T5" if not USE_MOCK_GENERATOR else "Mock"
        except Exception as model_error:
            # Fallback to mock generator if T5 model fails
            logger.warning(f"T5 model failed to load: {model_error}")
            logger.info("Falling back to mock NL2SQL generator...")
            from app.core.mock_nl2sql import MockNL2SQLGenerator
            nl2sql_generator = MockNL2SQLGenerator(database_url=request.database_url)
            generator_type = "Mock"
        
        logger.info(f"Connected to database: {request.database_url} using {generator_type} generator")
        
        # Get schema info (handle different method names)
        try:
            schema_info = nl2sql_generator.get_schema_info()
        except AttributeError:
            try:
                schema_info = nl2sql_generator.get_schema()
            except AttributeError:
                schema_info = {"tables": {}, "relationships": [], "summary": {}}
        
        # Ensure schema_info is serializable
        if not isinstance(schema_info, dict):
            schema_info = {"tables": {}, "relationships": [], "summary": {}}
        
        return {
            "message": f"Successfully connected to database using {generator_type} generator",
            "database_url": request.database_url,
            "model_name": request.model_name,
            "generator_type": generator_type,
            "schema_info": schema_info
        }
        
    except Exception as e:
        logger.error(f"Error connecting to database: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/create-sample-database")
async def create_sample_database_endpoint(database_url: str):
    """Create a sample database with example data"""
    try:
        success = create_sample_database(database_url)
        
        if success:
            return {"message": "Sample database created successfully"}
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to create sample database. Check your database URL and permissions."
            )
            
    except Exception as e:
        logger.error(f"Error creating sample database: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate-sql", response_model=QueryResponse)
async def generate_sql(request: QueryRequest, generator: NL2SQLGenerator = Depends(get_generator)):
    """Generate SQL from natural language query"""
    try:
        # Handle different method names for real vs mock generator
        try:
            # Try real generator method
            result = generator.generate_and_execute(
                natural_language_query=request.natural_language_query,
                include_examples=request.include_examples,
                max_examples=request.max_examples,
                execute_query=request.execute_query
            )
            generation = result.get('generation', {})
            execution = result.get('execution')
        except AttributeError:
            # Use mock generator method
            result = generator.generate_sql(request.natural_language_query)
            generation = {
                'generated_sql': result.get('sql_query', ''),
                'validation': result.get('validation', {}),
                'error': result.get('explanation', '')
            }
            execution = None
            if request.execute_query and result.get('sql_query'):
                execution = generator.execute_sql(result.get('sql_query'))
        
        return QueryResponse(
            natural_language_query=request.natural_language_query,
            generated_sql=generation.get('generated_sql', ''),
            validation=generation.get('validation', {}),
            execution_results=execution,
            error=generation.get('error')
        )
        
    except Exception as e:
        logger.error(f"Error generating SQL: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/execute-sql")
async def execute_sql(sql_query: str, generator: NL2SQLGenerator = Depends(get_generator)):
    """Execute a SQL query directly"""
    try:
        # Handle different method names for real vs mock generator
        try:
            result = generator.execute_query(sql_query)
        except AttributeError:
            result = generator.execute_sql(sql_query)
        
        if result.get('error'):
            raise HTTPException(status_code=400, detail=result['error'])
        
        return result
        
    except Exception as e:
        logger.error(f"Error executing SQL: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/schema", response_model=SchemaResponse)
async def get_schema(generator: NL2SQLGenerator = Depends(get_generator)):
    """Get database schema information"""
    try:
        # Handle different method names for real vs mock generator
        try:
            schema_info = generator.get_schema_info()
        except AttributeError:
            schema_info = generator.get_schema()
        
        return SchemaResponse(
            tables=schema_info.get('tables', {}),
            relationships=schema_info.get('relationships', []),
            summary=schema_info.get('summary', {})
        )
        
    except Exception as e:
        logger.error(f"Error getting schema: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/refresh-schema")
async def refresh_schema(generator: NL2SQLGenerator = Depends(get_generator)):
    """Refresh database schema"""
    try:
        generator.refresh_schema()
        return {"message": "Schema refreshed successfully"}
        
    except Exception as e:
        logger.error(f"Error refreshing schema: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/add-example")
async def add_example(request: ExampleRequest, generator: NL2SQLGenerator = Depends(get_generator)):
    """Add a new example to few-shot learning"""
    try:
        generator.add_example(
            natural_language=request.natural_language,
            sql=request.sql,
            category=request.category
        )
        
        return {"message": "Example added successfully"}
        
    except Exception as e:
        logger.error(f"Error adding example: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/examples")
async def get_examples(
    category: Optional[str] = None,
    difficulty: Optional[str] = None,
    generator: NL2SQLGenerator = Depends(get_generator)
):
    """Get few-shot learning examples"""
    try:
        # Handle different method names for real vs mock generator
        try:
            if category:
                examples = generator.few_shot_learning.get_examples_by_category(category)
            elif difficulty:
                examples = generator.few_shot_learning.get_examples_by_difficulty(difficulty)
            else:
                examples = generator.few_shot_learning.examples
        except AttributeError:
            # Use mock generator method
            examples = generator.get_examples()
            if category:
                examples = [ex for ex in examples if ex.get('category') == category]
            if difficulty:
                examples = [ex for ex in examples if ex.get('difficulty') == difficulty]
        
        return {"examples": examples}
        
    except Exception as e:
        logger.error(f"Error getting examples: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/update-model")
async def update_model(request: ModelUpdateRequest, generator: NL2SQLGenerator = Depends(get_generator)):
    """Update model parameters"""
    try:
        generator.update_model_parameters(
            max_tokens=request.max_tokens,
            temperature=request.temperature
        )
        
        return {"message": "Model parameters updated successfully"}
        
    except Exception as e:
        logger.error(f"Error updating model: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/statistics", response_model=StatisticsResponse)
async def get_statistics(generator: NL2SQLGenerator = Depends(get_generator)):
    """Get system statistics"""
    try:
        stats = generator.get_statistics()
        
        return StatisticsResponse(
            model_info=stats.get('model_info', {}),
            schema_info=stats.get('schema_info', {}),
            few_shot_learning=stats.get('few_shot_learning', {}),
            validation_rules=stats.get('validation_rules', {})
        )
        
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/validate-query")
async def validate_query(sql_query: str, generator: NL2SQLGenerator = Depends(get_generator)):
    """Validate a SQL query"""
    try:
        validation_result = generator.query_validator.validate_query(
            sql_query, generator.get_schema_info()
        )
        
        return validation_result
        
    except Exception as e:
        logger.error(f"Error validating query: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/batch-generate")
async def batch_generate_sql(
    queries: List[str],
    background_tasks: BackgroundTasks,
    generator: NL2SQLGenerator = Depends(get_generator)
):
    """Generate SQL for multiple queries in batch"""
    try:
        results = []
        
        for query in queries:
            try:
                result = generator.generate_sql(query)
                results.append({
                    "query": query,
                    "result": result,
                    "success": True
                })
            except Exception as e:
                results.append({
                    "query": query,
                    "error": str(e),
                    "success": False
                })
        
        return {"results": results}
        
    except Exception as e:
        logger.error(f"Error in batch generation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/models")
async def get_available_models():
    """Get list of available T5 models"""
    return {
        "models": [
            {"name": "t5-small", "description": "Small T5 model (60M parameters)"},
            {"name": "t5-base", "description": "Base T5 model (220M parameters)"},
            {"name": "t5-large", "description": "Large T5 model (770M parameters)"},
            {"name": "t5-3b", "description": "3B parameter T5 model"},
            {"name": "t5-11b", "description": "11B parameter T5 model"}
        ]
    }

@app.delete("/disconnect")
async def disconnect():
    """Disconnect from database and cleanup"""
    global nl2sql_generator
    
    if nl2sql_generator:
        nl2sql_generator = None
        return {"message": "Disconnected successfully"}
    else:
        return {"message": "No active connection to disconnect"}

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return {"error": "Endpoint not found", "detail": str(exc)}

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    return {"error": "Internal server error", "detail": str(exc)}

if __name__ == "__main__":
    # Get configuration from environment
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", 8000))
    
    # Run the server
    uvicorn.run(
        "app.api:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )
