import os
import json
from dotenv import load_dotenv

from sqlalchemy import create_engine
from langchain_community.utilities import SQLDatabase
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_ollama import ChatOllama

def initialize_components():
    """Load all necessary components for the Text-to-SQL chain."""
    load_dotenv()
    
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ConnectionError("DATABASE_URL not found in .env file.")
        
    engine = create_engine(db_url)
    db = SQLDatabase(engine=engine)
    
    llm = ChatOllama(model="llama3:8b", format="json") # Using the 8b model as you confirmed
    
    return llm, db, engine

def create_query_generation_chain(llm, db):
    """Creates the LangChain chain with our final, most robust prompt."""
    
    template = """You are an expert PostgreSQL developer. Your goal is to convert a user's question into a syntactically correct PostgreSQL query.

You must use only the tables and columns described in the schema below. Pay close attention to which columns belong to which tables to avoid errors.

**Schema:**
- **Table 'argo_floats' (alias 'af'):** Contains metadata about each float. Columns: `id`, `wmo_id`, `project_name`, `pi_name`, `launch_date`.
- **Table 'measurements' (alias 'm'):** Contains sensor readings. Columns: `id`, `float_id`, `timestamp`, `latitude`, `longitude`, `pressure`, `temperature`, `salinity`.
- **Relationship:** The `measurements.float_id` column joins to the `argo_floats.id` column.

**Rules for your output:**
1. For "profile" questions (e.g., "temperature profile"), you MUST select the `pressure` and the relevant measurement (e.g., `temperature`) columns **using their exact original names**. Do NOT use aliases like 'depth' or 'value'. The visualization type for a profile MUST be 'line_chart'.
2. You MUST return your answer as a single, valid JSON object with two keys: "query" (the SQL string) and "visualization_type" (a string from the list: ['table', 'line_chart', 'map', 'metric', 'bar_chart']).
3. Every SQL query MUST include a `FROM` clause and a `JOIN` clause if data from both tables is needed.

**User Question:** {question}

**Conversation History:**
{history}

**JSON Output:**
"""
    prompt = ChatPromptTemplate.from_messages([
        ("system", template),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{question}")
    ])
    
    return prompt | llm