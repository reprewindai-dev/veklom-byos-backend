import uuid

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from backend.apps.api.routers.tasks import router as tasks_router
from backend.core.database.database import get_db

# Create a small isolated app for the test
test_app = FastAPI()
test_app.include_router(tasks_router, prefix="/api/v1/tasks")


class MockResult:
    def __init__(self, obj):
        self.obj = obj

    def scalar_one_or_none(self):
        return self.obj


class MockAsyncSession:
    def __init__(self):
        self.nonces = set()
        self.tasks = []

    def add(self, obj):
        if hasattr(obj, "nonce"):
            self.nonces.add(obj.nonce)
        self.tasks.append(obj)

    async def flush(self):
        for task in self.tasks:
            if getattr(task, "id", None) is None:
                task.id = str(uuid.uuid4())

    async def commit(self):
        pass


# A global mock DB for the test
mock_db = MockAsyncSession()


async def override_get_db():
    yield mock_db


test_app.dependency_overrides[get_db] = override_get_db


@pytest.mark.asyncio
async def test_task_intake_rejects_replayed_nonce():
    unique_nonce = f"nonce-{uuid.uuid4()}"
    payload = {
        "email": "test@example.com",
        "task": "Test evaluate model",
        "round": 1,
        "nonce": unique_nonce,
        "secret": "default_secret",
        "brief": "A test brief",
    }

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # First submission
        # Override the mock's execute to simulate finding nothing for the nonce
        async def mock_execute_first(stmt):
            return MockResult(None)

        mock_db.execute = mock_execute_first

        response1 = await ac.post("/api/v1/tasks/intake", json=payload)
        assert (
            response1.status_code == 200
        ), f"Expected 200, got {response1.status_code}: {response1.text}"
        assert response1.json()["status"] == "success"

        # Second submission, nonce is in db
        async def mock_execute_second(stmt):
            return MockResult("existing_task")  # simulate nonce found

        mock_db.execute = mock_execute_second

        response2 = await ac.post("/api/v1/tasks/intake", json=payload)
        assert (
            response2.status_code == 409
        ), f"Expected 409, got {response2.status_code}: {response2.text}"
        assert "Replay detected" in response2.json()["detail"]
