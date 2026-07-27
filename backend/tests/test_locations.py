from fastapi.testclient import TestClient


def test_create_location(client: TestClient) -> None:
    response = client.post(
        "/api/locations",
        json={
            "name": "Sushi 201",
            "timezone": "America/New_York",
            "currency": "USD",
        },
    )

    assert response.status_code == 201

    response_data = response.json()

    assert response_data["name"] == "Sushi 201"
    assert response_data["timezone"] == "America/New_York"
    assert response_data["currency"] == "USD"
    assert response_data["is_active"] is True
    assert isinstance(response_data["id"], int)
    assert response_data["created_at"] is not None


def test_list_locations_alphabetically(
    client: TestClient,
) -> None:
    client.post(
        "/api/locations",
        json={"name": "West Ashley"},
    )

    client.post(
        "/api/locations",
        json={"name": "Downtown"},
    )

    response = client.get("/api/locations")

    assert response.status_code == 200

    location_names = [
        location["name"]
        for location in response.json()
    ]

    assert location_names == [
        "Downtown",
        "West Ashley",
    ]


def test_duplicate_location_returns_conflict(
    client: TestClient,
) -> None:
    client.post(
        "/api/locations",
        json={"name": "Sushi 201"},
    )

    response = client.post(
        "/api/locations",
        json={"name": "sushi 201"},
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": "A location with this name already exists."
    }


def test_duplicate_square_location_id_returns_conflict(
    client: TestClient,
) -> None:
    client.post(
        "/api/locations",
        json={
            "name": "Downtown",
            "square_location_id": "SQUARE-123",
        },
    )

    response = client.post(
        "/api/locations",
        json={
            "name": "West Ashley",
            "square_location_id": "SQUARE-123",
        },
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": "This Square location ID is already in use."
    }


def test_empty_location_name_fails_validation(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/locations",
        json={"name": ""},
    )

    assert response.status_code == 422