import pytest


INGREDIENTS = [
    "691577430cc94f001a65b85a",
    "691577430cc94f001a65b85b",
]


@pytest.mark.parametrize(
    ("ingredients", "expected_status"),
    [(INGREDIENTS, 200), ([], 400)],
    ids=["with-ingredients", "without-ingredients"],
)
def test_authorized_user_can_create_order_with_or_without_ingredients(
    api, api_url, user, ingredients, expected_status
):
    response = api.post(
        f"{api_url}/api/orders",
        headers={"Authorization": user["accessToken"]},
        json={"ingredients": ingredients},
    )

    body = response.json()
    expected_success = bool(ingredients)
    has_order_number = bool(body.get("order", {}).get("number"))
    assert (
        response.status_code,
        body.get("success"),
        has_order_number,
    ) == (
        expected_status,
        expected_success,
        expected_success,
    ), response.text


@pytest.mark.parametrize(
    ("ingredients", "expected_status"),
    [(INGREDIENTS, 200), ([], 400)],
    ids=["with-ingredients", "without-ingredients"],
)
def test_guest_can_create_order_with_or_without_ingredients(
    api, api_url, ingredients, expected_status
):
    response = api.post(
        f"{api_url}/api/orders",
        json={"ingredients": ingredients},
    )

    body = response.json()
    expected_success = bool(ingredients)
    has_order_number = bool(body.get("order", {}).get("number"))
    assert (
        response.status_code,
        body.get("success"),
        has_order_number,
    ) == (
        expected_status,
        expected_success,
        expected_success,
    ), response.text


def test_create_order_rejects_invalid_ingredient_hash(api, api_url, user):
    response = api.post(
        f"{api_url}/api/orders",
        headers={"Authorization": user["accessToken"]},
        json={"ingredients": ["invalid-ingredient-hash"]},
    )

    assert (
        response.status_code,
        "Internal Server Error" in response.text,
    ) == (500, True)


def test_authorized_user_can_get_personal_orders(api, api_url, user):
    create_response = api.post(
        f"{api_url}/api/orders",
        headers={"Authorization": user["accessToken"]},
        json={"ingredients": INGREDIENTS},
    )
    create_body = (
        create_response.json()
        if create_response.status_code == 200
        else {}
    )
    created_order_number = create_body.get("order", {}).get("number")

    response = api.get(
        f"{api_url}/api/orders",
        headers={"Authorization": user["accessToken"]},
    )

    body = response.json()
    orders = body.get("orders", [])
    assert (
        create_response.status_code,
        response.status_code,
        body.get("success"),
        isinstance(orders, list),
        any(
            order.get("number") == created_order_number
            for order in orders
            if isinstance(order, dict)
        ),
    ) == (200, 200, True, True, True), response.text


def test_guest_cannot_get_personal_orders(api, api_url):
    response = api.get(f"{api_url}/api/orders")

    assert (response.status_code, response.json().get("success")) == (
        401,
        False,
    )
