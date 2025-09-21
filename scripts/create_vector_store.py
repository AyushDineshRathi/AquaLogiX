import os
from sqlalchemy import create_engine, inspect
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from dotenv import load_dotenv

print("Starting the vector store creation process...")

# --- 1. CONFIGURATION & DATABASE CONNECTION ---
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL not found in .env file.")

engine = create_engine(DATABASE_URL)
inspector = inspect(engine)

# --- 2. EXTRACT DATABASE SCHEMA INFORMATION ---
schema_docs = []
table_names = inspector.get_table_names()
print(f"Found tables: {table_names}")

for table_name in table_names:
    columns = inspector.get_columns(table_name)
    # Create a simple, descriptive string for each table
    table_doc = f"Table named '{table_name}' has the following columns: "
    col_docs = []
    for column in columns:
        col_docs.append(f"{column['name']} (type: {column['type']})")
    
    table_doc += ", ".join(col_docs) + "."
    schema_docs.append(table_doc)

print("\n--- Generated Schema Documents ---")
for doc in schema_docs:
    print(doc)

# --- 3. CREATE EMBEDDINGS ---
# We use a powerful open-source model from Hugging Face to create the embeddings
# This runs locally on your machine.
print("\nLoading embedding model (this may take a moment on first run)...")
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

# --- 4. CREATE AND SAVE THE VECTOR STORE ---
if schema_docs:
    print("Creating the FAISS vector store...")
    vector_store = FAISS.from_texts(texts=schema_docs, embedding=embeddings)
    
    # Define the path to save the vector store
    vector_store_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'core', 'faiss_index')
    
    # Save the vector store locally
    vector_store.save_local(vector_store_path)
    print(f"\nVector store created and saved successfully at: {vector_store_path}")
else:
    print("No schema documents were generated. Vector store not created.")