import os
import re
from dotenv import load_dotenv

from sqlalchemy import create_engine
from langchain_community.utilities import SQLDatabase
from langchain.chains import create_sql_query_chain
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_ollama import ChatOllama
from langchain_community.vectorstores import FAISS

def extract_sql_from_string(text: str) -> str:
    """
    Extracts a SQL query from a string, designed to handle conversational LLM output.
    """
    if "sqlquery:" in text.lower():
        parts = re.split(r"sqlquery:", text, flags=re.IGNORECASE)
        sql_query = parts[1]
    else:
        select_pos = text.upper().find("SELECT")
        if select_pos != -1:
            sql_query = text[select_pos:]
        else:
            raise ValueError("Could not find a SQL query in the LLM's response.")
            
    sql_query = sql_query.replace("```sql", "").replace("```", "").strip()
    
    if not sql_query.endswith(';'):
        sql_query += ';'
        
    return sql_query

def initialize_components():
    """Load all necessary components for the Text-to-SQL chain."""
    load_dotenv()
    
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ConnectionError("DATABASE_URL not found in .env file.")
        
    # --- CORRECTED LOGIC ---
    # 1. Create the SQLAlchemy engine first.
    engine = create_engine(db_url)
    
    # 2. Pass the created engine to the SQLDatabase object.
    db = SQLDatabase(engine=engine)
    # --- END CORRECTION ---
    
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    llm = ChatOllama(model="llama3:8b")
    
    # Return all three components
    return llm, db, engine