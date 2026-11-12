import uuid

import allure
import pytest


@allure.step("Убрать обязательное поле из данных пользователя")
def make_incomplete_user_payload(missing_field):
    payload = {
        "email": f"api-test-{uuid.uuid4().hex}@example.com",
        "password": f"Test-{uuid.uuid4().hex}",
        "name": f"API test {uuid.uuid4().hex[:8]}",
    }
    payload.pop(missing_field)
    return payload


@allure.step("Подготовить неверные данные для входа")
def make_invalid_credentials(user, invalid_field):
    credentials = {
        "email": user["email"],
        "password": user["password"],
    }
    credentials[invalid_field] = f"Wrong-{uuid.uuid4().hex}"
    return credentials


@allure.step("Подготовить новое значение поля профиля")
def make_updated_value(template):
    return template.format(token=uuid.uuid4().hex)


@allure.step("Подготовить данные входа с обновлённым полем")
def make_updated_credentials(user, field, updated_value):
    return {
        "email": updated_value if field == "email" else user["email"],
        "password": updated_value if field == "password" else user["password"],
    }


@allure.step("Отправить запрос на регистрацию пользователя")
def register_user(api, api_url, payload):
    return api.post(f"{api_url}/api/auth/register", json=payload)


@allure.step("Отправить запрос на вход пользователя")
def login_user(api, api_url, credentials):
    return api.post(f"{api_url}/api/auth/login", json=credentials)


@allure.step("Отправить запрос на изменение данных пользователя")
def update_user(api, api_url, payload, token=None):
    headers = {"Authorization": token} if token else {}
    return api.patch(
        f"{api_url}/api/auth/user",
        headers=headers,
        json=payload,
    )


@allure.step("Проверить ответ с ошибкой")
def response_matches_status_and_success(response, status_code, success):
    return (
        response.status_code == status_code
        and response.json().get("success") is success
    )


@allure.step("Проверить успешную регистрацию пользователя")
def registration_matches_user(response, email, name):
    body = response.json()
    return (
        response.status_code == 200
        and body.get("success") is True
        and bool(body.get("accessToken"))
        and body.get("user", {}).get("email") == email
        and body.get("user", {}).get("name") == name
    )


@allure.step("Проверить успешный вход пользователя")
def login_matches_user(response, email):
    body = response.json()
    return (
        response.status_code == 200
        and body.get("success") is True
        and bool(body.get("accessToken"))
        and body.get("user", {}).get("email") == email
    )


@allure.step("Проверить, что авторизованный пользователь изменил поле")
def authorized_update_matches(
    update_response, login_response, field, updated_value
):
    update_body = update_response.json()
    login_body = login_response.json()
    response_value_matches = (
        update_body.get("user", {}).get(field) == updated_value
        if field != "password"
        else True
    )
    login_value_matches = (
        login_body.get("user", {}).get(field) == updated_value
        if field != "password"
        else True
    )
    return (
        update_response.status_code == 200
        and update_body.get("success") is True
        and response_value_matches
        and login_response.status_code == 200
        and login_body.get("success") is True
        and login_value_matches
    )


@allure.step("Проверить, что без авторизации данные пользователя не изменились")
def unauthorized_update_preserves_user(
    update_response,
    login_response,
    user,
    field,
    changed_password_response=None,
):
    login_body = login_response.json()
    current_user = login_body.get("user", {})
    password_unchanged = (
        changed_password_response is None
        or changed_password_response.status_code == 401
    )
    current_value_unchanged = (
        current_user.get(field) == user[field]
        if field != "password"
        else password_unchanged
    )
    return (
        update_response.status_code == 401
        and update_response.json().get("success") is False
        and login_response.status_code == 200
        and login_body.get("success") is True
        and current_value_unchanged
        and password_unchanged
    )


@allure.suite("Пользователь")
@allure.sub_suite("Регистрация")
@allure.feature("Регистрация")
class TestUserRegistration:
    @pytest.mark.parametrize(
        ("missing_field", "field_label"),
        [
            ("email", "почты"),
            ("password", "пароля"),
            ("name", "имени"),
        ],
        ids=["почта", "пароль", "имя"],
    )
    @allure.title("Ошибка регистрации без обязательного поля: {field_label}")
    def test_registration_rejects_missing_required_field(
        self, api, api_url, missing_field, field_label
    ):
        payload = make_incomplete_user_payload(missing_field)
        response = register_user(api, api_url, payload)

        assert response_matches_status_and_success(response, 403, False)

    @allure.title("Успешная регистрация нового пользователя")
    def test_registration_creates_unique_user(self, user):
        assert registration_matches_user(
            user["registration_response"],
            user["email"],
            user["name"],
        )

    @allure.title("Ошибка регистрации уже существующего пользователя")
    def test_registration_rejects_existing_user(self, api, api_url, user):
        response = register_user(
            api,
            api_url,
            {
                "email": user["email"],
                "password": user["password"],
                "name": user["name"],
            },
        )

        assert response_matches_status_and_success(response, 403, False)


@allure.suite("Пользователь")
@allure.sub_suite("Авторизация")
@allure.feature("Авторизация")
class TestUserLogin:
    @allure.title("Успешный вход зарегистрированного пользователя")
    def test_login_succeeds_for_registered_user(self, api, api_url, user):
        response = login_user(
            api,
            api_url,
            {"email": user["email"], "password": user["password"]},
        )

        assert login_matches_user(response, user["email"])

    @pytest.mark.parametrize(
        ("invalid_field", "field_label"),
        [
            ("email", "почтой"),
            ("password", "паролем"),
        ],
        ids=["неверная почта", "неверный пароль"],
    )
    @allure.title("Ошибка входа с неверными данными: {field_label}")
    def test_login_rejects_incorrect_credentials(
        self, api, api_url, user, invalid_field, field_label
    ):
        credentials = make_invalid_credentials(user, invalid_field)
        response = login_user(api, api_url, credentials)

        assert response_matches_status_and_success(response, 401, False)


@allure.suite("Пользователь")
@allure.sub_suite("Изменение данных")
@allure.feature("Изменение данных пользователя")
class TestUserUpdate:
    @pytest.mark.parametrize(
        ("field", "new_value", "field_label"),
        [
            ("email", "updated-{token}@example.com", "почты"),
            ("password", "Updated-{token}-password", "пароля"),
            ("name", "Updated {token}", "имени"),
        ],
        ids=["почта", "пароль", "имя"],
    )
    @allure.title("Авторизованное изменение поля: {field_label}")
    def test_authorized_user_can_update_each_field(
        self, api, api_url, user, auth_headers, field, new_value, field_label
    ):
        updated_value = make_updated_value(new_value)
        update_response = update_user(
            api,
            api_url,
            {field: updated_value},
            user["accessToken"],
        )
        credentials = make_updated_credentials(user, field, updated_value)
        login_response = login_user(api, api_url, credentials)

        assert authorized_update_matches(
            update_response,
            login_response,
            field,
            updated_value,
        )

    @pytest.mark.parametrize(
        ("field", "new_value", "field_label"),
        [
            ("email", "updated-{token}@example.com", "почты"),
            ("password", "Updated-{token}-password", "пароля"),
            ("name", "Updated {token}", "имени"),
        ],
        ids=["почта", "пароль", "имя"],
    )
    @allure.title("Изменение поля без авторизации отклонено: {field_label}")
    def test_unauthorized_user_cannot_update_each_field(
        self, api, api_url, user, field, new_value, field_label
    ):
        updated_value = make_updated_value(new_value)
        update_response = update_user(api, api_url, {field: updated_value})
        login_response = login_user(
            api,
            api_url,
            {"email": user["email"], "password": user["password"]},
        )
        changed_password_response = (
            login_user(
                api,
                api_url,
                {"email": user["email"], "password": updated_value},
            )
            if field == "password"
            else None
        )

        assert unauthorized_update_preserves_user(
            update_response,
            login_response,
            user,
            field,
            changed_password_response,
        )
