from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import email
from email import policy
from email.utils import parseaddr
import re
from urllib.parse import urlparse
from typing import Optional


app = FastAPI()


# -------- CORS (KEEP) -------- #
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


# -------- Provider Detection -------- #
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

    # fallback: root domain
    if "." in domain:
        parts = domain.split(".")
        root = ".".join(parts[-2:])
        return PROVIDER_MAP.get(root, root)

    return domain


# -------- Link Extraction -------- #
URL_PATTERN = re.compile(
    r'(https?://[^\s<>"\'\)\]]+)',
    re.IGNORECASE,
)


def extract_links(text: str):
    links = []

    for match in URL_PATTERN.findall(text or ""):
        try:
            parsed = urlparse(match)
            domain = parsed.netloc.lower()

            links.append({
                "url": match,
                "domain": domain,
            })
        except Exception:
            continue

    return links


# -------- Preview Cleaner (NEW) -------- #
def clean_preview_text(text: str) -> str:
    if not text:
        return ""

    # remove URLs from preview text
    text = re.sub(r'https?://\S+', '', text)

    # collapse repeated whitespace
    text = re.sub(r'\s+', ' ', text).strip()

    return text


# -------- Category + Intent Rules -------- #
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


# -------- Risk Scoring (Optional-safe) -------- #
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

    # suspicious or mismatched domains
    for d in link_domains:
        if provider and provider not in d and sender_domain not in d:
            risk += 0.25
            flags.append(f"suspicious link: {d}")

    # lots of domains → higher risk
    if len(link_domains) > 3:
        risk += 0.20
        flags.append("multiple external domains")

    # automated mailbox
    if is_noreply:
        risk += 0.05
        flags.append("no-reply sender")

    return round(min(risk, 1.0), 2), flags


# -------- Main Parser Endpoint -------- #
@app.post("/parse-email")
async def parse_email(file: UploadFile = File(...)):
    contents = await file.read()

    msg = email.message_from_bytes(contents, policy=policy.default)

    subject = msg["subject"] or ""
    from_raw = msg["from"] or ""

    # --- Parse sender fields --- #
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

    # --- Extract text body --- #
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                body = part.get_content()
                break
    else:
        body = msg.get_content()

    # clean preview text (NEW)
    preview_text = clean_preview_text(body)
    preview = preview_text[:200]

    # --- Extract links --- #
    links = extract_links(body)

    # --- Classify email --- #
    category, intent = classify_email(subject, body)

    # --- Risk profile --- #
    risk_score, risk_flags = compute_risk(
        provider,
        sender_domain,
        links,
        is_noreply
    )

    return {
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
