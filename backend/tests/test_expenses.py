def test_create_budget_and_default_categories(auth_client):
    client = auth_client
    resp = client.post("/api/budgets", json={"period": "2027-01", "total_amount": 1000, "categories": []})
    assert resp.status_code == 201
    data = resp.json()
    assert data["total_amount"] == 1000.0
    names = {c["name"] for c in data["categories"]}
    assert "Food" in names and "Travel" in names and "Others" in names


def test_over_allocation_is_blocked_by_default(auth_client):
    client = auth_client
    resp = client.post(
        "/api/budgets",
        json={
            "period": "2027-02",
            "total_amount": 500,
            "allow_over_allocation": False,
            "categories": [
                {"name": "Food", "allocation": 300},
                {"name": "Travel", "allocation": 400},
            ],
        },
    )
    assert resp.status_code == 400


def test_over_allocation_allowed_when_flagged(auth_client):
    client = auth_client
    resp = client.post(
        "/api/budgets",
        json={
            "period": "2027-03",
            "total_amount": 500,
            "allow_over_allocation": True,
            "categories": [
                {"name": "Food", "allocation": 300},
                {"name": "Travel", "allocation": 400},
            ],
        },
    )
    assert resp.status_code == 201


def test_expense_crud_flow(auth_client):
    client = auth_client
    budget_resp = client.post("/api/budgets", json={"period": "2027-04", "total_amount": 1000, "categories": []})
    budget = budget_resp.json()
    category_id = budget["categories"][0]["id"]

    create_resp = client.post(
        f"/api/budgets/{budget['id']}/expenses",
        json={"amount": 50, "category_id": category_id, "description": "Snacks", "date": "2027-04-02", "payment_method": "Cash"},
    )
    assert create_resp.status_code == 201
    expense = create_resp.json()
    assert expense["amount"] == 50.0

    list_resp = client.get(f"/api/budgets/{budget['id']}/expenses")
    assert len(list_resp.json()) == 1

    update_resp = client.patch(
        f"/api/budgets/{budget['id']}/expenses/{expense['id']}", json={"amount": 75}
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["amount"] == 75.0

    delete_resp = client.delete(f"/api/budgets/{budget['id']}/expenses/{expense['id']}")
    assert delete_resp.status_code == 204

    list_resp_after = client.get(f"/api/budgets/{budget['id']}/expenses")
    assert len(list_resp_after.json()) == 0


def test_parse_expense_endpoint_uses_fallback_without_ai_key(auth_client):
    client = auth_client
    budget_resp = client.post("/api/budgets", json={"period": "2027-05", "total_amount": 1000, "categories": []})
    budget = budget_resp.json()

    resp = client.post(
        f"/api/budgets/{budget['id']}/parse-expense", json={"text": "Spent 60 on auto to college"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["amount"] == 60.0
    assert data["source"] == "fallback"


def test_assistant_status_reports_ai_disabled(auth_client):
    client = auth_client
    budget_resp = client.post("/api/budgets", json={"period": "2027-06", "total_amount": 1000, "categories": []})
    budget = budget_resp.json()
    resp = client.get(f"/api/budgets/{budget['id']}/assistant/status")
    assert resp.status_code == 200
    assert resp.json()["ai_enabled"] is False
