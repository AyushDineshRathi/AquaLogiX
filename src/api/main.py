from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import sys
import os

# This line allows the API to find and import the query_engine module
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.core.query_engine import process_natural_language_query

app = FastAPI(
    title="AquaLogix API",
    description="API for converting natural language questions about ARGO data into SQL results.",
    version="1.0.0"
)

class QueryRequest(BaseModel):
    question: str

@app.post("/query")
async def handle_query(request: QueryRequest):
    try:
        result = process_natural_language_query(request.question)
        return {"question": request.question, "result": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An internal server error occurred: {str(e)}")

@app.get("/")
def read_root():
    return {"message": "Welcome to the AquaLogix API. Go to /docs to see the interactive API documentation."}