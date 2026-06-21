import logging
import httpx
from backend.core.config.settings import settings
from backend.core.database.database import get_db_session
from backend.core.audit import log_audit_event

logger = logging.getLogger(__name__)

async def send_email_via_resend(to_email: str, subject: str, html_content: str, from_email: str = None) -> bool:
    """Send an email using Resend HTTP API.
    Uses settings.RESEND_API_KEY.
    The from_email must be from the verified domain: mail.veklom.com (e.g., noreply@mail.veklom.com).
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

    # Default to verified domain sender
    default_from = settings.EMAIL_FROM or "Veklom <noreply@mail.veklom.com>"
    # Ensure it uses mail.veklom.com verified domain
    if "mail.veklom.com" not in default_from:
        default_from = "Veklom <noreply@mail.veklom.com>"

    from_addr = from_email or default_from

    payload = {
        "from": from_addr,
        "to": [to_email],
        "subject": subject,
        "html": html_content
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

