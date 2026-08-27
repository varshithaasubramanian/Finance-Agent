import os
import tempfile

_test_db_path = os.path.join(tempfile.gettempdir(), "finance_agent_test.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_test_db_path}"
os.environ["SEED_DEMO_DATA"] = "false"
os.environ["AI_API_KEY"] = ""

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database.db import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import models  # noqa: E402
from app.services import budget_service, category_service  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_client(client):
    """A TestClient pre-authenticated as a freshly signed-up user, with the
    Authorization header already attached to every request."""
    signup_resp = client.post(
        "/api/auth/signup",
        json={"name": "Test User", "email": "tester@example.com", "password": "supersecret123"},
    )
    assert signup_resp.status_code == 201, signup_resp.text
    token = signup_resp.json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


@pytest.fixture
def demo_budget(db):
    """A budget matching the project brief's canonical example:
    Total 2000, Food 1000, Travel 800, Others 200."""
    user = budget_service.get_or_create_demo_user(db)
    budget = models.Budget(user_id=user.id, period="2026-08", total_amount=2000, allow_over_allocation=False)
    db.add(budget)
    db.flush()

    food = models.Category(budget_id=budget.id, name="Food", allocation=1000, color="#0F766E")
    travel = models.Category(
        budget_id=budget.id,
        name="Travel",
        allocation=800,
        color="#2563EB",
        is_travel=True,
        fixed_amount=300,
        estimated_daily_amount=25,
    )
    others = models.Category(budget_id=budget.id, name="Others", allocation=200, color="#64748B")
    db.add_all([food, travel, others])
    db.commit()
    db.refresh(budget)
    return budget
