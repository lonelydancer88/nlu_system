"""Tests for rewritten OrderManager - using CoffeeAPIClient abstraction."""
import json
import os
import pytest
import sys
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modules.order_manager import OrderManager
from modules.coffee_api_client import MockCoffeeAPI, CoffeeAPIProtocol


@pytest.fixture
def mock_coffee_api():
    api = MagicMock(spec=CoffeeAPIProtocol)
    return api


@pytest.fixture
def tmp_data_dir(tmp_path, monkeypatch):
    import modules.data_manager as dm
    monkeypatch.setattr(dm, "DATA_DIR", str(tmp_path))

    prefs = {
        "default_shop": "瑞幸咖啡",
        "favorite_coffee": "拿铁",
        "default_size": "大杯",
        "default_ice": "少冰",
        "default_sugar": "半糖",
        "default_toppings": [],
        "last_order": {
            "order_id": "CF1001", "shop_name": "瑞幸咖啡", "coffee_name": "拿铁",
            "size": "大杯", "ice": "少冰", "sugar": "半糖", "toppings": [],
            "price": 18, "create_time": "2026-01-01 09:00:00", "status": "completed"
        }
    }
    with open(tmp_path / "user_preferences.json", "w", encoding="utf-8") as f:
        json.dump(prefs, f, ensure_ascii=False)

    with open(tmp_path / "order_history.json", "w", encoding="utf-8") as f:
        json.dump({"orders": []}, f, ensure_ascii=False)

    coffee_shops = {
        "shops": [{"id": 1, "name": "瑞幸咖啡", "menu": [{"id": 101, "name": "拿铁", "price": 18}]}]
    }
    with open(tmp_path / "coffee_shops.json", "w", encoding="utf-8") as f:
        json.dump(coffee_shops, f, ensure_ascii=False)

    return tmp_path


@pytest.fixture
def order_manager(mock_coffee_api, tmp_data_dir):
    mgr = OrderManager(coffee_api=mock_coffee_api)
    mgr.data_manager.user_preferences_path = str(tmp_data_dir / "user_preferences.json")
    mgr.data_manager.order_history_path = str(tmp_data_dir / "order_history.json")
    mgr.data_manager.coffee_shops_path = str(tmp_data_dir / "coffee_shops.json")
    return mgr


class TestSearchShops:
    def test_search_shops_calls_api(self, order_manager, mock_coffee_api):
        mock_coffee_api.search_shops.return_value = [
            {"id": "shop_1", "name": "瑞幸咖啡", "address": "望京SOHO"}
        ]
        shops = order_manager.search_shops("瑞幸")
        mock_coffee_api.search_shops.assert_called_once_with("瑞幸")
        assert len(shops) == 1
        assert shops[0]["name"] == "瑞幸咖啡"

    def test_search_shops_empty_keyword(self, order_manager, mock_coffee_api):
        mock_coffee_api.search_shops.return_value = [
            {"id": "shop_1", "name": "瑞幸咖啡"},
            {"id": "shop_2", "name": "星巴克"}
        ]
        shops = order_manager.search_shops("")
        assert len(shops) == 2


class TestGetMenu:
    def test_get_menu_calls_api(self, order_manager, mock_coffee_api):
        mock_coffee_api.get_shop_menu.return_value = [
            {"name": "拿铁", "price": 18},
            {"name": "美式", "price": 14}
        ]
        menu = order_manager.get_shop_menu("shop_1")
        mock_coffee_api.get_shop_menu.assert_called_once_with("shop_1")
        assert len(menu) == 2


class TestCreateOrderWithAPI:
    def test_create_order_calls_api(self, order_manager, mock_coffee_api):
        mock_coffee_api.create_order.return_value = {
            "order_id": "MOCK_123", "status": "pending", "total_price": 18,
            "items": [{"coffee_name": "拿铁", "size": "大杯", "ice": "少冰", "sugar": "半糖", "toppings": []}]
        }
        order = order_manager.create_order({
            "shop_id": "shop_1",
            "coffee_name": "拿铁",
            "size": "大杯",
            "ice": "少冰",
            "sugar": "半糖",
            "toppings": []
        })
        assert order["order_id"] == "MOCK_123"
        assert order_manager.pending_order is not None

    def test_create_order_with_coffee_name_only(self, order_manager, mock_coffee_api):
        """When only coffee_name given, should use defaults and search for shop."""
        mock_coffee_api.search_shops.return_value = [{"id": "shop_1", "name": "瑞幸咖啡"}]
        mock_coffee_api.create_order.return_value = {
            "order_id": "MOCK_456", "status": "pending", "total_price": 18,
            "items": [{"coffee_name": "拿铁", "size": "大杯", "ice": "少冰", "sugar": "半糖", "toppings": []}]
        }
        order = order_manager.create_order({"coffee_name": "拿铁"})
        assert order is not None


class TestConfirmOrder:
    def test_confirm_order(self, order_manager, mock_coffee_api):
        mock_coffee_api.create_order.return_value = {
            "order_id": "MOCK_789", "status": "pending", "total_price": 18,
            "items": [{"coffee_name": "拿铁", "size": "大杯", "ice": "少冰", "sugar": "半糖", "toppings": []}]
        }
        order_manager.create_order({"coffee_name": "拿铁"})
        confirmed = order_manager.confirm_order()
        assert confirmed is not None
        assert confirmed["status"] == "confirmed"
        assert order_manager.pending_order is None

    def test_confirm_without_pending(self, order_manager):
        result = order_manager.confirm_order()
        assert result is None


class TestCancelOrder:
    def test_cancel_order(self, order_manager, mock_coffee_api):
        mock_coffee_api.create_order.return_value = {
            "order_id": "MOCK_999", "status": "pending", "total_price": 18,
            "items": [{"coffee_name": "拿铁", "size": "大杯", "ice": "少冰", "sugar": "半糖", "toppings": []}]
        }
        order_manager.create_order({"coffee_name": "拿铁"})
        ok = order_manager.cancel_order()
        assert ok is True
        assert order_manager.pending_order is None

    def test_cancel_calls_api(self, order_manager, mock_coffee_api):
        mock_coffee_api.create_order.return_value = {
            "order_id": "MOCK_888", "status": "pending", "total_price": 18,
            "items": [{"coffee_name": "拿铁", "size": "大杯", "ice": "少冰", "sugar": "半糖", "toppings": []}]
        }
        order_manager.create_order({"coffee_name": "拿铁"})
        order_manager.cancel_order()
        mock_coffee_api.cancel_order.assert_called_once_with("MOCK_888")


class TestReorder:
    def test_reorder_last(self, order_manager, mock_coffee_api):
        mock_coffee_api.create_order.return_value = {
            "order_id": "MOCK_RE", "status": "pending", "total_price": 18,
            "items": [{"coffee_name": "拿铁", "size": "大杯", "ice": "少冰", "sugar": "半糖", "toppings": []}]
        }
        order = order_manager.reorder_last()
        assert order is not None
        assert order["order_id"] == "MOCK_RE"


class TestRecommendations:
    def test_get_recommendations(self, order_manager, mock_coffee_api):
        mock_coffee_api.search_shops.return_value = [{"id": "shop_1", "name": "瑞幸咖啡"}]
        mock_coffee_api.get_shop_menu.return_value = [
            {"name": "拿铁", "price": 18},
            {"name": "美式", "price": 14},
            {"name": "生椰拿铁", "price": 22}
        ]
        recs = order_manager.get_recommendations()
        assert len(recs) <= 5
        assert all("coffee_name" in r and "price" in r for r in recs)
