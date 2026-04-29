"""Tests for OrderManager - coffee order business logic."""
import json
import os
import pytest
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modules.order_manager import OrderManager
from modules.data_manager import DataManager


@pytest.fixture
def tmp_data_dir(tmp_path):
    coffee_shops = {
        "shops": [
            {
                "id": 1,
                "name": "瑞幸咖啡",
                "menu": [
                    {"id": 101, "name": "拿铁", "price": 18},
                    {"id": 102, "name": "美式", "price": 14},
                    {"id": 103, "name": "生椰拿铁", "price": 22},
                ]
            },
            {
                "id": 2,
                "name": "星巴克",
                "menu": [
                    {"id": 201, "name": "拿铁", "price": 30},
                    {"id": 202, "name": "美式", "price": 25},
                ]
            }
        ]
    }
    with open(tmp_path / "coffee_shops.json", "w", encoding="utf-8") as f:
        json.dump(coffee_shops, f, ensure_ascii=False)

    prefs = {
        "default_shop": "瑞幸咖啡",
        "favorite_coffee": "拿铁",
        "default_size": "大杯",
        "default_ice": "少冰",
        "default_sugar": "半糖",
        "default_toppings": [],
        "last_order": {
            "order_id": "CF1001",
            "shop_name": "瑞幸咖啡",
            "coffee_name": "拿铁",
            "size": "大杯",
            "ice": "少冰",
            "sugar": "半糖",
            "toppings": [],
            "price": 18,
            "create_time": "2026-01-01 09:00:00",
            "status": "completed"
        }
    }
    with open(tmp_path / "user_preferences.json", "w", encoding="utf-8") as f:
        json.dump(prefs, f, ensure_ascii=False)

    with open(tmp_path / "order_history.json", "w", encoding="utf-8") as f:
        json.dump({"orders": []}, f, ensure_ascii=False)

    return tmp_path


@pytest.fixture
def order_manager(tmp_data_dir, monkeypatch):
    import modules.data_manager as dm
    monkeypatch.setattr(dm, "DATA_DIR", str(tmp_data_dir))
    mgr = OrderManager()
    mgr.data_manager.coffee_shops_path = str(tmp_data_dir / "coffee_shops.json")
    mgr.data_manager.user_preferences_path = str(tmp_data_dir / "user_preferences.json")
    mgr.data_manager.order_history_path = str(tmp_data_dir / "order_history.json")
    return mgr


class TestCreateOrder:
    def test_create_order_with_all_params(self, order_manager):
        order = order_manager.create_order({
            "shop_name": "瑞幸咖啡",
            "coffee_name": "拿铁",
            "size": "大杯",
            "ice": "少冰",
            "sugar": "半糖",
            "toppings": []
        })
        assert order["shop_name"] == "瑞幸咖啡"
        assert order["coffee_name"] == "拿铁"
        assert order["price"] == 18
        assert order["status"] == "pending"
        assert order["order_id"].startswith(("CF", "MOCK_"))

    def test_create_order_uses_defaults(self, order_manager):
        order = order_manager.create_order({"coffee_name": "美式"})
        # Defaults from user_preferences
        assert order["shop_name"] == "瑞幸咖啡"
        assert order["size"] == "大杯"
        assert order["ice"] == "少冰"
        assert order["sugar"] == "半糖"

    def test_create_order_with_toppings(self, order_manager):
        order = order_manager.create_order({
            "coffee_name": "拿铁",
            "toppings": ["奶盖", "珍珠"]
        })
        # base 18 + 2 toppings * 3 = 24
        assert order["price"] == 24

    def test_create_order_unknown_coffee(self, order_manager):
        order = order_manager.create_order({"coffee_name": "不存在的咖啡"})
        assert order["price"] == 0

    def test_create_order_sets_pending(self, order_manager):
        order = order_manager.create_order({"coffee_name": "拿铁"})
        assert order_manager.pending_order is not None
        assert order_manager.pending_order["order_id"] == order["order_id"]


class TestConfirmOrder:
    def test_confirm_order(self, order_manager):
        order_manager.create_order({"coffee_name": "拿铁"})
        confirmed = order_manager.confirm_order()
        assert confirmed is not None
        assert confirmed["status"] == "confirmed"

    def test_confirm_order_clears_pending(self, order_manager):
        order_manager.create_order({"coffee_name": "拿铁"})
        order_manager.confirm_order()
        assert order_manager.pending_order is None

    def test_confirm_order_saves_to_history(self, order_manager):
        order_manager.create_order({"coffee_name": "拿铁"})
        order_manager.confirm_order()
        history = order_manager.get_order_history()
        assert len(history) == 1

    def test_confirm_order_updates_preferences(self, order_manager):
        order_manager.create_order({"coffee_name": "美式"})
        order_manager.confirm_order()
        prefs = order_manager.data_manager.get_user_preferences()
        assert prefs["favorite_coffee"] == "美式"

    def test_confirm_without_pending(self, order_manager):
        result = order_manager.confirm_order()
        assert result is None


class TestCancelOrder:
    def test_cancel_order(self, order_manager):
        order_manager.create_order({"coffee_name": "拿铁"})
        ok = order_manager.cancel_order()
        assert ok is True
        assert order_manager.pending_order is None

    def test_cancel_without_pending(self, order_manager):
        ok = order_manager.cancel_order()
        assert ok is False


class TestReorder:
    def test_reorder_last(self, order_manager):
        order = order_manager.reorder_last()
        assert order is not None
        assert order["coffee_name"] == "拿铁"
        assert order["shop_name"] == "瑞幸咖啡"
        assert order["status"] == "pending"

    def test_reorder_no_history(self, tmp_data_dir, monkeypatch):
        import modules.data_manager as dm
        monkeypatch.setattr(dm, "DATA_DIR", str(tmp_data_dir))
        # Write preferences without last_order
        with open(tmp_data_dir / "user_preferences.json", "w", encoding="utf-8") as f:
            json.dump({"default_shop": "瑞幸咖啡"}, f, ensure_ascii=False)

        mgr = OrderManager()
        mgr.data_manager.coffee_shops_path = str(tmp_data_dir / "coffee_shops.json")
        mgr.data_manager.user_preferences_path = str(tmp_data_dir / "user_preferences.json")
        mgr.data_manager.order_history_path = str(tmp_data_dir / "order_history.json")
        result = mgr.reorder_last()
        assert result is None


class TestRecommendations:
    def test_get_recommendations_all(self, order_manager):
        recs = order_manager.get_recommendations()
        assert len(recs) <= 5
        assert all("shop_name" in r and "coffee_name" in r and "price" in r for r in recs)

    def test_get_recommendations_specific_shop(self, order_manager):
        recs = order_manager.get_recommendations(shop_name="瑞幸咖啡")
        assert len(recs) > 0
        assert all(r["shop_name"] == "瑞幸咖啡" for r in recs)

    def test_get_recommendations_unknown_shop(self, order_manager):
        recs = order_manager.get_recommendations(shop_name="不存在")
        assert recs == []


class TestOrderHistory:
    def test_get_order_history_empty(self, order_manager):
        history = order_manager.get_order_history()
        assert history == []

    def test_get_order_history_after_confirm(self, order_manager):
        order_manager.create_order({"coffee_name": "拿铁"})
        order_manager.confirm_order()
        history = order_manager.get_order_history()
        assert len(history) == 1
        assert history[0]["status"] == "confirmed"


class TestPriceCalculation:
    def test_base_price_lookup(self, order_manager):
        order = order_manager.create_order({
            "coffee_name": "生椰拿铁",
            "toppings": []
        })
        assert order["price"] == 22

    def test_different_shop_same_coffee(self, order_manager):
        order = order_manager.create_order({
            "shop_name": "星巴克",
            "coffee_name": "拿铁",
            "toppings": []
        })
        assert order["price"] == 30

    def test_toppings_add_to_price(self, order_manager):
        order1 = order_manager.create_order({
            "coffee_name": "拿铁",
            "toppings": []
        })
        price1 = order1["price"]

        order2 = order_manager.create_order({
            "coffee_name": "拿铁",
            "toppings": ["奶盖", "珍珠", "糖浆"]
        })
        price2 = order2["price"]

        assert price2 - price1 == 9  # 3 toppings * 3 yuan each
