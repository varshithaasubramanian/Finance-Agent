def test_signup_creates_account_and_returns_token(client):
    resp = client.post(
        "/api/auth/signup",
        json={"name": "Alice", "email": "alice@example.com", "password": "password123"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["access_token"]
    assert data["user"]["email"] == "alice@example.com"


def test_signup_rejects_duplicate_email(client):
    payload = {"name": "Alice", "email": "dupe@example.com", "password": "password123"}
    first = client.post("/api/auth/signup", json=payload)
    assert first.status_code == 201
    second = client.post("/api/auth/signup", json=payload)
    assert second.status_code == 400


def test_login_with_correct_credentials(client):
    client.post("/api/auth/signup", json={"name": "Bob", "email": "bob@example.com", "password": "password123"})
    resp = client.post("/api/auth/login", json={"email": "bob@example.com", "password": "password123"})
    assert resp.status_code == 200
    assert resp.json()["access_token"]


def test_login_with_wrong_password_is_rejected(client):
    client.post("/api/auth/signup", json={"name": "Bob", "email": "bob2@example.com", "password": "password123"})
    resp = client.post("/api/auth/login", json={"email": "bob2@example.com", "password": "wrongpassword"})
    assert resp.status_code == 401


def test_protected_endpoint_requires_token(client):
    resp = client.get("/api/budgets")
    assert resp.status_code == 401


def test_me_endpoint_returns_current_user(auth_client):
    resp = auth_client.get("/api/auth/me")
    assert resp.status_code == 200
    assert resp.json()["email"] == "tester@example.com"


def test_users_cannot_see_each_others_budgets(client):
    # User A creates a budget
    a_signup = client.post(
        "/api/auth/signup", json={"name": "A", "email": "usera@example.com", "password": "password123"}
    )
    a_token = a_signup.json()["access_token"]
    a_headers = {"Authorization": f"Bearer {a_token}"}
    create_resp = client.post(
        "/api/budgets",
        json={"period": "2027-07", "total_amount": 1000, "categories": []},
        headers=a_headers,
    )
    budget_id = create_resp.json()["id"]

    # User B signs up separately and should NOT be able to see it
    b_signup = client.post(
        "/api/auth/signup", json={"name": "B", "email": "userb@example.com", "password": "password123"}
    )
    b_token = b_signup.json()["access_token"]
    b_headers = {"Authorization": f"Bearer {b_token}"}

    resp = client.get(f"/api/budgets/{budget_id}", headers=b_headers)
    assert resp.status_code == 404

    # User B's own budget list should be empty
    list_resp = client.get("/api/budgets", headers=b_headers)
    assert list_resp.json() == []
