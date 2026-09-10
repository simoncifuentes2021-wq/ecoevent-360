from fastapi.testclient import TestClient

from app.main import app


def test_official_frontend_domain_is_allowed_by_cors():
    response = TestClient(app).options(
        "/api/v1/health",
        headers={
            "Origin": "https://app.greenway.cl",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://app.greenway.cl"
