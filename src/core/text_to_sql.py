import os
from dotenv import load_dotenv
from sqlalchemy import create_engine

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains import create_sql_query_chain
from langchain_community.utilities import SQLDatabase

# --- 1. INITIALIZATION ---
def initialize_components():
    """Load all necessary components for the Text-to-SQL chain."""
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '..', '.env'))
    
    # Check for API Key
    google_api_key = os.getenv("GOOGLE_API_KEY")
    if not google_api_key:
        raise ValueError("GOOGLE_API_KEY not found in .env file.")
        
    # Load embedding model
    print("Loading embedding model...")
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    
    # Load the FAISS vector store
    vector_store_path = os.path.join(os.path.dirname(__file__), 'faiss_index')
    if not os.path.exists(vector_store_path):
        raise FileNotFoundError(f"FAISS index not found at {vector_store_path}. Please run create_vector_store.py first.")
    print("Loading FAISS vector store...")
    vector_store = FAISS.load_local(vector_store_path, embeddings, allow_dangerous_deserialization=True)
    
    # Initialize the LLM
    print("Initializing Gemini LLM...")
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro", api_key=google_api_key)
    
    # Connect to the SQL Database
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL not found in .env file.")
    db = SQLDatabase.from_uri(db_url)
    
    return llm, db

# --- 2. THE MAIN FUNCTION ---
def get_sql_query(question: str):
    """Takes a natural language question and returns a SQL query."""
    llm, db = initialize_components()
    
    print("\nCreating SQL query chain...")
    # This is the core LangChain component that generates the SQL
    chain = create_sql_query_chain(llm, db)
    
    print(f"Generating SQL for question: '{question}'")
    # Invoke the chain to get the SQL query
    sql_query = chain.invoke({"question": question})
    
    return sql_query

# --- 3. EXAMPLE USAGE ---
if __name__ == "__main__":
    # Example question to test the system
    test_question = "What is the average temperature for float with wmo_id 13858?"
    
    try:
        generated_sql = get_sql_query(test_question)
        print("\n--- Generated SQL Query ---")
        print(generated_sql)
        
        # Bonus: Execute the query to see the result
        print("\n--- Executing Query ---")
        llm, db = initialize_components()
        result = db.run(generated_sql)
        print("--- Query Result ---")
        print(result)

    except (ValueError, FileNotFoundError) as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")