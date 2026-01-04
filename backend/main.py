from fastapi import FastAPI, UploadFile, File, Depends
from fastapi.middleware.cors import CORSMiddleware

import email
from email import policy
from email.utils import parseaddr

import re
from urllib.parse import urlparse
from typing import Optional, List, cast

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
#  REQUIRES-REPLY DETECTOR (MVP)
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
    flags = []

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
#  CLASSIFIER (C-Strategy)
# ======================================================
def classify_email(subject: str, body: str):
    text = f"{subject} {body}".lower()

    promo_signals = 0

    PROMO_KEYWORDS = [
        "bonus", "reward", "offer", "discount",
        "deal", "sale", "promo", "promotion",
        "free spins", "exclusive", "expires",
    ]

    if any(k in text for k in PROMO_KEYWORDS):
        promo_signals += 1

    TRACKING_HINTS = [
        "sendgrid", "mandrill", "mailgun",
        "trk.", "click.", "campaign",
        "unsubscribe",
    ]

    if any(k in text for k in TRACKING_HINTS):
        promo_signals += 1

    if any(x in text for x in ["<table", "img src=", "button"]):
        promo_signals += 1

    # Security alerts
    if any(x in text for x in [
        "security alert", "new sign-in", "unusual activity",
        "suspicious", "login attempt"
    ]):
        return "security_alert", "login_security_notice"

    if "authorized" in text or "granted access" in text:
        return "security_alert", "account_access_granted"

    # Billing
    if any(x in text for x in ["invoice", "payment", "receipt", "billing"]):
        return "billing", "transaction_notification"

    # Newsletter
    if any(x in text for x in ["newsletter", "digest", "weekly update"]):
        return "newsletter", "content_digest"

    # Promotion
    if promo_signals >= 2:
        return "promotion", "marketing_offer"

    return "notification", "generic_update"


# ======================================================
#  RISK SCORING
# ======================================================
def compute_risk(provider, sender_domain, links, is_noreply):
    provider = (provider or "").lower()
    sender_domain = (sender_domain or "").lower()

    risk = 0.0
    flags = []

    link_domains = {l["domain"] for l in links}

    for d in link_domains:
        if provider and provider not in d and sender_domain not in d:
            risk += 0.25
            flags.append(f"suspicious link: {d}")

    if len(link_domains) > 3:
        risk += 0.20
        flags.append("multiple external domains")

    if is_noreply:
        risk += 0.05
        flags.append("no-reply sender")

    return round(min(risk, 1.0), 2), flags


# ======================================================
#  SAVE EMAIL
# ======================================================
def save_email_to_db(parsed, body_text, links):
    db: Session = SessionLocal()

    email_row = Email(
        subject=parsed["subject"],

        from_raw=parsed["from_raw"],
        from_name=parsed["from_name"],
        from_email=parsed["from_email"],

        sender_domain=parsed["sender_domain"],
        provider=parsed["provider"],
        is_noreply=parsed["is_noreply"],

        category=parsed["category"],
        intent=parsed["intent"],

        risk_score=parsed["risk_score"],
        risk_flags="; ".join(parsed["risk_flags"]),

        preview=parsed["preview"],
        body=body_text,

        # reply-intelligence
        requires_reply=parsed["requires_reply"],
        action_request=parsed["action_request"],
        urgency=parsed["urgency"],
        reply_score=parsed["reply_score"],
        reply_flags="; ".join(parsed["reply_flags"]),
        assigned_to_user=None,
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
#  PARSE EMAIL UPLOAD
# ======================================================
@app.post("/parse-email")
async def parse_email(file: UploadFile = File(...)):

    contents = await file.read()
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

    category, intent = classify_email(subject, body)

    risk_score, risk_flags = compute_risk(
        provider,
        sender_domain,
        links,
        is_noreply,
    )

    # reply detector
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
#  LIST EMAILS
# ======================================================
@app.get("/emails")
def list_emails(
    db: Session = Depends(get_db),
    q: Optional[str] = None,
    category: Optional[str] = None,
    intent: Optional[str] = None,
    min_risk: float = 0.0,
    max_risk: float = 1.0,
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

    rows = query.order_by(Email.id.desc()).limit(200).all()

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
        return {"error": "Email not found"}

    links = [{"url": l.url, "domain": l.domain} for l in email_row.links]

    # normalize flag strings safely
    risk_flags_raw = email_row.risk_flags or ""
    reply_flags_raw = email_row.reply_flags or ""

    risk_flags = [
        f for f in risk_flags_raw.split("; ") if f.strip()
    ] if isinstance(risk_flags_raw, str) else []

    reply_flags = [
        f for f in reply_flags_raw.split("; ") if f.strip()
    ] if isinstance(reply_flags_raw, str) else []

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
        "assigned_to_user": email_row.assigned_to_user,
    }
