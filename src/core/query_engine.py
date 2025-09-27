import os
import re
from dotenv import load_dotenv

# Import all LangChain and AI components
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_ollama import ChatOllama
from langchain_community.vectorstores import FAISS
from langchain.chains import create_sql_query_chain
from langchain_community.utilities import SQLDatabase

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

def process_natural_language_query(question: str) -> str:
    """
    The main function that processes a natural language query from start to finish.
    """
    print("--- Initializing components for query processing ---")
    load_dotenv()
    
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ConnectionError("DATABASE_URL not found in .env file.")
    db = SQLDatabase.from_uri(db_url)
    
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    llm = ChatOllama(model="llama3:8b")
    
    print(f"Generating SQL for question: '{question}'")
    chain = create_sql_query_chain(llm, db)
    raw_response = chain.invoke({"question": question})
    
    print(f"Raw LLM response: {raw_response}")
    sql_query = extract_sql_from_string(raw_response)
    print(f"Cleaned SQL query: {sql_query}")
    
    result = db.run(sql_query)
    print(f"Query result: {result}")
    
    return result