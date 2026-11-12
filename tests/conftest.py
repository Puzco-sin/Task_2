import os
import uuid

import allure
import pytest
import requests


@allure.step("Подготовить данные уникального пользователя")
def make_user_payload():
    return {
        "email": f"api-test-{uuid.uuid4().hex}@example.com",
        "password": f"Test-{uuid.uuid4().hex}",
        "name": f"API test {uuid.uuid4().hex[:8]}",
    }


@allure.step("Зарегистрировать тестового пользователя")
def register_user(api, api_url, credentials):
    return api.post(f"{api_url}/api/auth/register", json=credentials)


@allure.step("Войти под тестовым пользователем для очистки")
def login_user(api, api_url, credentials):
    return api.post(f"{api_url}/api/auth/login", json=credentials)


@allure.step("Удалить тестового пользователя")
def delete_user(api, api_url, access_token):
    return api.delete(
        f"{api_url}/api/auth/user",
        headers={"Authorization": access_token},
    )


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
    credentials = make_user_payload()
    response = register_user(api, api_url, credentials)
    body = response.json()
    registered_user = {
        **credentials,
        **body,
        "registration_status": response.status_code,
        "registration_response": response,
    }
    yield registered_user

    if body.get("success") is not True:
        return

    access_token = body.get("accessToken")
    if not access_token:
        login_response = login_user(
            api,
            api_url,
            {"email": credentials["email"], "password": credentials["password"]},
        )
        login_response.raise_for_status()
        access_token = login_response.json().get("accessToken")
    if not access_token:
        raise RuntimeError("Could not obtain an access token to delete test user")

    delete_response = delete_user(api, api_url, access_token)
    delete_response.raise_for_status()
    if delete_response.json().get("success") is not True:
        raise RuntimeError("API did not confirm deletion of test user")


@pytest.fixture
def auth_headers(user):
    return {"Authorization": user["accessToken"]}
