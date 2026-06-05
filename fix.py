import re

with open(r'c:\Users\antho\.windsurf\veklom-byos-backend-2\backend\apps\api\routers\marketplace.py', 'r', encoding='utf-8') as f:
    content = f.read()

target = """    except Exception as e:
        import logging
        from fastapi.responses import JSONResponse
        logging.getLogger("veklom").error(f"Stripe status check failed: {e}")
        return JSONResponse(status_code=503, content={
            "connected": False,
            "status": "configuration_error",
            "message": "Payment service unavailable. Contact support.",
            "action": "contact_support"
        })"""

replacement = """    except Exception as e:
        import logging
        from fastapi.responses import JSONResponse
        logger = logging.getLogger("veklom")
        err_msg = str(e)
        logger.error(f"Stripe status check failed: {err_msg}")
        
        # Self-healing: clear invalid test stripe accounts
        if "does not have access to account" in err_msg or "No such account" in err_msg or "does not exist" in err_msg:
            try:
                vendor.stripe_account_id = ""
                await db.commit()
                return {"connected": False, "status": "incomplete", "onboarding_url": "/api/v1/stripe/connect/onboard"}
            except Exception:
                pass

        return JSONResponse(status_code=503, content={
            "connected": False,
            "status": "configuration_error",
            "message": "Payment service unavailable. Contact support.",
            "action": "contact_support"
        })"""

new_content = content.replace(target, replacement)
with open(r'c:\Users\antho\.windsurf\veklom-byos-backend-2\backend\apps\api\routers\marketplace.py', 'w', encoding='utf-8') as f:
    f.write(new_content)
