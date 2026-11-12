import uuid

import pytest


@pytest.mark.parametrize(
    "missing_field",
    ["email", "password", "name"],
)
def test_registration_rejects_missing_required_field(
    api, api_url, missing_field
):
    payload = {
        "email": f"api-test-{uuid.uuid4().hex}@example.com",
        "password": f"Test-{uuid.uuid4().hex}",
        "name": f"API test {uuid.uuid4().hex[:8]}",
    }
    payload.pop(missing_field)

    response = api.post(f"{api_url}/api/auth/register", json=payload)

    assert (response.status_code, response.json().get("success")) == (
        403,
        False,
    )


def test_registration_creates_unique_user(user):
    assert (
        user["registration_status"],
        user["success"],
        user["user"]["email"],
        user["user"]["name"],
        bool(user["accessToken"]),
    ) == (200, True, user["email"], user["name"], True)


def test_registration_rejects_existing_user(api, api_url, user):
    response = api.post(
        f"{api_url}/api/auth/register",
        json={
            "email": user["email"],
            "password": user["password"],
            "name": user["name"],
        },
    )

    assert (response.status_code, response.json().get("success")) == (
        403,
        False,
    )


def test_login_succeeds_for_registered_user(api, api_url, user):
    response = api.post(
        f"{api_url}/api/auth/login",
        json={"email": user["email"], "password": user["password"]},
    )

    body = response.json()
    assert (
        response.status_code,
        body.get("success"),
        bool(body.get("accessToken")),
        body.get("user", {}).get("email"),
    ) == (200, True, True, user["email"]), response.text


@pytest.mark.parametrize("invalid_field", ["email", "password"])
def test_login_rejects_incorrect_credentials(
    api, api_url, user, invalid_field
):
    credentials = {
        "email": user["email"],
        "password": user["password"],
    }
    credentials[invalid_field] = f"Wrong-{uuid.uuid4().hex}"
    response = api.post(
        f"{api_url}/api/auth/login",
        json=credentials,
    )

    assert (response.status_code, response.json().get("success")) == (
        401,
        False,
    )


@pytest.mark.parametrize(
    ("field", "new_value"),
    [
        ("email", "updated-{token}@example.com"),
        ("password", "Updated-{token}-password"),
        ("name", "Updated {token}"),
    ],
)
def test_authorized_user_can_update_each_field(
    api, api_url, user, auth_headers, field, new_value
):
    updated_value = new_value.format(token=uuid.uuid4().hex)
    response = api.patch(
        f"{api_url}/api/auth/user",
        headers=auth_headers,
        json={field: updated_value},
    )

    body = response.json()
    updated_in_response = (
        body.get("user", {}).get(field) == updated_value
        if field != "password"
        else True
    )

    credentials = {
        "email": updated_value if field == "email" else user["email"],
        "password": updated_value if field == "password" else user["password"],
    }
    login_response = api.post(
        f"{api_url}/api/auth/login",
        json=credentials,
    )
    login_body = login_response.json()
    updated_in_login = (
        login_body.get("user", {}).get(field) == updated_value
        if field != "password"
        else True
    )
    assert (
        response.status_code,
        body.get("success"),
        updated_in_response,
        login_response.status_code,
        login_body.get("success"),
        updated_in_login,
    ) == (200, True, True, 200, True, True), (
        response.text,
        login_response.text,
    )


@pytest.mark.parametrize(
    ("field", "new_value"),
    [
        ("email", "updated-{token}@example.com"),
        ("password", "Updated-{token}-password"),
        ("name", "Updated {token}"),
    ],
)
def test_unauthorized_user_cannot_update_each_field(
    api, api_url, user, field, new_value
):
    updated_value = new_value.format(token=uuid.uuid4().hex)
    response = api.patch(
        f"{api_url}/api/auth/user",
        json={field: updated_value},
    )

    response_success = response.json().get("success")

    login_response = api.post(
        f"{api_url}/api/auth/login",
        json={"email": user["email"], "password": user["password"]},
    )
    login_body = login_response.json()
    current_user = login_body.get("user", {})
    if field == "password":
        changed_password_response = api.post(
            f"{api_url}/api/auth/login",
            json={"email": user["email"], "password": updated_value},
        )
        changed_password_status = changed_password_response.status_code
        current_value_unchanged = True
    else:
        changed_password_status = None
        current_value_unchanged = current_user.get(field) == user[field]
    assert (
        response.status_code,
        response_success,
        login_response.status_code,
        login_body.get("success"),
        current_value_unchanged,
        changed_password_status,
    ) == (
        401,
        False,
        200,
        True,
        True,
        401 if field == "password" else None,
    ), (response.text, login_response.text)
