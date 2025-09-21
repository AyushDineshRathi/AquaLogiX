import os
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
DB_NAME = "argodb"

# Step 1: Connect to default postgres DB to create argodb if it doesn't exist
conn = psycopg2.connect(DATABASE_URL.replace(f"/{DB_NAME}", "/postgres"))
conn.autocommit = True
cur = conn.cursor()

# Check if argodb exists
cur.execute(sql.SQL("SELECT 1 FROM pg_database WHERE datname = %s"), [DB_NAME])
if not cur.fetchone():
    cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(DB_NAME)))
    print(f"Database '{DB_NAME}' created successfully!")
else:
    print(f"Database '{DB_NAME}' already exists.")

cur.close()
conn.close()

# Step 2: Connect to argodb
conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

# Step 3: Create tables
sql_statements = [
    """
    CREATE TABLE IF NOT EXISTS argo_floats (
        id SERIAL PRIMARY KEY,
        wmo_id INTEGER UNIQUE NOT NULL,
        launch_date TIMESTAMP,
        project_name VARCHAR(255)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS measurements (
        id SERIAL PRIMARY KEY,
        float_id INTEGER REFERENCES argo_floats(id) ON DELETE CASCADE,
        timestamp TIMESTAMP NOT NULL,
        latitude DOUBLE PRECISION,
        longitude DOUBLE PRECISION,
        pressure DOUBLE PRECISION,
        temperature DOUBLE PRECISION,
        salinity DOUBLE PRECISION
    );
    """
]

for statement in sql_statements:
    cur.execute(statement)

conn.commit()
print("Tables created successfully!")

cur.close()
conn.close()
