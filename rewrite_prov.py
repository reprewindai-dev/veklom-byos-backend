import re

with open('backend/apps/api/routers/auth.py', 'r') as f:
    content = f.read()

new_func = '''@router.post("/vlink-credentials")
async def provision_vlink_credentials(
    body: VLinkRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    workspace_id = getattr(user, "workspace_id", None)
    if not workspace_id:
        raise HTTPException(
            status_code=403,
            detail={"error": "WORKSPACE_CONTEXT_MISSING"},
        )

    from backend.db.models.vlink_binding import VLinkBinding

    binding_result = await db.execute(select(VLinkBinding).where(VLinkBinding.vlink_id == body.vlink_id))
    binding = binding_result.scalar_one_or_none()

    connection_ref = None
    if binding:
        connection_ref = binding.connection_ref
        
        # Explicitly rotate/revoke the old key
        old_key_result = await db.execute(select(APIKey).where(APIKey.id == binding.api_key_id))
        old_key = old_key_result.scalar_one_or_none()
        if old_key:
            old_key.is_active = False

    connection_ref = connection_ref or f"conn_{uuid4().hex}"

    raw_key = f"byos_{secrets.token_urlsafe(32)}"
    scopes = [
        "vlink:assertion",
        f"vlink:id:{body.vlink_id}",
        f"vlink:conn:{connection_ref}",
    ]
    key = APIKey(
        user_id=user.id,
        workspace_id=workspace_id,
        name=f"vlink:{body.vlink_id}",
        key_hash=get_password_hash(raw_key),
        key_prefix=raw_key[:10],
        scopes=json.dumps(scopes),
    )
    db.add(key)
    await db.flush()

    if binding:
        binding.api_key_id = key.id
        binding.is_active = True
        binding.workspace_id = workspace_id
    else:
        binding = VLinkBinding(
            vlink_id=body.vlink_id,
            api_key_id=key.id,
            workspace_id=workspace_id,
            connection_ref=connection_ref,
        )
        db.add(binding)

    await db.commit()
    return {
        "key_id": key.id,
        "key": raw_key,
        "vlink_id": body.vlink_id,
        "connection_ref": connection_ref,
        "workspace_id": workspace_id,
        "scopes": scopes,
    }'''

start_idx = content.find('@router.post("/vlink-credentials")')
if start_idx != -1:
    end_str = '        "scopes": scopes,\n    }'
    end_idx = content.find(end_str, start_idx) + len(end_str)
    
    new_content = content[:start_idx] + new_func + content[end_idx:]
    with open('backend/apps/api/routers/auth.py', 'w') as f:
        f.write(new_content)
    print("Replaced successfully")
else:
    print("Could not find vlink-credentials route")

