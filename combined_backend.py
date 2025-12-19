# combined_backend.py
import os
import json
import tempfile
from pathlib import Path
from typing import Dict, Any
from urllib import response

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from faster_whisper import WhisperModel
import google.generativeai as genai


# ==================================================
# CONFIG (LOCALHOST)
# ==================================================
#GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
#if not GEMINI_API_KEY:
    #raise RuntimeError("Please set GEMINI_API_KEY")

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY missing")

GEMINI_MODEL = "models/gemini-2.5-flash-lite"
MAX_AUDIO_MB = 12

genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel("gemini-2.5-flash-lite")


# ==================================================
# FASTAPI APP
# ==================================================
app = FastAPI(title="Smart Meeting Assistant API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def global_exception_handler(_, exc: Exception):
    return JSONResponse(status_code=500, content={"error": str(exc)})

# ==================================================
# WHISPER (LOCAL CPU SAFE)
# ==================================================
whisper_model = WhisperModel(
    "tiny",
    device="cpu",
    compute_type="int8",
    cpu_threads=2
)

# ==================================================
# DATA MODELS
# ==================================================
class MeetingPlan(BaseModel):
    company_name: str
    title: str
    objective: str
    duration: int
    attendees: str

# ==================================================
# HELPERS
# ==================================================
def safe_json(text: str) -> Dict[str, Any]:
    try:
        s, e = text.find("{"), text.rfind("}")
        return json.loads(text[s:e + 1])
    except Exception:
        return {"summary": text.strip()}

# ==================================================
# MEETING PLANNING (GEMINI)
# ==================================================
@app.post("/plan")
async def plan_meeting(plan: MeetingPlan):
    try:
        prompt = f"""
You are an expert AI meeting planner.

Company: {plan.company_name}
Meeting Title: {plan.title}
Objective: {plan.objective}
Duration: {plan.duration} minutes
Attendees & Roles: {plan.attendees}

Generate:
1. Time-boxed agenda
2. Suggested tech stack
3. Features to be discussed
4. Expected tasks & owners
5. Expected outcomes

Use headings and bullet points.
"""

        response = gemini_model.generate_content(prompt)
        text = response.text or ""

        return {
            "status": "success",
            "plan": text
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "plan": ""
        }


# ==================================================
# MEETING SUMMARIZATION
# ==================================================
@app.post("/summarize")
async def summarize(audio: UploadFile = File(...)):
    if audio.size > MAX_AUDIO_MB * 1024 * 1024:
        raise HTTPException(413, "Audio too large (max 12MB)")

    tmp = Path(tempfile.gettempdir()) / audio.filename
    with open(tmp, "wb") as f:
        f.write(await audio.read())

    segments, _ = whisper_model.transcribe(str(tmp), vad_filter=True)
    transcript = " ".join(s.text for s in segments if s.text)
    tmp.unlink(missing_ok=True)

    if not transcript:
        raise HTTPException(400, "Empty transcription")

    prompt = f"""
You are an AI meeting assistant.

Return ONLY valid JSON:

{{
  "summary": "3–6 sentence summary",
  "action_points": [],
  "tasks": [
    {{
      "assignee": "",
      "task": "",
      "deadline": ""
    }}
  ],
  "deadlines": [],
  "followup_email": "",
  "whatsapp": ""
}}

Transcript:
{transcript}
"""

    response = gemini_model.generate_content(prompt)
    data = safe_json(response.text or "")

    #data = safe_json(resp.text or "")

    return {
        "transcript": transcript,
        **data
    }

@app.get("/")
def health():
    return {"status": "online"}
