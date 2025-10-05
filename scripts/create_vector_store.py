import os
from sqlalchemy import create_engine, inspect
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from dotenv import load_dotenv

print("Starting the vector store creation process...")

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL not found in .env file.")

engine = create_engine(DATABASE_URL)
inspector = inspect(engine)

# --- NEW: More descriptive schema documents ---
schema_docs = [
    (
        "argo_floats",
        "This table contains metadata about each ARGO float. It has the following columns: "
        "'id' which is the primary key and a unique identifier for each float in the database, "
        "'wmo_id' which is the float's official World Meteorological Organization (WMO) identifier, "
        "'launch_date' which is the date the float was deployed, and "
        "'project_name' which is the name of the project associated with the float."
    ),
    (
        "measurements",
        "This table contains the time-series sensor readings from the ARGO floats. It has the following columns: "
        "'id' which is a unique identifier for each measurement record, "
        "'float_id' which is a foreign key that references the 'id' column in the 'argo_floats' table, "
        "'timestamp' which is the date and time of the measurement, "
        "'latitude' and 'longitude' for the measurement's location, "
        "'pressure' which indicates the depth in dbar, "
        "'temperature' in Celsius, and "
        "'salinity' in PSU."
    )
]

# Create a list of text documents from our more descriptive schema
documents_for_embedding = [f"Table '{name}': {desc}" for name, desc in schema_docs]

print("\n--- Generated Schema Documents ---")
for doc in documents_for_embedding:
    print(doc)

print("\nLoading embedding model...")
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

if documents_for_embedding:
    print("Creating the FAISS vector store...")
    vector_store = FAISS.from_texts(texts=documents_for_embedding, embedding=embeddings)
    
    vector_store_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'core', 'faiss_index')
    
    vector_store.save_local(vector_store_path)
    print(f"\nVector store created and saved successfully at: {vector_store_path}")
else:
    print("No schema documents were generated. Vector store not created.")