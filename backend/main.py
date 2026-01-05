from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import email
from email import policy
from email.utils import parseaddr

import re
from urllib.parse import urlparse
from typing import Optional, List, cast

from datetime import datetime
from pydantic import BaseModel

from sqlalchemy.orm import Session
from sqlalchemy import and_

from db import SessionLocal
from models import Email, EmailLink


app = FastAPI()

# ---------- CORS ----------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- DB Session ----------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/health")
def health():
    return {"status": "ok"}


# ======================================================
#  REQUIRES-REPLY DETECTOR
# ======================================================
REQUIRES_REPLY_KEYWORDS = [
    "please confirm",
    "let me know",
    "can you update",
    "waiting for your response",
    "need your approval",
    "can you review",
    "follow up",
]

ACTION_REQUEST_KEYWORDS = [
    "send",
    "upload",
    "provide",
    "submit",
    "attach",
    "schedule",
    "approve",
]

URGENCY_KEYWORDS = [
    "asap",
    "urgent",
    "immediately",
    "right away",
    "today",
]


def detect_requires_reply(text: str):
    text = (text or "").lower()

    requires_reply = any(k in text for k in REQUIRES_REPLY_KEYWORDS)
    action_request = any(k in text for k in ACTION_REQUEST_KEYWORDS)
    urgency = any(k in text for k in URGENCY_KEYWORDS)

    score = 0.0
    flags: List[str] = []

    if requires_reply:
        score += 0.4
        flags.append("reply_requested")

    if action_request:
        score += 0.3
        flags.append("action_requested")

    if urgency:
        score += 0.3
        flags.append("urgent_language")

    return (
        requires_reply,
        action_request,
        urgency,
        round(score, 2),
        flags
    )


# ======================================================
#  PROVIDER DETECTION
# ======================================================
def infer_provider(domain: str) -> str:
    domain = (domain or "").lower()

    PROVIDER_MAP = {
        "github.com": "GitHub",
        "google.com": "Google",
        "gmail.com": "Gmail",
        "microsoft.com": "Microsoft",
        "outlook.com": "Outlook",
        "paypal.com": "PayPal",
        "apple.com": "Apple",
        "facebookmail.com": "Facebook",
        "amazon.com": "Amazon",
        "quora.com": "Quora",
    }

    if domain in PROVIDER_MAP:
        return PROVIDER_MAP[domain]

    if "." in domain:
        parts = domain.split(".")
        root = ".".join(parts[-2:])
        return PROVIDER_MAP.get(root, root)

    return domain


# ======================================================
#  LINK INTENT CLASSIFIER
# ======================================================
SUS_DOMAINS = [
    "bit.ly", "tinyurl.com", "rb.gy",
    "lnkd.in", "t.co"
]

LOGIN_HINTS = ["login", "signin", "verify", "account"]
BILLING_HINTS = ["billing", "invoice", "payment"]
UNSUB_HINTS = ["unsubscribe", "optout", "preferences"]


def classify_link_intent(url: str, domain: str):
    url_l = url.lower()

    if any(k in url_l for k in LOGIN_HINTS):
        return "login"

    if any(k in url_l for k in BILLING_HINTS):
        return "billing"

    if any(k in url_l for k in UNSUB_HINTS):
        return "unsubscribe"

    if domain in SUS_DOMAINS:
            return "redirector"

    return "generic"


# ======================================================
#  LINK EXTRACTION
# ======================================================
URL_PATTERN = re.compile(
    r'(https?://[^\s<>"\'\)\]]+)',
    re.IGNORECASE,
)


def extract_links(text: str):
    links = []

    for match in URL_PATTERN.findall(text or ""):
        parsed = urlparse(match)
        domain = parsed.netloc.lower()

        links.append({
            "url": match,
            "domain": domain,
            "intent": classify_link_intent(match, domain),
        })

    return links


# ======================================================
#  PREVIEW CLEANER
# ======================================================
def clean_preview_text(text: str) -> str:
    if not text:
        return ""

    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'\s+', ' ', text).strip()

    return text


# ======================================================
#  INTENT CLASSIFIER v2
# ======================================================
def classify_email(subject: str, body: str):
    text = f"{subject} {body}".lower()

    signals: List[str] = []
    confidence = 0.5

    def hit(rule, weight, reason):
        nonlocal confidence
        if rule:
            confidence += weight
            signals.append(reason)
        return rule

    # SECURITY
    if hit(any(x in text for x in [
        "security alert", "new sign-in", "unusual activity",
        "suspicious", "login attempt"
    ]), 0.3, "security_keywords"):
        return "security_alert", "login_security_notice", round(confidence, 2), signals

    if hit(("authorized" in text) or ("granted access" in text),
           0.2, "access_authorized"):
        return "security_alert", "account_access_granted", round(confidence, 2), signals

    # BILLING
    if hit(any(x in text for x in ["invoice", "payment", "receipt", "billing"]),
           0.25, "billing_terms"):
        return "billing", "transaction_notification", round(confidence, 2), signals

    # NEWSLETTER
    if hit(any(x in text for x in ["newsletter", "digest", "weekly update"]),
           0.2, "newsletter_terms"):
        return "newsletter", "content_digest", round(confidence, 2), signals

    # PROMOTION
    PROMO_KEYWORDS = [
        "bonus", "reward", "offer", "discount",
        "deal", "sale", "promo", "promotion",
        "exclusive", "expires"
    ]

    promo_hits = sum(k in text for k in PROMO_KEYWORDS)

    if promo_hits >= 2:
        confidence += 0.25
        signals.append("promo_signals")
        return "promotion", "marketing_offer", round(confidence, 2), signals

    # DEFAULT
    return "notification", "generic_update", round(confidence, 2), signals


# ======================================================
#  RISK MODEL v2
# ======================================================
def domain_root(domain: str):
    if not domain or "." not in domain:
        return domain
    parts = domain.split(".")
    return ".".join(parts[-2:])


def compute_risk(provider, sender_domain, links, is_noreply):
    provider = (provider or "").lower()
    sender_domain = (sender_domain or "").lower()

    sender_root = domain_root(sender_domain)

    risk = 0.0
    flags: List[str] = []

    link_domains = {l["domain"] for l in links}

    # LOOK-ALIKE DOMAINS
    for d in link_domains:
        root = domain_root(d)

        if sender_root and root != sender_root and provider not in d:
            risk += 0.3
            flags.append(f"lookalike_domain:{d}")

    # MULTI-DOMAIN
    if len(link_domains) > 3:
        risk += 0.2
        flags.append("multiple_external_domains")

    # REDIRECTORS
    if any(l.get("intent") == "redirector" for l in links):
        risk += 0.25
        flags.append("redirector_links_present")

    # LOGIN LINKS
    if any(l.get("intent") == "login" for l in links):
        risk += 0.25
        flags.append("login_link_detected")

    # UNSUBSCRIBE-ONLY
    if links and all(l.get("intent") == "unsubscribe" for l in links):
        risk -= 0.2
        flags.append("unsubscribe_only_links")

    # NO-REPLY
    if is_noreply:
        risk += 0.05
        flags.append("no_reply_sender")

    return round(max(min(risk, 1.0), 0.0), 2), flags


# ======================================================
#  SAVE EMAIL
# ======================================================
def save_email_to_db(parsed, body_text, links):
    db: Session = SessionLocal()

    email_row = Email(
        subject=parsed["subject"],

        from_raw=parsed.get("from_raw") or "",
        from_name=parsed.get("from_name") or "",
        from_email=parsed.get("from_email") or "",

        sender_domain=parsed.get("sender_domain") or "",
        provider=parsed.get("provider") or "",
        is_noreply=parsed["is_noreply"],

        category=parsed["category"],
        intent=parsed["intent"],

        risk_score=parsed["risk_score"],
        risk_flags="; ".join(parsed["risk_flags"]),

        preview=parsed["preview"],
        body=body_text,

        requires_reply=parsed["requires_reply"],
        action_request=parsed["action_request"],
        urgency=parsed["urgency"],
        reply_score=parsed["reply_score"],
        reply_flags="; ".join(parsed["reply_flags"]),

        status="open",
        assignee_name="",
        assignee_email="",
        assigned_at=None,
    )

    db.add(email_row)
    db.flush()


    for link in links:
        db.add(EmailLink(
            email_id=email_row.id,
            url=link["url"],
            domain=link["domain"],
        ))

    db.commit()
    db.refresh(email_row)
    db.close()

    return cast(int, email_row.id)


# ======================================================
#  SHARED EMAIL PARSER (used by single + bulk)
# ======================================================
def parse_and_store_email_from_bytes(contents: bytes):
    msg = email.message_from_bytes(contents, policy=policy.default)

    subject = msg["subject"] or ""
    from_raw = msg["from"] or ""

    name, email_addr = parseaddr(from_raw)
    email_addr = email_addr.lower() if email_addr else None
    name = name.strip() if name else None

    sender_domain = None
    provider = None
    is_noreply = False

    if email_addr and "@" in email_addr:
        sender_domain = email_addr.split("@")[-1]
        provider = infer_provider(sender_domain)

        is_noreply = any(k in email_addr for k in
                         ["no-reply", "noreply", "do-not-reply"])

    # extract body
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                body = part.get_content()
                break
    else:
        body = msg.get_content()

    preview = clean_preview_text(body)[:200]
    links = extract_links(body)

    category, intent, intent_conf, intent_signals = \
        classify_email(subject, body)

    risk_score, risk_flags = compute_risk(
        provider,
        sender_domain,
        links,
        is_noreply,
    )

    requires_reply, action_request, urgency, reply_score, reply_flags = \
        detect_requires_reply(f"{subject}\n{body}")

    parsed = {
        "subject": subject,

        "from_raw": from_raw,
        "from_name": name,
        "from_email": email_addr,

        "sender_domain": sender_domain,
        "provider": provider,
        "is_noreply": is_noreply,

        "links": links,

        "category": category,
        "intent": intent,
        "intent_confidence": intent_conf,
        "intent_signals": intent_signals,

        "risk_score": risk_score,
        "risk_flags": risk_flags,

        "requires_reply": requires_reply,
        "action_request": action_request,
        "urgency": urgency,
        "reply_score": reply_score,
        "reply_flags": reply_flags,

        "preview": preview,
    }

    email_id = save_email_to_db(parsed, body, links)
    parsed["email_id"] = email_id

    return parsed


# ======================================================
#  SINGLE EMAIL UPLOAD
# ======================================================
@app.post("/parse-email")
async def parse_email(file: UploadFile = File(...)):
    contents = await file.read()
    return parse_and_store_email_from_bytes(contents)


# ======================================================
#  BULK EMAIL UPLOAD
# ======================================================
@app.post("/parse-email/bulk")
async def parse_email_bulk(files: List[UploadFile] = File(...)):
    results = []

    for file in files:
        contents = await file.read()
        parsed = parse_and_store_email_from_bytes(contents)
        results.append(parsed)

    return {
        "count": len(results),
        "items": results
    }


# ======================================================
#  LIST EMAILS (filters + pagination)
# ======================================================
@app.get("/emails")
def list_emails(
    db: Session = Depends(get_db),

    q: Optional[str] = None,
    category: Optional[str] = None,
    intent: Optional[str] = None,

    min_risk: float = 0.0,
    max_risk: float = 1.0,

    has_links: Optional[bool] = None,
    suspicious_only: Optional[bool] = None,

    limit: int = 100,
    offset: int = 0,
):
    query = db.query(Email)

    if q:
        like = f"%{q}%"
        query = query.filter(
            (Email.subject.ilike(like)) |
            (Email.preview.ilike(like))
        )

    if category:
        query = query.filter(Email.category == category)

    if intent:
        query = query.filter(Email.intent == intent)

    query = query.filter(
        and_(Email.risk_score >= min_risk, Email.risk_score <= max_risk)
    )

    if has_links is True:
        query = query.join(Email.links).distinct()

    if suspicious_only is True:
        query = query.filter(Email.risk_score >= 0.5)

    rows = (
        query
        .order_by(Email.id.desc())
        .offset(offset)
        .limit(min(limit, 500))
        .all()
    )

    return [
        {
            "id": e.id,
            "subject": e.subject,

            "from_name": e.from_name,
            "from_email": e.from_email,

            "sender_domain": e.sender_domain,
            "provider": e.provider,
            "is_noreply": e.is_noreply,

            "category": e.category,
            "intent": e.intent,

            "risk_score": e.risk_score,
            "preview": e.preview,

            "requires_reply": e.requires_reply,
            "reply_score": e.reply_score,

            "status": e.status,
            "assignee_name": e.assignee_name,
            "assignee_email": e.assignee_email,
        }
        for e in rows
    ]


# ======================================================
#  EMAIL DETAIL VIEW
# ======================================================
@app.get("/emails/{email_id}")
def get_email(email_id: int, db: Session = Depends(get_db)):

    email_row = db.query(Email).filter(Email.id == email_id).first()

    if not email_row:
        raise HTTPException(status_code=404, detail="Email not found")

    links = [{"url": l.url, "domain": l.domain} for l in email_row.links]

    risk_flags = [f for f in (email_row.risk_flags or "").split("; ") if f]
    reply_flags = [f for f in (email_row.reply_flags or "").split("; ") if f]

    return {
        "id": email_row.id,
        "subject": email_row.subject,

        "from_raw": email_row.from_raw,
        "from_name": email_row.from_name,
        "from_email": email_row.from_email,

        "sender_domain": email_row.sender_domain,
        "provider": email_row.provider,
        "is_noreply": email_row.is_noreply,

        "category": email_row.category,
        "intent": email_row.intent,

        "risk_score": email_row.risk_score,
        "risk_flags": risk_flags,

        "preview": email_row.preview,
        "body": email_row.body,

        "links": links,

        "requires_reply": email_row.requires_reply,
        "action_request": email_row.action_request,
        "urgency": email_row.urgency,
        "reply_score": email_row.reply_score,
        "reply_flags": reply_flags,

        "status": email_row.status,
        "assignee_name": email_row.assignee_name,
        "assignee_email": email_row.assignee_email,
        "assigned_at": email_row.assigned_at,
    }


# ======================================================
#  ASSIGNMENT WORKFLOW (multi-user)
# ======================================================
class AssignRequest(BaseModel):
    assignee_name: str
    assignee_email: str


@app.post("/emails/{email_id}/assign")
def assign_email(
    email_id: int,
    payload: AssignRequest,
    db: Session = Depends(get_db)
):

    email_row = db.query(Email).filter(Email.id == email_id).first()
    if not email_row:
        raise HTTPException(status_code=404, detail="Email not found")

    email_row.status = "in_review"
    email_row.assignee_name = payload.assignee_name
    email_row.assignee_email = payload.assignee_email
    email_row.assigned_at = datetime.utcnow()

    db.commit()
    db.refresh(email_row)

    return {"status": "assigned"}


@app.post("/emails/{email_id}/unassign")
def unassign_email(email_id: int, db: Session = Depends(get_db)):

    email_row = db.query(Email).filter(Email.id == email_id).first()
    if not email_row:
        raise HTTPException(status_code=404, detail="Email not found")

    email_row.status = "open"
    email_row.assignee_name = ""
    email_row.assignee_email = ""
    email_row.assigned_at = None

    db.commit()
    db.refresh(email_row)

    return {"status": "unassigned"}


@app.post("/emails/{email_id}/resolve")
def resolve_email(email_id: int, db: Session = Depends(get_db)):

    email_row = db.query(Email).filter(Email.id == email_id).first()
    if not email_row:
        raise HTTPException(status_code=404, detail="Email not found")

    email_row.status = "resolved"
    db.commit()
    db.refresh(email_row)

    return {"status": "resolved"}
