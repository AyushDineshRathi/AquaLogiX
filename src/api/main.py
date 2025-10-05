from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
import sys
import os
import json
from typing import List, Dict, Any

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.core.query_engine import initialize_components, create_query_generation_chain

app = FastAPI(title="AquaLogix API", version="1.0.0")

class QueryRequest(BaseModel):
    question: str
    history: List[Dict[str, Any]] = []

def determine_visualization_type(llm_suggestion: str, columns: list, rows: list) -> str:
    """
    Corrects the LLM's visualization suggestion based on the actual query results.
    """
    columns_lower = [col.lower() for col in columns]
    
    if 'latitude' in columns_lower and 'longitude' in columns_lower:
        return 'map'
        
    if 'pressure' in columns_lower and ('temperature' in columns_lower or 'salinity' in columns_lower):
        return 'line_chart'
        
    if len(rows) == 1 and len(columns) == 1:
        return 'metric'
        
    # --- NEW RULE FOR BAR CHARTS ---
    # If we have two columns, and one is text (object) and the other is a number, it's likely a bar chart.
    if len(columns) == 2:
        # We need to create a temporary DataFrame to check data types
        import pandas as pd
        df = pd.DataFrame(rows, columns=columns)
        dtype1 = df.dtypes[0]
        dtype2 = df.dtypes[1]
        if ('object' in str(dtype1) and pd.api.types.is_numeric_dtype(dtype2)) or \
           ('object' in str(dtype2) and pd.api.types.is_numeric_dtype(dtype1)):
            return 'bar_chart'
    # --- END NEW RULE ---
        
    if llm_suggestion in ['table', 'metric', 'bar_chart']:
        return llm_suggestion

    return 'table'

@app.post("/query")
async def handle_query(request: QueryRequest):
    try:
        llm, db, engine = initialize_components()
        
        schema = db.get_table_info()
        chain = create_query_generation_chain(llm, db)
        response_str = chain.invoke({
            "schema": schema,
            "question": request.question,
            "history": request.history # Pass the history
        }).content
        
        response_json = json.loads(response_str)
        sql_query = response_json["query"]
        llm_viz_suggestion = response_json.get("visualization_type", "table")
        
        with engine.connect() as connection:
            result = connection.execute(text(sql_query))
            columns = list(result.keys())
            rows = [list(row) for row in result.fetchall()]

        # --- Use our new function to get the corrected visualization type ---
        final_viz_type = determine_visualization_type(llm_viz_suggestion, columns, rows)
        
        return {
            "question": request.question,
            "query": sql_query,
            "visualization_type": final_viz_type, # Send the corrected type
            "columns": columns,
            "rows": rows
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An internal server error occurred: {str(e)}")

@app.get("/")
def read_root():
    return {"message": "Welcome to the AquaLogix API. Go to /docs to see the interactive API documentation."}