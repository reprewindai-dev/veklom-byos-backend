import time
import pytest
from backend.core.security.jti_guard import JtiGuard, JtiStore

def mk_claims(offset=0, ttl=300):
    now = int(time.time()) + offset
    return dict(iss="https://issuer", jti=f"jti-{now}", aud="vek", iat=now, exp=now+ttl)

@pytest.mark.asyncio
async def test_accept_first_use():
    g = JtiGuard(JtiStore())
    c = mk_claims()
    await g.check_and_commit(**c)

@pytest.mark.asyncio
async def test_reject_replay():
    g = JtiGuard(JtiStore())
    c = mk_claims()
    await g.check_and_commit(**c)
    with pytest.raises(PermissionError):
        await g.check_and_commit(**c)

@pytest.mark.asyncio
async def test_expiry_allows_reuse_after_ttl():
    g = JtiGuard(JtiStore(), skew=0)
    c = mk_claims(ttl=1)
    await g.check_and_commit(**c)
    time.sleep(2)
    # OK post-expiry
    await g.check_and_commit(**c)

@pytest.mark.asyncio
async def test_missing_jti_fails():
    g = JtiGuard(JtiStore())
    c = mk_claims()
    c["jti"] = ""
    with pytest.raises(ValueError, match="missing jti"):
        await g.check_and_commit(**c)

@pytest.mark.asyncio
async def test_aud_policy_toggle():
    g = JtiGuard(JtiStore(), enforce_aud=False)
    c = mk_claims()
    c["aud"] = None
    await g.check_and_commit(**c)  # Allowed when aud is permissive
    
    g_strict = JtiGuard(JtiStore(), enforce_aud=True)
    with pytest.raises(ValueError, match="missing aud"):
        await g_strict.check_and_commit(**c)
