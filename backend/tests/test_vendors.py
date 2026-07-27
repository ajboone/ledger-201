from fastapi.testclient import TestClient


def test_create_vendor(client: TestClient) -> None:
    response = client.post(
        "/api/vendors",
        json={"name": "Pacific Seafood"},
    )

    assert response.status_code == 201

    response_data = response.json()

    assert response_data["name"] == "Pacific Seafood"
    assert isinstance(response_data["id"], int)
    assert response_data["created_at"] is not None


def test_list_vendors(client: TestClient) -> None:
    client.post(
        "/api/vendors",
        json={"name": "Restaurant Depot"},
    )

    client.post(
        "/api/vendors",
        json={"name": "Pacific Seafood"},
    )

    response = client.get("/api/vendors")

    assert response.status_code == 200
    assert len(response.json()) == 2

    vendor_names = [
        vendor["name"]
        for vendor in response.json()
    ]

    assert vendor_names == [
        "Pacific Seafood",
        "Restaurant Depot",
    ]


def test_duplicate_vendor_returns_conflict(
    client: TestClient,
) -> None:
    client.post(
        "/api/vendors",
        json={"name": "Pacific Seafood"},
    )

    response = client.post(
        "/api/vendors",
        json={"name": "pacific seafood"},
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": "A vendor with this name already exists."
    }


def test_empty_vendor_name_fails_validation(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/vendors",
        json={"name": ""},
    )

    assert response.status_code == 422