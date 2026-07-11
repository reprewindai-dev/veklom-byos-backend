import os
import asyncio
import unittest
from datetime import datetime, timedelta, timezone
from backend.core.services.pgl_identity_lifecycle import (
    compute_lifecycle,
    stamp_new_human_identity,
    build_renewal_patch,
    TrustLevel,
    PROBATION_DAYS,
    RENEWAL_INTERVAL_DAYS,
    GRACE_PERIOD_DAYS,
)

class TestPGLIdentityLifecycle(unittest.TestCase):
    def test_new_identity_probationary(self):
        # Create metadata for a brand new identity
        now = datetime.now(timezone.utc)
        meta = stamp_new_human_identity(
            human_id="usr_123",
            human_email="test@veklom.com",
            workspace_id="ws_456"
        )
        
        # Compute lifecycle (probationary requires at least 5 attestations to graduate, defaults to 0)
        lc = compute_lifecycle(meta, created_at=now, active_attestations=0, active_rollbacks=0)
        self.assertEqual(lc.trust_level, TrustLevel.PROBATIONARY)
        self.assertTrue(lc.can_execute)
        self.assertIsNotNone(lc.warning)
        self.assertIn("PROBATIONARY", lc.warning)

    def test_active_after_probation(self):
        # Identity created 100 days ago
        now = datetime.now(timezone.utc)
        created_at = now - timedelta(days=100)
        meta = stamp_new_human_identity(
            human_id="usr_123",
            human_email="test@veklom.com",
            workspace_id="ws_456"
        )
        
        # 90 days elapsed, has 5 successful attestations, 0 rollbacks -> ACTIVE
        lc = compute_lifecycle(meta, created_at=created_at, active_attestations=5, active_rollbacks=0)
        self.assertEqual(lc.trust_level, TrustLevel.ACTIVE)
        self.assertTrue(lc.can_execute)
        self.assertIsNone(lc.warning)

        # 90 days elapsed but only 4 successful attestations -> stays PROBATIONARY
        lc_insufficient = compute_lifecycle(meta, created_at=created_at, active_attestations=4, active_rollbacks=0)
        self.assertEqual(lc_insufficient.trust_level, TrustLevel.PROBATIONARY)
        self.assertIn("needs 1 more successful attestations", lc_insufficient.warning)

        # 90 days elapsed, 5 attestations but has 1 rollback -> stays PROBATIONARY
        lc_rollback = compute_lifecycle(meta, created_at=created_at, active_attestations=5, active_rollbacks=1)
        self.assertEqual(lc_rollback.trust_level, TrustLevel.PROBATIONARY)
        self.assertIn("has 1 unresolved failures/rollbacks", lc_rollback.warning)

    def test_renewal_due_warning(self):
        # Identity created 350 days ago (within 30 days of the 365-day renewal window)
        now = datetime.now(timezone.utc)
        created_at = now - timedelta(days=350)
        meta = stamp_new_human_identity(
            human_id="usr_123",
            human_email="test@veklom.com",
            workspace_id="ws_456"
        )
        
        # Active for 350 days, satisfies active requirements
        lc = compute_lifecycle(meta, created_at=created_at, active_attestations=5, active_rollbacks=0)
        self.assertEqual(lc.trust_level, TrustLevel.RENEWAL_DUE)
        self.assertTrue(lc.can_execute)
        self.assertIsNotNone(lc.warning)
        self.assertIn("renewal due", lc.warning.lower())

    def test_grace_period_reminders(self):
        # Created 370 days ago (5 days past the 365-day deadline, within the 14-day grace period)
        now = datetime.now(timezone.utc)
        created_at = now - timedelta(days=370)
        meta = stamp_new_human_identity(
            human_id="usr_123",
            human_email="test@veklom.com",
            workspace_id="ws_456"
        )
        
        # Within 14-day grace period
        lc = compute_lifecycle(meta, created_at=created_at, active_attestations=5, active_rollbacks=0)
        self.assertEqual(lc.trust_level, TrustLevel.GRACE_PERIOD)
        self.assertTrue(lc.can_execute)  # Must be allowed to execute during grace period
        self.assertEqual(lc.grace_day, 6) # (370 - 365) + 1 = 6
        self.assertIsNotNone(lc.warning)
        self.assertIn("GRACE PERIOD", lc.warning)

    def test_hard_expired_block(self):
        # Created 385 days ago (20 days past the deadline, grace period of 14 days exceeded)
        now = datetime.now(timezone.utc)
        created_at = now - timedelta(days=385)
        meta = stamp_new_human_identity(
            human_id="usr_123",
            human_email="test@veklom.com",
            workspace_id="ws_456"
        )
        
        # Grace period expired
        lc = compute_lifecycle(meta, created_at=created_at, active_attestations=5, active_rollbacks=0)
        self.assertEqual(lc.trust_level, TrustLevel.HARD_EXPIRED)
        self.assertFalse(lc.can_execute) # Hard block enforced
        self.assertIsNotNone(lc.warning)
        self.assertIn("HARD EXPIRED", lc.warning)

    def test_renewal_resets_clock(self):
        # Created 380 days ago, but renewed yesterday
        now = datetime.now(timezone.utc)
        created_at = now - timedelta(days=380)
        meta = stamp_new_human_identity(
            human_id="usr_123",
            human_email="test@veklom.com",
            workspace_id="ws_456"
        )
        
        # Apply renewal patch yesterday
        yesterday = now - timedelta(days=1)
        renewed_meta = build_renewal_patch(meta)
        renewed_meta["last_renewed_at"] = yesterday.isoformat()
        
        lc = compute_lifecycle(renewed_meta, created_at=created_at, active_attestations=5, active_rollbacks=0)
        self.assertEqual(lc.trust_level, TrustLevel.ACTIVE)
        self.assertTrue(lc.can_execute)
        self.assertEqual(renewed_meta["renewal_count"], 1)

    def test_key_rotation_signing(self):
        import json
        from unittest.mock import patch
        from backend.services.pgl_client import PGLClient

        # Setup rotation keys configuration with an active 'v2' key and inactive 'v1' key
        mock_keys = {
            "active_key_id": "v2",
            "keys": {
                "v1": "signing_key_payload_secret_version_1",
                "v2": "rotated_signing_key_payload_secret_version_2"
            }
        }

        pgl = PGLClient(db=None) # Instantiating with None db makes persistent return False

        with patch.dict(os.environ, {"PGL_AUTHORITY_KEYS_JSON": json.dumps(mock_keys)}):
            res = asyncio.run(pgl.commit_intent(
                workspace_id="ws_1",
                actor_id="actor_1",
                genome_hash="g_hash",
                constitution_hash="c_hash",
                scope="wallet:spend"
            ))
            
            # Signature prefix check to ensure key index rotation is preserved
            self.assertIsNotNone(res.get("signature"))
            self.assertTrue(res["signature"].startswith("v2:"))

if __name__ == "__main__":
    import os
    import asyncio
    unittest.main()

