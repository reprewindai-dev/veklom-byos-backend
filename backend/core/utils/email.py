import logging
import httpx
import re
from html import unescape
from backend.core.config.settings import settings
from backend.core.database.database import get_db_session
from backend.core.audit import log_audit_event

logger = logging.getLogger(__name__)

def html_to_text(html_content: str) -> str:
    """Extract plain text from HTML content by stripping tags and unescaping entities."""
    if not html_content:
        return ""
    # Remove style, script, head blocks
    text = re.sub(r'<(style|script|head)\b[^>]*>([\s\S]*?)<\/\1>', '', html_content, flags=re.IGNORECASE)
    # Replace block level elements with newlines
    text = re.sub(r'</?(p|div|h\d|tr|br|hr)\b[^>]*>', '\n', text, flags=re.IGNORECASE)
    # Remove all other tags
    text = re.sub(r'<[^>]+>', '', text)
    # Replace multiple spaces/newlines
    text = re.sub(r'\n\s*\n+', '\n\n', text)
    # Unescape HTML entities
    return unescape(text).strip()

def sanitize_sender(from_email: str) -> str:
    """Sanitize the sender address to match verified Resend subdomain mail.veklom.com and avoid no-reply.
    Example:
        noreply@veklom.com -> hello@mail.veklom.com
        sales@veklom.com -> sales@mail.veklom.com
        Veklom <noreply@veklom.com> -> Veklom <hello@mail.veklom.com>
    """
    if not from_email:
        return "Veklom <hello@mail.veklom.com>"
    
    # Parse potential display name: Name <email@domain.com>
    match = re.search(r'^(.*?)\s*<([^>]+)>$', from_email)
    if match:
        name, email = match.group(1).strip(), match.group(2).strip()
    else:
        name, email = "", from_email.strip()
    
    # Replace noreply or no-reply prefix with hello
    email = re.sub(r'^(noreply|no-reply)\b', 'hello', email, flags=re.IGNORECASE)
    
    # Ensure domain is mail.veklom.com
    parts = email.split('@')
    if len(parts) == 2:
        username, domain = parts[0], parts[1].lower()
        if domain != "mail.veklom.com":
            domain = "mail.veklom.com"
        email = f"{username}@{domain}"
    else:
        email = "hello@mail.veklom.com"
        
    if name:
        return f"{name} <{email}>"
    return email

async def send_email_via_resend(to_email: str, subject: str, html_content: str, from_email: str = None) -> bool:
    """Send an email using Resend HTTP API.
    Uses settings.RESEND_API_KEY.
    The sender must use the verified domain: mail.veklom.com.
    """
    api_key = (settings.RESEND_API_KEY or "").strip()
    if not api_key or "YOUR_" in api_key or "NEED_FROM" in api_key:
        logger.warning("[email] RESEND_API_KEY is not configured. Simulating email send.")
        logger.info(f"[email] To: {to_email} | Subject: {subject}\nHTML: {html_content[:200]}...")
        
        # Log simulated email
        try:
            async with get_db_session() as db:
                await log_audit_event(
                    db=db,
                    user_id="system",
                    action="email.send.simulated",
                    workspace_id="default",
                    resource_type="email",
                    resource_id="simulated",
                    details={
                        "to": to_email,
                        "subject": subject,
                        "resend_id": "simulated",
                        "success": True,
                        "body_preview": html_content[:200]
                    }
                )
        except Exception as log_err:
            logger.error(f"[email] Failed to log simulated email to audit: {log_err}")
            
        return True

    url = "https://api.resend.com/emails"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    # Retrieve and sanitize sender
    default_from = settings.EMAIL_FROM or "Veklom <hello@mail.veklom.com>"
    from_addr = sanitize_sender(from_email or default_from)
    
    # Generate plain text version from HTML
    text_content = html_to_text(html_content)

    payload = {
        "from": from_addr,
        "to": [to_email],
        "subject": subject,
        "html": html_content,
        "text": text_content
    }

    success = False
    resend_id = None
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload, timeout=10.0)
            if response.status_code in (200, 201):
                resend_id = response.json().get('id')
                logger.info(f"[email] Email sent successfully to {to_email} via Resend. ID: {resend_id}")
                success = True
                return True
            else:
                logger.error(f"[email] Resend API error: {response.status_code} - {response.text}")
                return False
    except Exception as e:
        logger.error(f"[email] Error sending email via Resend: {e}")
        return False
    finally:
        # Log real email send result
        try:
            async with get_db_session() as db:
                await log_audit_event(
                    db=db,
                    user_id="system",
                    action="email.send.success" if success else "email.send.failure",
                    workspace_id="default",
                    resource_type="email",
                    resource_id=resend_id or "failed",
                    details={
                        "to": to_email,
                        "subject": subject,
                        "resend_id": resend_id,
                        "success": success,
                        "body_preview": html_content[:200]
                    }
                )
        except Exception as log_err:
            logger.error(f"[email] Failed to log email result to audit: {log_err}")


