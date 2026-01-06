import re
from urllib.parse import urlparse
from typing import List, Tuple, Dict, Any
import email
from email import policy
from email.utils import parseaddr

# --- Constants ---
REQUIRES_REPLY_KEYWORDS = [
    "please confirm", "let me know", "can you update", 
    "waiting for your response", "need your approval"
]
ACTION_REQUEST_KEYWORDS = ["send", "upload", "provide", "submit", "approve"]
URGENCY_KEYWORDS = ["asap", "urgent", "immediately", "right away"]

PROVIDER_MAP = {
    "github.com": "GitHub", "google.com": "Google", "gmail.com": "Gmail",
    "microsoft.com": "Microsoft", "outlook.com": "Outlook", "paypal.com": "PayPal",
    "apple.com": "Apple", "amazon.com": "Amazon"
}

SUS_DOMAINS = ["bit.ly", "tinyurl.com", "rb.gy", "lnkd.in", "t.co"]
URL_PATTERN = re.compile(r'(https?://[^\s<>"\'\)\]]+)', re.IGNORECASE)

# --- NEW: AI Simulation Logic ---

def extract_ai_intelligence(subject: str, body: str) -> Dict[str, Any]:
    """
    Simulates Advanced AI Parsing. 
    This generates a summary and a list of specific tasks based on email context.
    """
    text = f"{subject}\n{body}".lower()
    
    # Default State
    intelligence = {
        "summary": "General communication requiring review.",
        "tasks": ["Review email content", "Determine if follow-up is needed"]
    }
    
    # Contextual Intelligence Generation
    if any(x in text for x in ["security", "login", "password", "unauthorized"]):
        intelligence["summary"] = "Security alert regarding account access or authentication."
        intelligence["tasks"] = [
            "Verify login IP address", 
            "Check for unauthorized account changes", 
            "Confirm identity with user via secondary channel"
        ]
    
    elif any(x in text for x in ["invoice", "billing", "payment", "receipt"]):
        intelligence["summary"] = "Financial notification regarding a transaction or outstanding balance."
        intelligence["tasks"] = [
            "Cross-reference invoice number with accounting",
            "Verify bank/payment details are legitimate",
            "Process for approval"
        ]

    elif any(x in text for x in ["project", "milestone", "update", "phoenix"]):
        intelligence["summary"] = "Project management update regarding ongoing milestones."
        intelligence["tasks"] = [
            "Update internal project tracker",
            "Acknowledge receipt of milestone",
            "Assess impact on timeline"
        ]
        
    return intelligence

# --- Existing Helper Functions ---

def clean_preview_text(text: str) -> str:
    if not text: return ""
    text = re.sub(r'https?://\S+', '', text)
    return re.sub(r'\s+', ' ', text).strip()

def infer_provider(domain: str) -> str:
    domain = (domain or "").lower()
    if domain in PROVIDER_MAP: return PROVIDER_MAP[domain]
    if "." in domain:
        parts = domain.split(".")
        root = ".".join(parts[-2:])
        return PROVIDER_MAP.get(root, root)
    return domain

def detect_requires_reply(text: str) -> Tuple[bool, bool, bool, float, List[str]]:
    text = (text or "").lower()
    req_reply = any(k in text for k in REQUIRES_REPLY_KEYWORDS)
    act_req = any(k in text for k in ACTION_REQUEST_KEYWORDS)
    urgency = any(k in text for k in URGENCY_KEYWORDS)
    
    score = 0.0
    flags = []
    if req_reply: score += 0.4; flags.append("reply_requested")
    if act_req: score += 0.3; flags.append("action_requested")
    if urgency: score += 0.3; flags.append("urgent_language")
    
    return req_reply, act_req, urgency, round(score, 2), flags

def classify_link_intent(url: str, domain: str) -> str:
    url_l = url.lower()
    if any(k in url_l for k in ["login", "signin", "verify", "account"]): return "login"
    if any(k in url_l for k in ["billing", "invoice", "payment"]): return "billing"
    if any(k in url_l for k in ["unsubscribe", "optout"]): return "unsubscribe"
    if domain in SUS_DOMAINS: return "redirector"
    return "generic"

def extract_links(text: str) -> List[Dict[str, str]]:
    links = []
    safe_text = text[:50000] if text else ""
    for match in URL_PATTERN.findall(safe_text):
        parsed = urlparse(match)
        domain = parsed.netloc.lower()
        links.append({
            "url": match,
            "domain": domain,
            "intent": classify_link_intent(match, domain)
        })
    return links

def classify_email(subject: str, body: str) -> Tuple[str, str, float, List[str]]:
    text = f"{subject} {body}".lower()
    signals = []
    if any(x in text for x in ["security alert", "new sign-in", "unusual activity"]):
        signals.append("security_keywords")
        return "security_alert", "login_security_notice", 0.8, signals
    if any(x in text for x in ["invoice", "payment", "receipt"]):
        signals.append("billing_terms")
        return "billing", "transaction_notification", 0.75, signals
    return "notification", "generic_update", 0.5, signals

def compute_risk(provider: str, sender_domain: str, links: List[Dict], is_noreply: bool) -> Tuple[float, List[str]]:
    risk = 0.0
    flags = []
    if any(l["intent"] == "login" for l in links):
        risk += 0.25; flags.append("login_link_detected")
    if is_noreply:
        risk += 0.05; flags.append("no_reply_sender")
    return round(min(risk, 1.0), 2), flags

# --- Main Parsing Function ---

def parse_email_bytes(contents: bytes) -> Dict[str, Any]:
    msg = email.message_from_bytes(contents, policy=policy.default)
    
    subject = msg["subject"] or ""
    from_raw = msg["from"] or ""
    name, email_addr = parseaddr(from_raw)
    email_addr = email_addr.lower() if email_addr else ""
    
    sender_domain = email_addr.split("@")[-1] if "@" in email_addr else ""
    provider = infer_provider(sender_domain)
    is_noreply = any(x in email_addr for x in ["no-reply", "noreply"])
    
    body_text = ""
    for part in msg.walk():
        content_type = part.get_content_type()
        content_disposition = str(part.get_content_disposition())
        if content_type == "text/plain" and "attachment" not in content_disposition:
            payload = part.get_payload(decode=True)
            if isinstance(payload, bytes):
                body_text = payload.decode(errors="replace")
                break 

    if not body_text:
        body_part = msg.get_body(preferencelist=('html'))
        if body_part:
            body_text = body_part.get_content()

    # --- Run Heuristics ---
    links = extract_links(body_text)
    preview = clean_preview_text(body_text)[:200]
    cat, intent, conf, signals = classify_email(subject, body_text)
    
    combined_text = f"{subject}\n{body_text}"
    req_reply, act_req, urgency, rep_score, rep_flags = detect_requires_reply(combined_text)
    risk_score, risk_flags = compute_risk(provider, sender_domain, links, is_noreply)
    
    # --- NEW: Run AI Intelligence Extraction ---
    ai_intel = extract_ai_intelligence(subject, body_text)
    
    return {
        "subject": subject,
        "from_raw": from_raw,
        "from_name": name,
        "from_email": email_addr,
        "sender_domain": sender_domain,
        "provider": provider,
        "is_noreply": is_noreply,
        "body": body_text,
        "preview": preview,
        "links": links,
        "category": cat,
        "intent": intent,
        "intent_confidence": conf,
        "intent_signals": signals,
        "requires_reply": req_reply,
        "action_request": act_req,
        "urgency": urgency,
        "reply_score": rep_score,
        "reply_flags": rep_flags,
        "risk_score": risk_score,
        "risk_flags": risk_flags,
        # Map the new AI fields
        "ai_summary": ai_intel["summary"],
        "ai_tasks": "; ".join(ai_intel["tasks"]) # Store as string for easy DB storage
    }