from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import email
from email import policy
from email.utils import parseaddr
import re
from urllib.parse import urlparse
from typing import Optional, cast

from db import engine, SessionLocal
from models import Email, EmailLink
from sqlalchemy.orm import Session



app = FastAPI()


# ---------- CORS ---------- #
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


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ping")
def ping():
    return {"message": "pong"}


# ---------- Provider Detection ---------- #
def infer_provider(domain: str) -> str:
    domain = domain.lower()

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


# ---------- Link Extraction ---------- #
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


# ---------- Preview Cleaner ---------- #
def clean_preview_text(text: str) -> str:
    if not text:
        return ""

    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'\s+', ' ', text).strip()

    return text


# ---------- Category + Intent Rules ---------- #
def classify_email(subject: str, body: str):
    text = f"{subject} {body}".lower()

    if any(x in text for x in [
        "security alert", "new sign-in", "unusual activity",
        "suspicious", "login attempt"
    ]):
        return "security_alert", "login_security_notice"

    if any(x in text for x in [
        "allowed access", "granted access", "authorized"
    ]):
        return "security_alert", "account_access_granted"

    if any(x in text for x in [
        "invoice", "payment", "receipt", "billing"
    ]):
        return "billing", "transaction_notification"

    if any(x in text for x in [
        "newsletter", "digest", "weekly update"
    ]):
        return "newsletter", "content_digest"

    return "notification", "generic_update"


# ---------- Risk Scoring ---------- #
def compute_risk(
    provider: Optional[str],
    sender_domain: Optional[str],
    links: list,
    is_noreply: bool,
) -> tuple[float, list[str]]:

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


# ---------- Save Email To DB (type-safe) ---------- #
def save_email_to_db(parsed: dict, body_text: str, links: list) -> int:
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
    )

    db.add(email_row)
    db.flush()  # real int id assigned here

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


# ---------- Main Parser Endpoint ---------- #
@app.post("/parse-email")
async def parse_email(file: UploadFile = File(...)):
    contents = await file.read()

    msg = email.message_from_bytes(contents, policy=policy.default)

    subject = msg["subject"] or ""
    from_raw = msg["from"] or ""

    name, email_addr = parseaddr(from_raw)
    email_addr = email_addr.lower() if email_addr else None
    name = name.strip() if name else None

    sender_domain: Optional[str] = None
    provider: Optional[str] = None
    is_noreply = False

    if email_addr and "@" in email_addr:
        sender_domain = email_addr.split("@")[-1]
        provider = infer_provider(sender_domain)

        noreply_keywords = ["no-reply", "noreply", "do-not-reply"]
        is_noreply = any(k in email_addr for k in noreply_keywords)

    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                body = part.get_content()
                break
    else:
        body = msg.get_content()

    preview_text = clean_preview_text(body)
    preview = preview_text[:200]

    links = extract_links(body)

    category, intent = classify_email(subject, body)

    risk_score, risk_flags = compute_risk(
        provider,
        sender_domain,
        links,
        is_noreply,
    )

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

        "preview": preview,
    }

    email_id = save_email_to_db(parsed, body, links)

    parsed["email_id"] = email_id

    return parsed
