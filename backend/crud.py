from sqlalchemy.orm import Session
from models import Email, EmailLink
from typing import Dict, Any

def create_email(db: Session, parsed_data: Dict[str, Any]) -> int:
    # Ensure body and subject have fallbacks
    safe_body = parsed_data.get("body") or "No body content found."
    safe_subject = parsed_data.get("subject") or "(No Subject)"
    
    email_row = Email(
        subject=safe_subject,
        from_raw=parsed_data.get("from_raw") or "",
        from_name=parsed_data.get("from_name") or "Unknown",
        from_email=parsed_data.get("from_email") or "unknown@domain.com",
        sender_domain=parsed_data.get("sender_domain") or "unknown",
        provider=parsed_data.get("provider") or "Unknown",
        is_noreply=bool(parsed_data.get("is_noreply")),
        
        category=parsed_data.get("category") or "notification",
        intent=parsed_data.get("intent") or "generic_update",
        
        risk_score=float(parsed_data.get("risk_score", 0.0)),
        risk_flags="; ".join(parsed_data.get("risk_flags", [])),
        
        preview=parsed_data.get("preview") or safe_body[:200],
        body=safe_body,
        
        # ======== NEW AI INTELLIGENCE FIELDS ========
        summary=parsed_data.get("ai_summary") or "No summary available.",
        ai_tasks=parsed_data.get("ai_tasks") or "",
        
        requires_reply=bool(parsed_data.get("requires_reply")),
        action_request=bool(parsed_data.get("action_request")),
        # Map urgency boolean to string for DB
        urgency="urgent" if parsed_data.get("urgency") else "none", 
        reply_score=float(parsed_data.get("reply_score", 0.0)),
        reply_flags="; ".join(parsed_data.get("reply_flags", [])),
        
        status="open",
        assignee_name="",
        assignee_email=""
    )
    
    db.add(email_row)
    db.flush() 
    
    # Save extracted links
    for link in parsed_data.get("links", []):
        db.add(EmailLink(
            email_id=email_row.id,
            url=link["url"],
            domain=link["domain"]
        ))
        
    return email_row.id