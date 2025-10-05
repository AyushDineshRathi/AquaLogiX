import os
import json
from dotenv import load_dotenv

from sqlalchemy import create_engine
from langchain_community.utilities import SQLDatabase
from langchain_core.prompts import ChatPromptTemplate
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

def initialize_components():
    """Load all necessary components for the Text-to-SQL chain."""
    load_dotenv()
    
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ConnectionError("DATABASE_URL not found in .env file.")
        
    engine = create_engine(db_url)
    db = SQLDatabase(engine=engine)
    
    llm = ChatOllama(model="llama3:8b", format="json")
    
    return llm, db, engine

def create_query_generation_chain(llm, db):
    """Creates the LangChain chain with our custom prompt for generating SQL and a viz type."""
    
    # --- FINAL, MOST DETAILED PROMPT ---
    template = """
    Based on the table schema below, write a SQL query that would answer the user's question.
    Also, provide a suggestion for the best visualization type from this list: ['table', 'line_chart', 'map', 'metric', 'bar_chart'].

    ---
    **RULE 1:** If the user asks for a 'profile' (e.g., 'temperature profile', 'salinity profile'), 
    you MUST select the 'pressure' column to represent depth, along with the requested measurement column 
    (e.g., 'temperature' or 'salinity'). The visualization_type for a profile MUST be 'line_chart'.
    
    **RULE 2:** The 'pressure', 'temperature', and 'salinity' columns belong to the 'measurements' table. 
    The 'wmo_id' column belongs to the 'argo_floats' table. 
    You MUST use the correct table aliases when selecting columns (e.g., 'm.pressure', not 'p.pressure').
    ---

    Return ONLY a JSON object with two keys: "query" and "visualization_type".

    Schema: {schema}

    Here is the conversation history:
    {history}

    Question: {question}
    """
    prompt = ChatPromptTemplate.from_messages([
        ("system", template),
        MessagesPlaceholder(variable_name="history"), # Placeholder for history
        ("human", "{question}")
    ])
    
    return prompt | llm