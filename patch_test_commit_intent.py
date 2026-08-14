with open("backend/tests/test_pgl_identity_gate.py", "r") as f:
    content = f.read()

content = content.replace(
"""        with patch("backend.core.services.pgl_identity_gate.PGLIdentityGate._check_status", new_callable=MagicMock) as mock_check_status:
            mock_check_status.return_value = None

            from backend.core.services.pgl_identity_gate import PGLIdentityError
            with pytest.raises(PGLIdentityError) as exc_info:
                await PGLIdentityGate.require(
                    db=session,
                    actor_id="test-actor",
                    action="test-action",
                    payload={"key": "val"},
                    kind=AgentKind.REGISTERED,
                    scope="test-scope"
                )""",
"""        with patch("backend.core.services.pgl_identity_gate.PGLIdentityGate._check_status", new_callable=MagicMock) as mock_check_status:
            mock_check_status.return_value = None

            from backend.core.services.pgl_identity_gate import PGLIdentityError
            with patch("backend.services.pgl_client.PGLClient.commit_intent", new_callable=AsyncMock) as mock_commit_intent:
                with pytest.raises(PGLIdentityError) as exc_info:
                    await PGLIdentityGate.require(
                        db=session,
                        actor_id="test-actor",
                        action="test-action",
                        payload={"key": "val"},
                        kind=AgentKind.REGISTERED,
                        scope="test-scope"
                    )
                # Assert commit_intent is not reached when lifecycle fails
                mock_commit_intent.assert_not_called()""")

with open("backend/tests/test_pgl_identity_gate.py", "w") as f:
    f.write(content)
