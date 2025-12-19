# combined_backend.py
import os
import json
import re
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from pydub import AudioSegment
from faster_whisper import WhisperModel
import google.generativeai as genai

# =========================
# ENV & GEMINI
# =========================
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY missing")

genai.configure(api_key=GEMINI_API_KEY)
GEMINI_MODEL = genai.GenerativeModel("gemini-2.5-flash-lite")

# =========================
# FASTAPI APP
# =========================
app = FastAPI(title="Smart Meeting Assistant API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# MODELS
# =========================
class MeetingPlan(BaseModel):
    company_name: str
    title: str
    objective: str
    duration: int
    attendees: str

# =========================
# WHISPER LOAD
# =========================
whisper = WhisperModel(
    "small",
    device="cpu",
    compute_type="int8"
)

# =========================
# HELPERS
# =========================
def convert_to_wav(path: Path) -> Path:
    audio = AudioSegment.from_file(path)
    audio = audio.set_frame_rate(16000).set_channels(1)
    out = path.with_suffix(".wav")
    audio.export(out, format="wav")
    return out


def transcribe_audio(path: Path) -> str:
    segments, _ = whisper.transcribe(str(path))
    return " ".join(seg.text.strip() for seg in segments if seg.text)


# =========================
# GEMINI FUNCTIONS
# =========================
def gemini_plan(plan: MeetingPlan) -> str:
    prompt = f"""
You are an expert meeting planner.

Create a structured meeting plan including:
- Recommended tech stack
- Key discussion points
- Expected tasks
- Timeline

Company: {plan.company_name}
Title: {plan.title}
Objective: {plan.objective}
Duration: {plan.duration} minutes
Attendees: {plan.attendees}
"""
    return GEMINI_MODEL.generate_content(prompt).text


def gemini_summarize(text: str) -> Dict[str, Any]:
    prompt = f"""
Return ONLY valid JSON with keys:
summary, action_points, tasks, deadlines.

Transcript:
{text}
"""
    out = GEMINI_MODEL.generate_content(prompt).text
    start, end = out.find("{"), out.rfind("}")
    return json.loads(out[start:end + 1])


def gemini_email(summary: str, tasks: List[Dict[str, Any]]) -> str:
    prompt = f"""
Write a professional follow-up email.

Summary:
{summary}

Tasks:
{json.dumps(tasks, indent=2)}
"""
    return GEMINI_MODEL.generate_content(prompt).text


def gemini_whatsapp(summary: str) -> str:
    prompt = f"""
Create a short WhatsApp-style recap.

Summary:
{summary}
"""
    return GEMINI_MODEL.generate_content(prompt).text


# =========================
# ROUTES
# =========================
@app.get("/")
def health():
    return {"status": "ok"}


@app.post("/plan")
def plan_meeting(plan: MeetingPlan):
    try:
        content = gemini_plan(plan)
        return {"plan": content}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e), "plan": ""}
        )


@app.post("/summarize")
async def summarize(audio: UploadFile = File(...)):
    try:
        tmp = Path(tempfile.gettempdir()) / audio.filename
        with open(tmp, "wb") as f:
            f.write(await audio.read())

        wav = convert_to_wav(tmp)
        transcript = transcribe_audio(wav)

        structured = gemini_summarize(transcript)
        email = gemini_email(structured["summary"], structured.get("tasks", []))
        whatsapp = gemini_whatsapp(structured["summary"])

        tmp.unlink(missing_ok=True)
        wav.unlink(missing_ok=True)

        return {
            "summary": structured["summary"],
            "action_points": structured.get("action_points", []),
            "tasks": structured.get("tasks", []),
            "deadlines": structured.get("deadlines", []),
            "followup_email": email,
            "whatsapp": whatsapp,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))






