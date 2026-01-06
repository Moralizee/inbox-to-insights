from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

# --- Import our modules ---
from db import get_db, engine, Base
from models import Email, EmailLink
import logic
import crud

# Initialize DB tables
Base.metadata.create_all(bind=engine)

app = FastAPI()

# ---------- CORS ----------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Pydantic Models for Requests ----------
class AssignRequest(BaseModel):
    assignee_name: str
    assignee_email: str

# ---------- Utility Endpoints ----------
@app.get("/health")
def health():
    return {"status": "ok"}

# ---------- EMAIL UPLOAD ENDPOINTS ----------

@app.post("/parse-email")
async def parse_email(
    file: UploadFile = File(...), 
    db: Session = Depends(get_db)
):
    try:
        contents = await file.read()
        parsed_data = logic.parse_email_bytes(contents)
        email_id = crud.create_email(db, parsed_data)
        db.commit()
        
        parsed_data["email_id"] = email_id
        return parsed_data
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=422, detail=f"Parsing failed: {str(e)}")

@app.post("/parse-email/bulk")
async def parse_email_bulk(
    files: List[UploadFile] = File(...), 
    db: Session = Depends(get_db)
):
    results = []
    for file in files:
        try:
            contents = await file.read()
            parsed = logic.parse_email_bytes(contents)
            eid = crud.create_email(db, parsed)
            db.commit()
            parsed["email_id"] = eid
            results.append(parsed)
        except Exception:
            db.rollback()
            continue
    return {"count": len(results), "items": results}

# ---------- LISTING & FILTERING ----------

@app.get("/emails")
def list_emails(
    db: Session = Depends(get_db),
    q: Optional[str] = None,
    category: Optional[str] = None,
    intent: Optional[str] = None,
    min_risk: float = 0.0,
    max_risk: float = 1.0,
    limit: int = 500,
    offset: int = 0,
):
    query = db.query(Email)

    if q:
        like = f"%{q}%"
        query = query.filter((Email.subject.ilike(like)) | (Email.preview.ilike(like)))
    if category:
        query = query.filter(Email.category == category)
    if intent:
        query = query.filter(Email.intent == intent)

    query = query.filter(and_(Email.risk_score >= min_risk, Email.risk_score <= max_risk))

    return query.order_by(Email.id.desc()).offset(offset).limit(limit).all()

@app.get("/emails/{email_id}")
def get_email_detail(email_id: int, db: Session = Depends(get_db)):
    email_row = db.query(Email).filter(Email.id == email_id).first()
    if not email_row:
        raise HTTPException(status_code=404, detail="Email not found")
    
    # We create a dictionary copy to add formatted fields for the UI
    data = {column.name: getattr(email_row, column.name) for column in email_row.__table__.columns}
    
    data["links"] = [{"url": l.url, "domain": l.domain} for l in email_row.links]
    data["risk_flags"] = [f for f in (email_row.risk_flags or "").split("; ") if f]
    data["reply_flags"] = [f for f in (email_row.reply_flags or "").split("; ") if f]
    
    return data

# ---------- ASSIGNMENT WORKFLOW ----------

@app.post("/emails/{email_id}/assign")
def assign_email(email_id: int, payload: AssignRequest, db: Session = Depends(get_db)):
    email = db.query(Email).filter(Email.id == email_id).first()
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")

    # Change status to "assigned" or "in_review" based on your preference
    email.status = "assigned" 
    email.assignee_name = payload.assignee_name
    email.assignee_email = payload.assignee_email
    email.assigned_at = datetime.utcnow()
    db.commit()
    return {"status": "assigned"}

@app.post("/emails/{email_id}/unassign")
def unassign_email(email_id: int, db: Session = Depends(get_db)):
    email = db.query(Email).filter(Email.id == email_id).first()
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")

    email.status = "open"
    email.assignee_name = "" 
    email.assignee_email = ""
    email.assigned_at = None
    db.commit()
    return {"status": "unassigned"}

@app.post("/emails/{email_id}/resolve")
def resolve_email(email_id: int, db: Session = Depends(get_db)):
    email = db.query(Email).filter(Email.id == email_id).first()
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")

    email.status = "resolved"
    db.commit()
    return {"status": "resolved"}