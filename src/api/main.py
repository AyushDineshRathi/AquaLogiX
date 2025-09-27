from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
import sys
import os

from langchain.chains import create_sql_query_chain

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.core.query_engine import extract_sql_from_string, initialize_components

app = FastAPI(title="AquaLogix API", version="1.0.0")

class QueryRequest(BaseModel):
    question: str

@app.post("/query")
async def handle_query(request: QueryRequest):
    try:
        llm, db, engine = initialize_components()
        
        # This line will now work correctly
        chain = create_sql_query_chain(llm, db)
        raw_response = chain.invoke({"question": request.question})
        sql_query = extract_sql_from_string(raw_response)
        
        with engine.connect() as connection:
            result = connection.execute(text(sql_query))
            columns = list(result.keys())
            rows = result.fetchall()
            rows_as_list = [list(row) for row in rows]

        return {
            "question": request.question,
            "query": sql_query,
            "columns": columns,
            "rows": rows_as_list
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An internal server error occurred: {str(e)}")

@app.get("/")
def read_root():
    return {"message": "Welcome to the AquaLogix API. Go to /docs to see the interactive API documentation."}