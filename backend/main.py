import os
import json
import sqlite3
import shutil
import re
import gc
from typing import Optional
from datetime import datetime

import pandas as pd
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv

# LangChain / AI
from langchain_community.document_loaders import PyMuPDFLoader, Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_groq import ChatGroq
from langchain_classic.chains import RetrievalQA
from langchain_core.messages import HumanMessage
from langchain_core.prompts import PromptTemplate

# ── Config ────────────────────────────────────────────────────────────────────
load_dotenv()
BASE_DIR     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROMA_PATH  = os.path.join(BASE_DIR, "chroma_db")
UPLOAD_DIR   = os.path.join(BASE_DIR, "static")
STATS_DB     = os.path.join(BASE_DIR, "stats.db")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

os.makedirs(UPLOAD_DIR, exist_ok=True)

# ── FastAPI App ────────────────────────────────────────────────────────────────
app = FastAPI(title="Hire AI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve uploaded resumes
app.mount("/static", StaticFiles(directory=UPLOAD_DIR), name="static")

# ── Models (loaded once) ───────────────────────────────────────────────────────
_embeddings = None
_llm        = None

def get_models():
    global _embeddings, _llm
    if _embeddings is None:
        _embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    if _llm is None:
        _llm = ChatGroq(temperature=0.1, model_name="llama-3.1-8b-instant", groq_api_key=GROQ_API_KEY)
    return _embeddings, _llm

# ── DB Helpers ─────────────────────────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect(STATS_DB)
    cur  = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS candidate_metadata (
            id                   INTEGER PRIMARY KEY AUTOINCREMENT,
            filename             TEXT,
            full_name            TEXT,
            total_experience     REAL DEFAULT 0.0,
            pega_experience      REAL DEFAULT 0.0,
            skills               TEXT,
            certifications       TEXT,
            ctc                  TEXT,
            notice_period        TEXT,
            current_organization TEXT,
            email                TEXT,
            phone                TEXT,
            linkedin             TEXT,
            timestamp            DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Migration: add missing columns
    cur.execute("PRAGMA table_info(candidate_metadata)")
    existing = [c[1] for c in cur.fetchall()]
    for col in ['current_organization', 'email', 'phone', 'linkedin']:
        if col not in existing:
            cur.execute(f"ALTER TABLE candidate_metadata ADD COLUMN {col} TEXT")
    conn.commit()
    conn.close()

def get_candidates_df() -> pd.DataFrame:
    conn = sqlite3.connect(STATS_DB)
    try:
        df = pd.read_sql_query(
            "SELECT * FROM candidate_metadata ORDER BY timestamp DESC", conn
        )
    except Exception:
        df = pd.DataFrame()
    conn.close()
    return df

def log_candidate(data: dict):
    conn = sqlite3.connect(STATS_DB)
    cur  = conn.cursor()
    cols = [
        'filename', 'full_name', 'total_experience', 'pega_experience',
        'skills', 'certifications', 'ctc', 'notice_period',
        'current_organization', 'email', 'phone', 'linkedin'
    ]
    vals = [str(data.get(c, '')) if data.get(c) is not None else '' for c in cols]
    cur.execute("DELETE FROM candidate_metadata WHERE filename = ?", (data.get('filename', ''),))
    cur.execute(
        f"INSERT INTO candidate_metadata ({','.join(cols)}) VALUES ({','.join(['?']*len(cols))})",
        vals
    )
    conn.commit()
    conn.close()

init_db()

# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

# ── Health ─────────────────────────────────────────────────────────────────────
@app.get("/api/health")
def health():
    return {"status": "ok"}

# ── Candidates ─────────────────────────────────────────────────────────────────
@app.get("/api/candidates")
def list_candidates():
    df = get_candidates_df()
    if df.empty:
        return []
    df = df.fillna("")
    return df.to_dict(orient="records")

class CandidateUpdate(BaseModel):
    full_name:            Optional[str] = None
    total_experience:     Optional[float] = None
    pega_experience:      Optional[float] = None
    skills:               Optional[str] = None
    certifications:       Optional[str] = None
    ctc:                  Optional[str] = None
    notice_period:        Optional[str] = None
    current_organization: Optional[str] = None
    email:                Optional[str] = None
    phone:                Optional[str] = None
    linkedin:             Optional[str] = None

@app.put("/api/candidates/{candidate_id}")
def update_candidate(candidate_id: int, body: CandidateUpdate):
    conn = sqlite3.connect(STATS_DB)
    cur  = conn.cursor()
    updates = {k: v for k, v in body.dict().items() if v is not None}
    if not updates:
        conn.close()
        return {"status": "no changes"}
    set_clause = ", ".join(f"{k}=?" for k in updates)
    cur.execute(
        f"UPDATE candidate_metadata SET {set_clause} WHERE id=?",
        list(updates.values()) + [candidate_id]
    )
    conn.commit()
    conn.close()
    return {"status": "updated"}

@app.delete("/api/candidates/{candidate_id}")
def delete_candidate(candidate_id: int):
    conn = sqlite3.connect(STATS_DB)
    cur  = conn.cursor()
    cur.execute("DELETE FROM candidate_metadata WHERE id=?", (candidate_id,))
    conn.commit()
    conn.close()
    return {"status": "deleted"}

# ── Upload & Extract ────────────────────────────────────────────────────────────
EXTRACT_PROMPT = """You are an expert resume parser. Extract EVERY piece of information from the resume below.
Be thorough — search all sections: Summary, Experience, Skills, Education, Certifications, Contact.

Return ONLY a valid JSON object with these exact keys (no extra text, no markdown, just raw JSON):

{{
  "full_name": "<Full name from top of resume>",
  "total_experience": <number — total years of professional work experience. Calculate from date ranges if not stated explicitly. Use 0 if fresher>,
  "pega_experience": <number — years of Pega PRPC/BPM experience specifically. Use 0 if none>,
  "skills": "<All technical skills comma-separated. Be exhaustive — include programming languages, frameworks, tools, databases, cloud, methodologies>",
  "certifications": "<All certifications and courses comma-separated. Include issuer if mentioned. Empty string if none>",
  "ctc": "<Current CTC or expected CTC as stated. Include currency and frequency, e.g. '12 LPA', '₹15,00,000 per annum'. Empty if not found>",
  "notice_period": "<Notice period as stated, e.g. 'Immediate', '30 days', '60 days', '3 months'. Empty if not found>",
  "current_organization": "<Current or most recent employer name>",
  "email": "<Email address>",
  "phone": "<Phone number with country code if available>",
  "linkedin": "<Full LinkedIn profile URL if found, else empty string>"
}}

Rules:
- total_experience: if the resume says '4 years', use 4. If it shows date ranges like 'Jan 2020 - Present (2024)', calculate the total.
- pega_experience: count only Pega PRPC/BPM/Platform work specifically.
- skills: list every technology mentioned — tools, languages, frameworks, databases, cloud services, etc.
- certifications: include Pega certifications (CSA, CSSA, CPRSA, CPDC), IT certs, and online courses.
- If a field is truly not present anywhere in the resume, use an empty string "" (not null, not N/A).

Resume Text:
{text}

JSON:"""


@app.post("/api/upload")
async def upload_resume(file: UploadFile = File(...)):
    _, llm = get_models()
    embeddings, _ = get_models()

    # Save file
    safe_name = file.filename
    path = os.path.join(UPLOAD_DIR, safe_name)
    with open(path, "wb") as f:
        content = await file.read()
        f.write(content)

    # Load document
    try:
        if safe_name.lower().endswith(".pdf"):
            loader = PyMuPDFLoader(path)
        else:
            loader = Docx2txtLoader(path)
        docs = loader.load()
        text = "\n".join([d.page_content for d in docs])
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not read file: {e}")

    # LLM extraction
    try:
        resp = llm.invoke([HumanMessage(content=EXTRACT_PROMPT.format(text=text[:7000]))])
        raw  = resp.content.strip()

        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()
        start, end = raw.find('{'), raw.rfind('}')
        if start != -1 and end != -1:
            raw = raw[start:end+1]

        data = json.loads(raw)
        data['filename'] = safe_name
        log_candidate(data)
    except Exception as e:
        data = {"filename": safe_name, "full_name": safe_name}
        log_candidate(data)

    # Add to ChromaDB
    try:
        for d in docs:
            d.metadata['source'] = safe_name
        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
        chunks   = splitter.split_documents(docs)
        Chroma.from_documents(chunks, embeddings, persist_directory=CHROMA_PATH)
    except Exception:
        pass

    return {"status": "ok", "data": data}

# ── Chat ──────────────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str

CONVERSATIONAL_KW = [
    "hi", "hello", "hey", "how are you", "what's up",
    "good morning", "good afternoon", "good evening",
    "thanks", "thank you", "bye", "goodbye", "who are you",
]

def _is_conversational(msg: str) -> bool:
    m = msg.strip().lower()
    if m in CONVERSATIONAL_KW:
        return True
    # Short messages (≤4 words) with no data keywords → conversational
    data_kw = ["candidate", "resume", "experience", "pega", "skill", "cert",
               "ctc", "notice", "company", "email", "phone", "show", "list",
               "find", "give", "who", "which", "how many", "count", "year",
               "join", "immediate", "work", "hire", "select"]
    if len(m.split()) <= 4 and not any(k in m for k in data_kw):
        return True
    return False

def _df_to_rows(df: pd.DataFrame, names: list) -> list:
    """Return exact DB rows for the given candidate names."""
    lower_names = [n.strip().lower() for n in names]
    matched = df[df['full_name'].str.lower().str.strip().isin(lower_names)]
    if matched.empty:
        # Try partial match
        mask = df['full_name'].str.lower().apply(
            lambda x: any(ln in x or x in ln for ln in lower_names)
        )
        matched = df[mask]
    records = []
    for _, r in matched.iterrows():
        records.append({
            "name":             r.get("full_name", ""),
            "total_experience": r.get("total_experience", 0),
            "pega_experience":  r.get("pega_experience", 0),
            "skills":           r.get("skills", ""),
            "certifications":   r.get("certifications", ""),
            "ctc":              r.get("ctc", ""),
            "notice_period":    r.get("notice_period", ""),
            "organization":     r.get("current_organization", ""),
            "email":            r.get("email", ""),
            "phone":            r.get("phone", ""),
        })
    return records

@app.post("/api/chat")
def chat(body: ChatRequest):
    embeddings, llm = get_models()
    prompt  = body.message.strip()
    p_lower = prompt.lower()

    # ── Route 1: Conversational ──────────────────────────────────────────────
    if _is_conversational(p_lower):
        resp = llm.invoke([HumanMessage(content=(
            "You are Hire AI, an intelligent HR recruitment assistant for Alamaticz Solutions. "
            "Respond warmly and professionally.\n\nUser: " + prompt
        ))])
        return {"type": "text", "answer": resp.content}

    # ── Route 2: Structured (SQLite) — always try this first ─────────────────
    df = get_candidates_df()
    if not df.empty:
        for col in ['total_experience', 'pega_experience']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        # Build a compact summary of each candidate for the LLM
        candidate_lines = []
        for _, r in df.iterrows():
            line = (
                f"Name: {r.get('full_name','?')} | "
                f"Total Exp: {r.get('total_experience',0)} yrs | "
                f"Pega Exp: {r.get('pega_experience',0)} yrs | "
                f"Skills: {r.get('skills','') or 'none'} | "
                f"Certifications: {r.get('certifications','') or 'none'} | "
                f"CTC: {r.get('ctc','') or '?'} | "
                f"Notice: {r.get('notice_period','') or '?'} | "
                f"Company: {r.get('current_organization','') or '?'} | "
                f"Email: {r.get('email','') or '?'} | "
                f"Phone: {r.get('phone','') or '?'}"
            )
            candidate_lines.append(line)
        candidates_text = "\n".join(candidate_lines)

        filter_prompt = f"""You are an expert HR data analyst. I have the following candidate database:

{candidates_text}

HR question: "{prompt}"

Instructions:
1. Read the question carefully.
2. If the question asks to LIST / SHOW / FIND candidates:
   - Return EXACTLY this JSON format (no other text before or after):
   MATCH_RESULT: {{"type":"table","matched_names":[<exact full_name values>],"intro":"<one sentence intro>"}}
3. If the question asks for a COUNT or YES/NO:
   - Return EXACTLY: MATCH_RESULT: {{"type":"count","answer":"<direct answer>"}}
4. If the question is about a SPECIFIC candidate's detail:
   - Return EXACTLY: MATCH_RESULT: {{"type":"table","matched_names":[<that candidate's name>],"intro":"Here are the details:"}}
5. IMPORTANT: Use ONLY exact full_name values from the database above. Do NOT invent names.
6. 'Pega Exp: 0 yrs' = ZERO Pega experience.

Respond with ONLY the MATCH_RESULT line, nothing else."""

        try:
            resp = llm.invoke([HumanMessage(content=filter_prompt)])
            ans  = resp.content.strip()

            if "MATCH_RESULT:" in ans:
                json_str = ans.split("MATCH_RESULT:")[1].strip()
                # Extract JSON object
                s, e = json_str.find('{'), json_str.rfind('}')
                if s != -1 and e != -1:
                    result = json.loads(json_str[s:e+1])

                    if result.get("type") == "count":
                        return {"type": "text", "answer": result.get("answer", ans)}

                    if result.get("type") == "table":
                        names = result.get("matched_names", [])
                        intro = result.get("intro", "Here are the matching candidates:")
                        if names:
                            rows = _df_to_rows(df, names)
                            if rows:
                                return {"type": "table", "answer": intro, "rows": rows}
                        # No matches found
                        return {"type": "text", "answer": "No candidates match your query. Try a different filter."}
        except Exception:
            pass  # Fall through to RAG

    # ── Route 3: RAG (ChromaDB) — for very specific resume content ────────────
    if not os.path.exists(CHROMA_PATH):
        return {"type": "text", "answer": "No resumes uploaded yet. Please upload resumes first."}

    try:
        db        = Chroma(persist_directory=CHROMA_PATH, embedding_function=embeddings)
        retriever = db.as_retriever(search_kwargs={"k": 6})
        qa_prompt = PromptTemplate(
            template="""You are Hire AI, an expert HR recruitment assistant.
Answer using ONLY the resume context below. Be specific and structured.

Resume Context:
{context}

HR Question: {question}

Answer:""",
            input_variables=["context", "question"]
        )
        qa  = RetrievalQA.from_chain_type(
            llm=llm, chain_type="stuff", retriever=retriever,
            chain_type_kwargs={"prompt": qa_prompt}
        )
        ans = qa.invoke(prompt)['result']
        return {"type": "text", "answer": ans}
    except Exception as e:
        return {"type": "text", "answer": f"Search error: {e}"}


# ── Reset ──────────────────────────────────────────────────────────────────────
@app.post("/api/reset")
def reset_all():
    conn = sqlite3.connect(STATS_DB)
    conn.execute("DELETE FROM candidate_metadata")
    conn.commit()
    conn.close()
    try:
        if os.path.exists(CHROMA_PATH):
            shutil.rmtree(CHROMA_PATH)
    except Exception:
        pass
    return {"status": "reset complete"}
