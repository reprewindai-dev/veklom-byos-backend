import re

with open('backend/apps/api/routers/auth.py', 'r', encoding='utf-8') as f:
    content = f.read()

new_func = '''@router.post("/vlink-assertion")
async def exchange_vlink_assertion(
    body: VLinkRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    # 1. receive X-API-Key
    raw_key = request.headers.get("X-API-Key", "")
    if not raw_key.startswith("byos_"):
        raise HTTPException(status_code=401, detail={"error": "INVALID_MACHINE_CREDENTIAL"})

    # 2. locate candidates by prefix
    result = await db.execute(select(APIKey).where(APIKey.key_prefix == raw_key[:10]))
    
    # 3. bcrypt/hash verify full credential
    # 4. resolve exact APIKey.id
    key = next(
        (candidate for candidate in result.scalars().all() if verify_password(raw_key, candidate.key_hash)),
        None,
    )
    if key is None:
        raise HTTPException(status_code=401, detail={"error": "INVALID_MACHINE_CREDENTIAL"})
        
    # 5. key active
    if not key.is_active:
        raise HTTPException(status_code=403, detail={"error": "MACHINE_CREDENTIAL_REVOKED"})
        
    # 6. key unexpired
    if key.expires_at and key.expires_at <= datetime.utcnow():
        raise HTTPException(status_code=403, detail={"error": "MACHINE_CREDENTIAL_EXPIRED"})

    # 7. owning user active and not suspended/locked
    owner_result = await db.execute(select(User).where(User.id == key.user_id))
    owner = owner_result.scalar_one_or_none()
    if (
        owner is None
        or not owner.is_active
        or str(getattr(owner, "status", "")).upper() in {"INACTIVE", "SUSPENDED", "LOCKED"}
    ):
        raise HTTPException(status_code=403, detail={"error": "OWNER_INACTIVE"})

    # 8. enforce exact vlink:assertion scope
    scopes = _vlink_scopes(key.scopes)
    if "vlink:assertion" not in scopes:
        raise HTTPException(status_code=403, detail={"error": "SCOPE_NOT_GRANTED"})

    # 9. resolve canonical workspace from owning user/database
    workspace_id = getattr(owner, "workspace_id", None)
    if not workspace_id:
        raise HTTPException(status_code=403, detail={"error": "WORKSPACE_CONTEXT_MISSING"})

    # 10. load requested vlink_id from TRUSTED SERVER-SIDE VLINK STATE/BINDING
    from backend.db.models.vlink_binding import VLinkBinding
    binding_result = await db.execute(select(VLinkBinding).where(VLinkBinding.vlink_id == body.vlink_id))
    vlink_binding = binding_result.scalar_one_or_none()
    
    if not vlink_binding:
        raise HTTPException(status_code=403, detail={"error": "VLINK_NOT_FOUND"})

    # 11. require this exact APIKey.id is bound to this exact VLink
    if vlink_binding.api_key_id != key.id or vlink_binding.vlink_id != body.vlink_id:
        raise HTTPException(status_code=403, detail={"error": "VLINK_BINDING_MISMATCH"})

    # 12. require VLink workspace matches canonical workspace
    if vlink_binding.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail={"error": "WORKSPACE_MISMATCH"})

    # 13. require VLink active / not revoked
    if not vlink_binding.is_active:
        raise HTTPException(status_code=403, detail={"error": "VLINK_REVOKED"})

    # 14. recover stable projected connection reference
    connection_ref = vlink_binding.connection_ref
    if not connection_ref:
        raise HTTPException(status_code=403, detail={"error": "CONNECTION_REFERENCE_MISSING"})

    # 15. only then mint CAPPO assertion
    now = int(datetime.now(timezone.utc).timestamp())
    payload = {
        "iss": os.getenv("CAPPO_ASSERTION_ISSUER", "https://api.veklom.com"),
        "aud": os.getenv("CAPPO_ASSERTION_AUDIENCE", "https://cappo.veklom.com"),
        "sub": f"vlink:{body.vlink_id}",
        "workspace_id": workspace_id,
        "connection_ref": connection_ref,
        "role": "MACHINE",
        "iat": now,
        "exp": now + 120,
        "jti": secrets.token_urlsafe(24),
    }
    try:
        import jwt
        token = jwt.encode(
            payload,
            _cappo_assertion_private_key(),
            algorithm="EdDSA",
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=503,
            detail={"error": "CAPPO_ASSERTION_UNCONFIGURED"},
        )

    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": 120,
        "workspace_id": workspace_id,
        "connection_ref": connection_ref,
    }'''

start_idx = content.find('@router.post("/vlink-assertion")')
if start_idx != -1:
    end_str = '        "connection_ref": connection_ref,\n    }'
    end_idx = content.find(end_str, start_idx) + len(end_str)
    
    new_content = content[:start_idx] + new_func + content[end_idx:]
    with open('backend/apps/api/routers/auth.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Replaced successfully")
else:
    print("Could not find vlink-assertion route")
