"""
Streamlit Web Interface for NL2SQL System
A beautiful and modern web interface for natural language to SQL conversion
"""

import streamlit as st
import pandas as pd
import json
import os
from typing import Dict, List, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import our NL2SQL components
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Try to import the real NL2SQL generator, fallback to mock if it fails
try:
    from app.core.nl2sql import NL2SQLGenerator
    USE_MOCK_GENERATOR = False
except Exception as e:
    st.warning(f"⚠️ T5 model not available: {str(e)}")
    st.info("🔄 Using mock NL2SQL generator for demonstration...")
    from app.core.mock_nl2sql import MockNL2SQLGenerator as NL2SQLGenerator
    USE_MOCK_GENERATOR = True

from app.utils.helpers import (
    validate_database_url, 
    create_sample_database, 
    format_sql, 
    validate_natural_language_query,
    format_results_for_display
)

# Page configuration
st.set_page_config(
    page_title="NL2SQL Query Generator",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 5px;
        padding: 1rem;
        margin: 1rem 0;
    }
    .error-box {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        border-radius: 5px;
        padding: 1rem;
        margin: 1rem 0;
    }
    .info-box {
        background-color: #d1ecf1;
        border: 1px solid #bee5eb;
        border-radius: 5px;
        padding: 1rem;
        margin: 1rem 0;
    }
    .sql-box {
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 5px;
        padding: 1rem;
        margin: 1rem 0;
        font-family: 'Courier New', monospace;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'nl2sql_generator' not in st.session_state:
    st.session_state.nl2sql_generator = None
if 'database_connected' not in st.session_state:
    st.session_state.database_connected = False
if 'schema_info' not in st.session_state:
    st.session_state.schema_info = None

def main():
    """Main application function"""
    
    # Header
    st.markdown('<h1 class="main-header">🔍 NL2SQL Query Generator</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Convert natural language to SQL queries using AI</p>', unsafe_allow_html=True)
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Database connection
        st.subheader("Database Connection")
        database_url = st.text_input(
            "Database URL",
            value="postgresql://username:password@localhost:5432/database_name",
            help="PostgreSQL connection URL"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔗 Connect"):
                connect_to_database(database_url)
        
        with col2:
            if st.button("📊 Create Sample DB"):
                create_sample_database_ui(database_url)
        
        # Model configuration
        st.subheader("Model Settings")
        model_name = st.selectbox(
            "Model",
            ["t5-base", "t5-small", "t5-large"],
            index=0
        )
        
        max_tokens = st.slider("Max Tokens", 100, 1000, 512)
        temperature = st.slider("Temperature", 0.1, 1.0, 0.7, 0.1)
        
        # Few-shot learning settings
        st.subheader("Few-Shot Learning")
        include_examples = st.checkbox("Include Examples", value=True)
        max_examples = st.slider("Max Examples", 1, 10, 3)
        
        # Update model if parameters changed
        if st.button("🔄 Update Model"):
            update_model_parameters(model_name, max_tokens, temperature)
    
    # Main content area
    if st.session_state.database_connected:
        show_main_interface(include_examples, max_examples)
    else:
        show_connection_instructions()

def connect_to_database(database_url: str):
    """Connect to the database and initialize the NL2SQL generator"""
    try:
        # Validate database URL
        is_valid, message = validate_database_url(database_url)
        
        if not is_valid:
            st.error(f"❌ {message}")
            return
        
        # Initialize NL2SQL generator
        with st.spinner("🔄 Connecting to database and loading model..."):
            st.session_state.nl2sql_generator = NL2SQLGenerator(
                database_url=database_url,
                model_name="t5-base",  # Will be updated later
                max_tokens=512,
                temperature=0.7
            )
            
            # Get schema information
            st.session_state.schema_info = st.session_state.nl2sql_generator.get_schema_info()
            st.session_state.database_connected = True
        
        st.success("✅ Connected to database successfully!")
        
    except Exception as e:
        st.error(f"❌ Error connecting to database: {str(e)}")
        logger.error(f"Database connection error: {e}")

def create_sample_database_ui(database_url: str):
    """Create sample database with UI feedback"""
    try:
        with st.spinner("🔄 Creating sample database..."):
            success = create_sample_database(database_url)
            
        if success:
            st.success("✅ Sample database created successfully!")
            st.info("You can now connect to the database using the Connect button.")
        else:
            st.error("❌ Failed to create sample database. Check your database URL and permissions.")
            
    except Exception as e:
        st.error(f"❌ Error creating sample database: {str(e)}")

def update_model_parameters(model_name: str, max_tokens: int, temperature: float):
    """Update model parameters"""
    if st.session_state.nl2sql_generator:
        try:
            with st.spinner("🔄 Updating model parameters..."):
                st.session_state.nl2sql_generator.update_model_parameters(
                    max_tokens=max_tokens,
                    temperature=temperature
                )
            st.success("✅ Model parameters updated successfully!")
        except Exception as e:
            st.error(f"❌ Error updating model parameters: {str(e)}")
    else:
        st.error("❌ Please connect to a database first.")

def show_connection_instructions():
    """Show instructions for connecting to database"""
    st.markdown("""
    ## 🚀 Getting Started
    
    ### 1. Database Connection
    To use the NL2SQL Query Generator, you need to connect to a PostgreSQL database.
    
    **Database URL Format:**
    ```
    postgresql://username:password@hostname:port/database_name
    ```
    
    ### 2. Sample Database
    If you don't have a database set up, you can create a sample database with example data:
    - Click the "Create Sample DB" button in the sidebar
    - This will create tables for users, products, orders, etc.
    
    ### 3. Connect
    Once you have a database URL, click the "Connect" button to initialize the system.
    
    ---
    
    ### Example Queries You Can Try:
    - "Show me all users"
    - "Find products that cost more than $50"
    - "Count the number of orders per customer"
    - "Get the top 5 most expensive products"
    - "Show me users who placed orders last month"
    """)

def show_main_interface(include_examples: bool, max_examples: int):
    """Show the main NL2SQL interface"""
    
    # Display schema information
    if st.session_state.schema_info:
        with st.expander("📋 Database Schema", expanded=False):
            schema_summary = st.session_state.schema_info.get('summary', {})
            st.write(f"**Tables:** {schema_summary.get('total_tables', 0)}")
            st.write(f"**Columns:** {schema_summary.get('total_columns', 0)}")
            st.write(f"**Relationships:** {schema_summary.get('total_relationships', 0)}")
            
            # Show table details
            for table_name, table_info in st.session_state.schema_info.get('tables', {}).items():
                st.write(f"**{table_name}:**")
                for column in table_info.get('columns', []):
                    st.write(f"  - {column['name']}: {column['type']}")
    
    # Query input
    st.header("💬 Natural Language Query")
    
    # Query input with examples
    query_examples = [
        "Show me all users",
        "Find products that cost more than $50",
        "Count the number of orders per customer",
        "Get the top 5 most expensive products",
        "Show me users who placed orders last month"
    ]
    
    selected_example = st.selectbox(
        "Or choose an example:",
        ["Custom query"] + query_examples
    )
    
    if selected_example == "Custom query":
        natural_language_query = st.text_area(
            "Enter your natural language query:",
            placeholder="e.g., Show me all users who signed up last month",
            height=100
        )
    else:
        natural_language_query = st.text_area(
            "Enter your natural language query:",
            value=selected_example,
            height=100
        )
    
    # Generate button
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        generate_button = st.button("🚀 Generate SQL", type="primary", use_container_width=True)
    
    # Process query
    if generate_button and natural_language_query:
        process_query(natural_language_query, include_examples, max_examples)

def process_query(natural_language_query: str, include_examples: bool, max_examples: int):
    """Process the natural language query and generate SQL"""
    
    # Validate input
    is_valid, message = validate_natural_language_query(natural_language_query)
    if not is_valid:
        st.error(f"❌ {message}")
        return
    
    try:
        # Generate SQL
        with st.spinner("🤖 Generating SQL query..."):
            result = st.session_state.nl2sql_generator.generate_and_execute(
                natural_language_query=natural_language_query,
                include_examples=include_examples,
                max_examples=max_examples,
                execute_query=True
            )
        
        # Display results
        display_results(result, natural_language_query)
        
    except Exception as e:
        st.error(f"❌ Error processing query: {str(e)}")
        logger.error(f"Query processing error: {e}")

def display_results(result: Dict, original_query: str):
    """Display the generation and execution results"""
    
    # Generation results
    generation = result.get('generation', {})
    execution = result.get('execution', {})
    
    # Display generated SQL
    st.header("📝 Generated SQL")
    
    if generation.get('error'):
        st.error(f"❌ Generation Error: {generation['error']}")
        return
    
    generated_sql = generation.get('generated_sql', '')
    if generated_sql:
        # Format and display SQL
        formatted_sql = format_sql(generated_sql)
        st.markdown('<div class="sql-box">', unsafe_allow_html=True)
        st.code(formatted_sql, language='sql')
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Copy button
        st.button("📋 Copy SQL", on_click=lambda: st.write("SQL copied to clipboard!"))
        
        # Validation results
        validation = generation.get('validation', {})
        if validation.get('errors'):
            st.error("❌ Validation Errors:")
            for error in validation['errors']:
                st.write(f"  - {error}")
        
        if validation.get('warnings'):
            st.warning("⚠️ Warnings:")
            for warning in validation['warnings']:
                st.write(f"  - {warning}")
        
        if validation.get('suggestions'):
            st.info("💡 Suggestions:")
            for suggestion in validation['suggestions']:
                st.write(f"  - {suggestion}")
    
    # Execution results
    if execution:
        st.header("📊 Query Results")
        
        if execution.get('error'):
            st.error(f"❌ Execution Error: {execution['error']}")
        else:
            results = execution.get('results', [])
            
            if results:
                # Display results as table
                df = pd.DataFrame(results)
                st.dataframe(df, use_container_width=True)
                
                # Results summary
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Rows", execution.get('row_count', 0))
                with col2:
                    st.metric("Columns", execution.get('column_count', 0))
                with col3:
                    st.metric("Tables Used", len(execution.get('validation', {}).get('tables_used', [])))
                
                # Download button
                csv = df.to_csv(index=False)
                st.download_button(
                    label="📥 Download Results (CSV)",
                    data=csv,
                    file_name=f"nl2sql_results_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
            else:
                st.info("ℹ️ Query executed successfully but returned no results.")
    
    # Metadata
    with st.expander("🔍 Query Metadata", expanded=False):
        if generation:
            st.write("**Generation Info:**")
            st.json(generation.get('model_info', {}))
            
            st.write("**Schema Used:**")
            st.json(generation.get('schema_used', {}))
            
            st.write("**Examples Used:**")
            st.write(f"Number of examples: {generation.get('examples_used', 0)}")

if __name__ == "__main__":
    main()
