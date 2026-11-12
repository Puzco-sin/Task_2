import os
import uuid

import pytest
import requests


@pytest.fixture(scope="session")
def api_url():
    return os.getenv(
        "STELLAR_API_URL",
        "https://qa-stellarburgers.education-services.ru",
    ).rstrip("/")


@pytest.fixture
def api():
    with requests.Session() as session:
        yield session


@pytest.fixture
def user(api, api_url):
    credentials = {
        "email": f"api-test-{uuid.uuid4().hex}@example.com",
        "password": f"Test-{uuid.uuid4().hex}",
        "name": f"API test {uuid.uuid4().hex[:8]}",
    }
    response = api.post(f"{api_url}/api/auth/register", json=credentials)
    body = response.json()
    return {
        **credentials,
        **body,
        "registration_status": response.status_code,
    }


@pytest.fixture
def auth_headers(user):
    return {"Authorization": user["accessToken"]}
