import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_ollama import ChatOllama
from langchain_community.vectorstores import FAISS
from langchain.chains import create_sql_query_chain
from langchain_community.utilities import SQLDatabase
import re

# Helper function to extract SQL query from LLM response
def extract_sql_from_string(text: str) -> str:
    """
    Extracts the first SQL query from a given string.
    It looks for a query that starts with SELECT and ends with a semicolon.
    """
    # Use regex to find a SQL query (case-insensitive)
    match = re.search(r"SELECT\s+.*?;", text, re.IGNORECASE | re.DOTALL)
    
    if match:
        # If a match is found, return the cleaned query
        return match.group(0).strip()
    else:
        # As a fallback, if the model just returns the query without "SQLQuery:"
        if "SELECT" in text.upper():
            return text.strip()
        
    raise ValueError("Could not extract a valid SQL query from the LLM's response.")


def initialize_components():
    """Load all necessary components for the Text-to-SQL chain."""
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '..', '.env'))
    
    print("Loading embedding model...")
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    
    vector_store_path = os.path.join(os.path.dirname(__file__), 'faiss_index')
    if not os.path.exists(vector_store_path):
        raise FileNotFoundError(f"FAISS index not found. Please run create_vector_store.py first.")
    print("Loading FAISS vector store...")
    vector_store = FAISS.load_local(vector_store_path, embeddings, allow_dangerous_deserialization=True)
    
    print("Initializing Ollama LLM (llama3:8b)...")
    llm = ChatOllama(model="llama3:8b")
    
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL not found in .env file.")
    db = SQLDatabase.from_uri(db_url)
    
    return llm, db

def get_sql_query(question: str):
    """Takes a natural language question and returns the LLM's raw response."""
    llm, db = initialize_components()
    
    print("\nCreating SQL query chain...")
    chain = create_sql_query_chain(llm, db)
    
    print(f"Generating SQL for question: '{question}'")
    response = chain.invoke({"question": question})
    
    return response

# Example
if __name__ == "__main__":
    test_question = "What is the average temperature for the float with wmo_id 13858?"
    
    try:
        raw_response = get_sql_query(test_question)
        print("\n--- Raw LLM Response ---")
        print(raw_response)
        
        # Function to clean the SQL query from the LLM's response
        clean_sql_query = extract_sql_from_string(raw_response)
        print("\n--- Cleaned SQL Query ---")
        print(clean_sql_query)
        
        # Cleaned Query Execution 
        print("\n--- Executing Query ---")
        llm, db = initialize_components()
        result = db.run(clean_sql_query)
        print("--- Query Result ---")
        print(result)

    except (ValueError, FileNotFoundError) as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")