from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def _get_token() -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "password123"},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data.get("success") is True
    token = data.get("access_token")
    assert token
    return token


def test_volunteer_list_returns_items():
    token = _get_token()
    response = client.get(
        "/api/v1/volunteers",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["success"] is True
    assert "items" in payload
    assert payload["total"] >= len(payload["items"])


def test_meta_prefixes_returns_options():
    token = _get_token()
    response = client.get(
        "/api/v1/meta/prefixes",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["success"] is True
    assert payload["items"], "Meta items should not be empty"
    sample = payload["items"][0]
    assert "label" in sample and "value" in sample


def test_area_provinces_include_quota_field():
    token = _get_token()
    response = client.get(
        "/api/v1/areas/provinces",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["success"] is True
    assert payload["items"], "Area response should return at least one province"
    first_item = payload["items"][0]
    assert "quota" in first_item
    assert isinstance(first_item["quota"], int)
