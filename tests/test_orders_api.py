import allure
import pytest


@allure.step("Отправить запрос на создание заказа")
def create_order(api, api_url, ingredients, token=None):
    headers = {"Authorization": token} if token else {}
    return api.post(
        f"{api_url}/api/orders",
        headers=headers,
        json={"ingredients": ingredients},
    )


@allure.step("Получить список заказов пользователя")
def get_user_orders(api, api_url, token=None):
    headers = {"Authorization": token} if token else {}
    return api.get(f"{api_url}/api/orders", headers=headers)


@allure.step("Проверить ответ на создание заказа")
def order_creation_matches(response, expected_status, has_ingredients):
    body = response.json()
    expected_success = has_ingredients
    has_order_number = bool(body.get("order", {}).get("number"))
    return (
        response.status_code == expected_status
        and body.get("success") is expected_success
        and has_order_number is expected_success
    )


@allure.step("Проверить отклонение заказа с неверным хешем ингредиента")
def invalid_ingredient_hash_is_rejected(response):
    return (
        response.status_code == 500
        and "Internal Server Error" in response.text
    )


@allure.step("Проверить наличие созданного заказа в ленте пользователя")
def personal_orders_contain_created_order(create_response, orders_response):
    create_body = (
        create_response.json()
        if create_response.status_code == 200
        else {}
    )
    created_order_number = create_body.get("order", {}).get("number")
    orders_body = orders_response.json()
    orders = orders_body.get("orders", [])
    return (
        create_response.status_code == 200
        and orders_response.status_code == 200
        and orders_body.get("success") is True
        and isinstance(orders, list)
        and any(
            order.get("number") == created_order_number
            for order in orders
            if isinstance(order, dict)
        )
    )


@allure.step("Проверить ответ с ошибкой")
def response_matches_status_and_success(response, status_code, success):
    return (
        response.status_code == status_code
        and response.json().get("success") is success
    )


INGREDIENTS = [
    "691577430cc94f001a65b85a",
    "691577430cc94f001a65b85b",
]


@allure.suite("Заказы")
@allure.sub_suite("Создание заказа")
@allure.feature("Создание заказа")
class TestCreateOrder:
    @pytest.mark.parametrize(
        ("ingredients", "expected_status", "ingredient_case"),
        [
            (INGREDIENTS, 200, "с ингредиентами"),
            ([], 400, "без ингредиентов"),
        ],
        ids=["с ингредиентами", "без ингредиентов"],
    )
    @allure.title("Создание заказа авторизованным пользователем {ingredient_case}")
    def test_authorized_user_can_create_order_with_or_without_ingredients(
        self, api, api_url, user, ingredients, expected_status, ingredient_case
    ):
        response = create_order(
            api,
            api_url,
            ingredients,
            user["accessToken"],
        )

        assert order_creation_matches(
            response,
            expected_status,
            has_ingredients=bool(ingredients),
        )

    @pytest.mark.parametrize(
        ("ingredients", "expected_status", "ingredient_case"),
        [
            (INGREDIENTS, 200, "с ингредиентами"),
            ([], 400, "без ингредиентов"),
        ],
        ids=["с ингредиентами", "без ингредиентов"],
    )
    @allure.title("Создание заказа без авторизации {ingredient_case}")
    def test_guest_can_create_order_with_or_without_ingredients(
        self, api, api_url, ingredients, expected_status, ingredient_case
    ):
        response = create_order(api, api_url, ingredients)

        assert order_creation_matches(
            response,
            expected_status,
            has_ingredients=bool(ingredients),
        )

    @allure.title("Заказ с неверным хешем ингредиента отклонён")
    def test_create_order_rejects_invalid_ingredient_hash(
        self, api, api_url, user
    ):
        response = create_order(
            api,
            api_url,
            ["invalid-ingredient-hash"],
            user["accessToken"],
        )

        assert invalid_ingredient_hash_is_rejected(response)


@allure.suite("Заказы")
@allure.sub_suite("Получение заказов пользователя")
@allure.feature("Заказы пользователя")
class TestUserOrders:
    @allure.title("Авторизованный пользователь получает свои заказы")
    def test_authorized_user_can_get_personal_orders(self, api, api_url, user):
        create_response = create_order(
            api,
            api_url,
            INGREDIENTS,
            user["accessToken"],
        )
        orders_response = get_user_orders(
            api,
            api_url,
            user["accessToken"],
        )

        assert personal_orders_contain_created_order(
            create_response,
            orders_response,
        )

    @allure.title("Неавторизованный пользователь не получает заказы")
    def test_guest_cannot_get_personal_orders(self, api, api_url):
        response = get_user_orders(api, api_url)

        assert response_matches_status_and_success(response, 401, False)
