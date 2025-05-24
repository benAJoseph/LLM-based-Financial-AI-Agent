from fastapi import FastAPI, File, UploadFile, HTTPException, Request, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import pandas as pd
import io
import json
import uuid
from datetime import datetime
import uvicorn
import os
from pathlib import Path
from llm_agent import FinancialLLMAgent

# Create necessary directories
os.makedirs("uploads", exist_ok=True)
os.makedirs("static", exist_ok=True)

app = FastAPI(
    title="Financial AI Agent",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Set up templates
templates = Jinja2Templates(directory="templates")

# In-memory storage for sessions
sessions = {}
llm_agent = FinancialLLMAgent()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

class QueryRequest(BaseModel):
    prompt: str
    session_id: str

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return FileResponse("templates/web_interface.html")

@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    session_id: str = Form(""),
):
    try:
        # Validate file type
        if not file.filename or not file.filename.lower().endswith(('.csv', '.xlsx', '.xls')):
            raise HTTPException(status_code=400, detail="Only CSV and Excel files are supported")
        
        # Read file content
        content = await file.read()
        
        # Process the file based on its type
        try:
            if file.filename.lower().endswith('.csv'):
                df = pd.read_csv(io.StringIO(content.decode('utf-8')))
            else:
                df = pd.read_excel(io.BytesIO(content))
                
            # Basic data validation
            if df.empty:
                raise ValueError("The uploaded file is empty")
                
            # Clean column names and convert to string
            df = df.astype(str)
            df.columns = df.columns.astype(str).str.strip()
            
            # Use provided session_id or create a new one
            if not session_id or session_id == 'undefined':
                session_id = str(uuid.uuid4())
            
            # Save file to uploads directory
            file_path = os.path.join("uploads", f"{session_id}_{file.filename}")
            with open(file_path, "wb") as f:
                f.write(content)
            
            # Store session data
            sessions[session_id] = {
                "filename": file.filename,
                "file_path": file_path,
                "upload_time": datetime.utcnow().isoformat(),
                "columns": [{"name": col, "type": "string"} for col in df.columns],
                "data_preview": df.head(100).to_dict(orient='records')  # Store a preview of the data
            }
            
            rows_processed = len(df)
            
            return {
                "status": "success",
                "session_id": session_id,
                "filename": file.filename,
                "rows_processed": rows_processed,
                "columns": sessions[session_id]["columns"],
                "preview": sessions[session_id]["data_preview"][:5]  # Return first 5 rows as preview
            }
            
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error processing file: {str(e)}")
            
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

@app.post("/query")
async def query_data(request: Request):
    try:
        data = await request.json()
        session_id = data.get('session_id')
        prompt = data.get('prompt')
        
        if not session_id or not prompt:
            raise HTTPException(status_code=400, detail="Missing session_id or prompt")
            
        if session_id not in sessions:
            raise HTTPException(status_code=404, detail="Session not found. Please upload a file first.")
            
        # Get the session data
        session_data = sessions[session_id]
        
        # Convert the preview data to a string for the context
        context = "\n".join([str(row) for row in session_data.get('data_preview', [])])
        
        # Get response from LLM
        result = llm_agent.query_financial_data(
            prompt=prompt,
            context=f"Financial data preview:\n{context}"
        )
        
        if not result.get('success', False):
            raise HTTPException(status_code=500, detail=result.get('error', 'Failed to generate response'))
        
        return {
            "status": "success",
            "response": result.get('response', 'No response generated'),
            "model": result.get('model', 'unknown'),
            "tokens": {
                "prompt": result.get('prompt_tokens', 0),
                "completion": result.get('completion_tokens', 0),
                "total": result.get('total_tokens', 0)
            },
            "metadata": {
                "session_id": session_id,
                "prompt": prompt,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")

# Serve the web interface for all other routes
@app.get("/{full_path:path}")
async def catch_all(request: Request, full_path: str):
    return FileResponse("templates/web_interface.html")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)