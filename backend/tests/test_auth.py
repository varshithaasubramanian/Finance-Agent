def test_signup_creates_account_and_returns_token(client):
    resp = client.post(
        "/api/auth/signup",
        json={"name": "Alice", "email": "alice@example.com", "password": "password123", "security_question": "What city were you born in?", "security_answer": "testville"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["access_token"]
    assert data["user"]["email"] == "alice@example.com"


def test_signup_rejects_duplicate_email(client):
    payload = {"name": "Alice", "email": "dupe@example.com", "password": "password123", "security_question": "What city were you born in?", "security_answer": "testville"}
    first = client.post("/api/auth/signup", json=payload)
    assert first.status_code == 201
    second = client.post("/api/auth/signup", json=payload)
    assert second.status_code == 400


def test_login_with_correct_credentials(client):
    client.post("/api/auth/signup", json={"name": "Bob", "email": "bob@example.com", "password": "password123", "security_question": "What city were you born in?", "security_answer": "testville"})
    resp = client.post("/api/auth/login", json={"email": "bob@example.com", "password": "password123", "security_question": "What city were you born in?", "security_answer": "testville"})
    assert resp.status_code == 200
    assert resp.json()["access_token"]


def test_login_with_wrong_password_is_rejected(client):
    client.post("/api/auth/signup", json={"name": "Bob", "email": "bob2@example.com", "password": "password123", "security_question": "What city were you born in?", "security_answer": "testville"})
    resp = client.post("/api/auth/login", json={"email": "bob2@example.com", "password": "wrongpassword", "security_question": "What city were you born in?", "security_answer": "testville"})
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
        "/api/auth/signup", json={"name": "A", "email": "usera@example.com", "password": "password123", "security_question": "What city were you born in?", "security_answer": "testville"}
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
        "/api/auth/signup", json={"name": "B", "email": "userb@example.com", "password": "password123", "security_question": "What city were you born in?", "security_answer": "testville"}
    )
    b_token = b_signup.json()["access_token"]
    b_headers = {"Authorization": f"Bearer {b_token}"}

    resp = client.get(f"/api/budgets/{budget_id}", headers=b_headers)
    assert resp.status_code == 404

    # User B's own budget list should be empty
    list_resp = client.get("/api/budgets", headers=b_headers)
    assert list_resp.json() == []


def test_security_questions_endpoint_returns_list(client):
    resp = client.get("/api/auth/security-questions")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
    assert len(resp.json()) > 0


def test_change_password_with_correct_current_password(auth_client):
    resp = auth_client.post(
        "/api/auth/change-password",
        json={"current_password": "supersecret123", "new_password": "newpassword456"},
    )
    assert resp.status_code == 204

    old_login = auth_client.post("/api/auth/login", json={"email": "tester@example.com", "password": "supersecret123"})
    assert old_login.status_code == 401

    new_login = auth_client.post("/api/auth/login", json={"email": "tester@example.com", "password": "newpassword456"})
    assert new_login.status_code == 200


def test_change_password_rejects_wrong_current_password(auth_client):
    resp = auth_client.post(
        "/api/auth/change-password",
        json={"current_password": "wrongpassword", "new_password": "newpassword456"},
    )
    assert resp.status_code == 400


def test_update_profile_name(auth_client):
    resp = auth_client.patch("/api/auth/me", json={"name": "New Name"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "New Name"


def test_forgot_password_returns_question_for_known_email(client):
    client.post(
        "/api/auth/signup",
        json={
            "name": "Carol",
            "email": "carol@example.com",
            "password": "password123",
            "security_question": "What city were you born in?",
            "security_answer": "Chennai",
        },
    )
    resp = client.post("/api/auth/forgot-password", json={"email": "carol@example.com"})
    assert resp.status_code == 200
    assert resp.json()["security_question"] == "What city were you born in?"


def test_forgot_password_does_not_reveal_unknown_email(client):
    resp = client.post("/api/auth/forgot-password", json={"email": "nobody@example.com"})
    assert resp.status_code == 200
    assert resp.json()["security_question"] is None


def test_reset_password_with_correct_answer(client):
    client.post(
        "/api/auth/signup",
        json={
            "name": "Dave",
            "email": "dave@example.com",
            "password": "oldpassword123",
            "security_question": "What was your childhood nickname?",
            "security_answer": "  Sparky  ",
        },
    )
    resp = client.post(
        "/api/auth/reset-password",
        json={"email": "dave@example.com", "security_answer": "sparky", "new_password": "brandnewpass123"},
    )
    assert resp.status_code == 200
    assert resp.json()["access_token"]

    login_resp = client.post("/api/auth/login", json={"email": "dave@example.com", "password": "brandnewpass123"})
    assert login_resp.status_code == 200


def test_reset_password_with_wrong_answer_is_rejected(client):
    client.post(
        "/api/auth/signup",
        json={
            "name": "Eve",
            "email": "eve@example.com",
            "password": "oldpassword123",
            "security_question": "What city were you born in?",
            "security_answer": "Mumbai",
        },
    )
    resp = client.post(
        "/api/auth/reset-password",
        json={"email": "eve@example.com", "security_answer": "wronganswer", "new_password": "brandnewpass123"},
    )
    assert resp.status_code == 400
