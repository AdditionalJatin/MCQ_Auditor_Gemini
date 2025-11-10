import os
import re
import json
import time
import requests
import google.generativeai as genai
import asyncio  # Added for non-blocking sleep

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from google.generativeai.types import GenerationConfig
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware

# --- 1. Load Environment Variables ---
load_dotenv()
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    print("FATAL ERROR: 'GOOGLE_API_KEY' not found in .env file.")
    # In a real app, you'd raise an error to stop it from starting
else:
    print("Google AI client configuring...")
    genai.configure(api_key=GOOGLE_API_KEY)
    print("Google AI client configured successfully.")

# --- 2. Initialize FastAPI App ---
app = FastAPI(
    title="MCQ Auditor API",
    description="Audits Google Docs for MCQ errors using Gemini 2.5."
)

# --- 3. Add CORS Middleware ---
# This is VITAL for Google Apps Script to be able to call your API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# --- 4. Define Master Prompt and JSON Schema (Copied from your script) ---
MASTER_PROMPT = """
You are an AI Quality Assurance agent. Your task is to audit a single Multiple Choice Question (MCQ) for the predefined errors.
Analyze the question and its options, then fill the provided JSON schema.

**Error Categories to Detect:**
1.  **`InvalidOptionCount`**: Not exactly 4 options.
2.  **`MislabeledIdentifier`**: Identifiers are inconsistent (e.g., "A, B, 2, D").
3.  **`ExactDuplicate`**: Two options are character-for-character identical.
4.  **`DuplicateMeaning`**: Two options are semantic paraphrases.
5.  **`MathEquivalent`**: Two options are mathematically equivalent (e.g., "4" and "2+2").
"""

MCQ_SCHEMA = {
    "type": "object",
    "properties": {
        "Q_no": {
            "type": "integer",
            "description": "The question number found in the text."
        },
        "Option Status": {
            "type": "string",
            "enum": ["OK", "Faulty", "Inconclusive"],
            "description": "OK if no errors, Faulty if an error is detected."
        },
        "Issue Summary": {
            "type": "string",
            "description": "Null if status is OK. Otherwise, a terse note (e.g., 'DuplicateMeaning: 1 & 4')."
        }
    },
    "required": ["Q_no", "Option Status", "Issue Summary"]
}

# --- 5. Helper Functions (Copied from your script) ---
def extract_doc_id(url):
    match = re.search(r'/d/([a-zA-Z0-9-_]+)', url)
    return match.group(1) if match else None

def get_google_doc_text(doc_id):
    url = f"https://docs.google.com/document/d/{doc_id}/export?format=txt"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.content.decode('utf-8')
        else:
            print(f"Error fetching doc. Status: {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return None

def parse_mcqs_from_text(doc_text):
    parsed_questions = []
    regex = r'(Q\s*(\d+)\s*.*?)(?=Q\s*\d+\s*|\Z)'
    matches = re.finditer(regex, doc_text, re.DOTALL)
    
    for match in matches:
        full_text = match.group(1).strip()
        q_num = match.group(2).strip()
        
        if full_text:
            parsed_questions.append({
                "q_num_str": str(q_num),
                "full_text": full_text
            })
    return parsed_questions

# --- 6. Core AI Audit Function (Copied from your script) ---
# This is a synchronous (blocking) function, which is fine
# when called from an async endpoint as we do below.
def run_mcq_audit_gemini(one_question_text):
    try:
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            system_instruction=MASTER_PROMPT
        )
        generation_config = GenerationConfig(
            response_mime_type="application/json",
            response_schema=MCQ_SCHEMA
        )
        response = model.generate_content(
            one_question_text,
            generation_config=generation_config
        )
        return json.loads(response.text)

    except Exception as e:
        print(f"!!! ERROR during Gemini API call: {e}")
        # This will catch 429 rate limit errors
        if "429" in str(e):
            return "RATE_LIMIT_ERROR"
        return None

# --- 7. Define the API Request Model ---
class AuditRequest(BaseModel):
    doc_url: str

# --- 8. The Main API Endpoint ---
@app.post("/audit-doc")
async def audit_document(request: AuditRequest):
    """
    Receives a Google Doc URL, audits all MCQs, and returns a JSON report.
    """
    if not GOOGLE_API_KEY:
        raise HTTPException(status_code=500, detail="Server is missing GOOGLE_API_KEY")

    doc_id = extract_doc_id(request.doc_url)
    if not doc_id:
        raise HTTPException(status_code=400, detail="Invalid Google Doc link.")

    doc_text = get_google_doc_text(doc_id)
    if not doc_text:
        raise HTTPException(status_code=404, detail="Failed to get document text. Is it public?")

    parsed_questions = parse_mcqs_from_text(doc_text)
    if not parsed_questions:
        raise HTTPException(status_code=404, detail="No valid question blocks (e.g., 'Q1') found.")

    final_audit_list = []
    print(f"\n--- Starting audit of {len(parsed_questions)} questions ---")

    for question in parsed_questions:
        print(f"Auditing Q{question['q_num_str']}...")
        result_obj = run_mcq_audit_gemini(question['full_text'])
        
        if result_obj == "RATE_LIMIT_ERROR":
            # If we get rate limited, we stop and tell the user
            print("!!! Hit Rate Limit. Aborting audit.")
            # Add a partial result so the user knows what happened
            final_audit_list.append({
                "Q_no": int(question['q_num_str']),
                "Option Status": "Inconclusive",
                "Issue Summary": "Failed: API Rate Limit hit."
            })
            # Return the partial list
            return final_audit_list
            
        elif result_obj:
            final_audit_list.append(result_obj)
        else:
            final_audit_list.append({
                "Q_no": int(question['q_num_str']),
                "Option Status": "Inconclusive",
                "Issue Summary": "Failed to audit (API or JSON error)"
            })
        
        # Use asyncio.sleep to avoid blocking the server
        # This respects the 12 QPM (5 seconds)
        print("Waiting 5 seconds to respect rate limits...")
        await asyncio.sleep(5)

    print("\n--- ✅ AUDIT COMPLETE ---")
    return final_audit_list

# --- 9. Run the server (for local testing) ---
if __name__ == "__main__":
    import uvicorn
    # This will run on http://127.0.0.1:8000
    uvicorn.run(app, host="0.0.0.0", port=8000)