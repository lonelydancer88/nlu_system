"""Tests for CoffeeAPIProtocol and MockCoffeeAPI - Meituan interface abstraction."""
import json
import os
import pytest
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture
def mock_api(tmp_path, monkeypatch):
    """Create MockCoffeeAPI pointing to tmp data dir."""
    import modules.coffee_api_client as cac
    monkeypatch.setattr(cac, "DATA_DIR", str(tmp_path))

    # Write sample coffee_shops.json
    coffee_shops = {
        "shops": [
            {
                "id": "shop_1",
                "name": "瑞幸咖啡",
                "address": "望京SOHO T1",
                "location": {"lat": 39.991, "lng": 116.478},
                "menu": [
                    {"id": "101", "name": "拿铁", "price": 18, "sizes": ["中杯", "大杯"], "ice_options": ["热", "少冰"], "sugar_options": ["无糖", "半糖"]},
                    {"id": "102", "name": "美式", "price": 14, "sizes": ["中杯", "大杯"], "ice_options": ["热", "少冰"], "sugar_options": ["无糖"]},
                ]
            },
            {
                "id": "shop_2",
                "name": "星巴克",
                "address": "望京SOHO T2",
                "location": {"lat": 39.992, "lng": 116.479},
                "menu": [
                    {"id": "201", "name": "拿铁", "price": 30, "sizes": ["中杯", "大杯", "超大杯"], "ice_options": ["热", "少冰"], "sugar_options": ["无糖", "半糖"]},
                ]
            }
        ]
    }
    with open(tmp_path / "coffee_shops.json", "w", encoding="utf-8") as f:
        json.dump(coffee_shops, f, ensure_ascii=False)

    api = cac.MockCoffeeAPI()
    api.data_path = str(tmp_path / "coffee_shops.json")
    return api


class TestMockCoffeeAPISearchShops:
    def test_search_all_shops(self, mock_api):
        shops = mock_api.search_shops("")
        assert len(shops) == 2
        assert shops[0]["name"] == "瑞幸咖啡"

    def test_search_by_keyword(self, mock_api):
        shops = mock_api.search_shops("瑞幸")
        assert len(shops) == 1
        assert shops[0]["name"] == "瑞幸咖啡"

    def test_search_no_results(self, mock_api):
        shops = mock_api.search_shops("不存在的店")
        assert shops == []


class TestMockCoffeeAPIGetMenu:
    def test_get_shop_menu(self, mock_api):
        menu = mock_api.get_shop_menu("shop_1")
        assert len(menu) == 2
        assert menu[0]["name"] == "拿铁"
        assert menu[0]["price"] == 18

    def test_get_menu_unknown_shop(self, mock_api):
        menu = mock_api.get_shop_menu("unknown_shop")
        assert menu == []


class TestMockCoffeeAPICreateOrder:
    def test_create_order(self, mock_api):
        order = mock_api.create_order(
            shop_id="shop_1",
            items=[{"coffee_name": "拿铁", "size": "大杯", "ice": "少冰", "sugar": "半糖", "toppings": []}],
            delivery_info={"address": "望京西园四区"}
        )
        assert order["order_id"].startswith("MOCK_")
        assert order["status"] == "pending"
        assert order["shop_id"] == "shop_1"
        assert order["items"][0]["coffee_name"] == "拿铁"

    def test_create_order_price_calculation(self, mock_api):
        order = mock_api.create_order(
            shop_id="shop_1",
            items=[{"coffee_name": "拿铁", "size": "大杯", "ice": "少冰", "sugar": "半糖", "toppings": ["奶盖"]}],
            delivery_info={"address": "望京西园四区"}
        )
        # 18 (拿铁) + 3 (奶盖) = 21
        assert order["total_price"] == 21


class TestMockCoffeeAPIOrderStatus:
    def test_get_order_status(self, mock_api):
        order = mock_api.create_order(
            shop_id="shop_1",
            items=[{"coffee_name": "拿铁", "size": "大杯", "ice": "少冰", "sugar": "半糖", "toppings": []}],
            delivery_info={"address": "test"}
        )
        status = mock_api.get_order_status(order["order_id"])
        assert status["status"] == "pending"

    def test_get_status_unknown_order(self, mock_api):
        status = mock_api.get_order_status("nonexistent_order")
        assert status is None


class TestMockCoffeeAPICancelOrder:
    def test_cancel_order(self, mock_api):
        order = mock_api.create_order(
            shop_id="shop_1",
            items=[{"coffee_name": "拿铁", "size": "大杯", "ice": "少冰", "sugar": "半糖", "toppings": []}],
            delivery_info={"address": "test"}
        )
        result = mock_api.cancel_order(order["order_id"])
        assert result["status"] == "cancelled"

    def test_cancel_unknown_order(self, mock_api):
        result = mock_api.cancel_order("nonexistent_order")
        assert result is None


class TestCoffeeAPIFactory:
    def test_create_mock_api(self, monkeypatch):
        monkeypatch.delenv("COFFEE_API_MODE", raising=False)
        from modules.coffee_api_client import create_coffee_api
        api = create_coffee_api(mode="mock")
        from modules.coffee_api_client import MockCoffeeAPI
        assert isinstance(api, MockCoffeeAPI)

    def test_create_meituan_api(self):
        from modules.coffee_api_client import create_coffee_api, MeituanCoffeeAPI
        api = create_coffee_api(mode="meituan", api_key="test_key")
        assert isinstance(api, MeituanCoffeeAPI)
