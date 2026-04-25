import os
import json
import logging
import tempfile
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Load environment logic so that ADK can hit Vertex AI or Gemini natively
def _load_env():
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    os.environ.setdefault(key.strip(), value.strip())
    os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "1")
    os.environ.setdefault("MODEL_NAME", "gemini-3.1-flash-lite-preview")

_load_env()

# Import the agent AFTER env variables are loaded (due to model configs)
from document_extractor.agent import root_agent

app = FastAPI(title="Document Extractor ADK API", version="1.0")

# Note: We keep global session service running
session_service = InMemorySessionService()

@app.on_event("startup")
async def startup_event():
    await session_service.create_session(
        app_name="doc_extractor_api",
        user_id="api_user",
        session_id="default_session",
    )

@app.post("/extract")
async def extract_document(
    document: UploadFile = File(None, description="The binary document file to process (e.g. PDF)."),
    document_str: str = Form(None, description="The string document content."),
    extraction_schema: str = Form(None, description="The JSON schema string to govern extraction.")
):
    if not document and not document_str:
        raise HTTPException(status_code=400, detail="Either 'document' or 'document_str' must be provided.")

    # Setup message content to the Coordinator Agent
    instructions = "Please extract data from this document.\n"
    schema_block = ""
    if extraction_schema:
        # Ensure it is valid JSON, though the sub-tools do validate it as well
        try:
            json.loads(extraction_schema)
            schema_block = f"\nSchema override:\n{extraction_schema}\n"
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="'extraction_schema' is not a valid JSON string.")
    
    query = ""
    temp_file_path = None
    try:
        # If Binary File provided
        if document:
            temp_dir = tempfile.mkdtemp()
            temp_file_path = os.path.join(temp_dir, document.filename or "upload.pdf")
            with open(temp_file_path, "wb") as f:
                content = await document.read()
                f.write(content)
            
            query = f"{instructions}\nThe document is located at: {temp_file_path}{schema_block}"
            if extraction_schema:
                query += f"\nUse the provided Schema override exactly as text: {extraction_schema}"
            
        # Else if String text provided
        elif document_str:
            query = f"{instructions}\nDocument Content:\n{document_str}\n{schema_block}"
            if extraction_schema:
                query += f"\nUse the provided Schema override exactly as text: {extraction_schema}"

        logger.info("Starting ADK Runner for Extraction Request")
        
        runner = Runner(
            agent=root_agent,
            app_name="doc_extractor_api",
            session_service=session_service,
        )

        content_part = types.Content(
            role="user",
            parts=[types.Part(text=query)],
        )

        final_response_text = ""
        async for event in runner.run_async(
            user_id="api_user",
            session_id="default_session",
            new_message=content_part,
        ):
            if event.is_final_response():
                if event.content and event.content.parts:
                    final_response_text = event.content.parts[0].text

        # Safely parse agent's response to strict JSON structure 
        # Usually the agent output should be cleanly formatted JSON if tools were successfully used
        try:
            # Strip markdown if present
            cleaned_response = final_response_text.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:-3]
            elif cleaned_response.startswith("```"):
                cleaned_response = cleaned_response[3:-3]
            
            parsed_data = json.loads(cleaned_response)
            return JSONResponse(content={"extraction": parsed_data})
        except json.JSONDecodeError:
            logger.error(f"Failed to parse agent JSON. Raw response: {final_response_text}")
            return JSONResponse(
                status_code=500,
                content={"error": "Agent returned malformed JSON.", "raw_response": final_response_text}
            )
    
    finally:
        # Clean up temporary file
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            try:
                os.rmdir(os.path.dirname(temp_file_path))
            except OSError:
                pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8001, reload=True)
