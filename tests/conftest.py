"""Tests for DataManager - coffee data persistence layer."""
import json
import os
import pytest
import tempfile

# Add project root to path
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modules.data_manager import DataManager


@pytest.fixture
def tmp_data_dir(tmp_path):
    """Create a temporary data directory with sample data."""
    # coffee_shops.json
    coffee_shops = {
        "shops": [
            {
                "id": 1,
                "name": "瑞幸咖啡",
                "menu": [
                    {"id": 101, "name": "拿铁", "price": 18},
                    {"id": 102, "name": "美式", "price": 14},
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

    # user_preferences.json
    prefs = {
        "default_shop": "瑞幸咖啡",
        "favorite_coffee": "拿铁",
        "default_size": "大杯",
        "default_ice": "少冰",
        "default_sugar": "半糖",
        "default_toppings": [],
        "last_order": {
            "order_id": "CF1234",
            "shop_name": "瑞幸咖啡",
            "coffee_name": "拿铁",
            "size": "大杯",
            "ice": "少冰",
            "sugar": "半糖",
            "toppings": [],
            "price": 18,
            "create_time": "2026-01-01 10:00:00",
            "status": "completed"
        }
    }
    with open(tmp_path / "user_preferences.json", "w", encoding="utf-8") as f:
        json.dump(prefs, f, ensure_ascii=False)

    # order_history.json
    history = {
        "orders": [
            {
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
            },
            {
                "order_id": "CF1002",
                "shop_name": "星巴克",
                "coffee_name": "美式",
                "size": "大杯",
                "ice": "正常冰",
                "sugar": "无糖",
                "toppings": ["奶盖"],
                "price": 28,
                "create_time": "2026-01-02 10:00:00",
                "status": "completed"
            }
        ]
    }
    with open(tmp_path / "order_history.json", "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False)

    return tmp_path


@pytest.fixture
def data_manager(tmp_data_dir, monkeypatch):
    """Create a DataManager pointing to tmp data dir."""
    import modules.data_manager as dm
    monkeypatch.setattr(dm, "DATA_DIR", str(tmp_data_dir))
    mgr = DataManager()
    mgr.coffee_shops_path = str(tmp_data_dir / "coffee_shops.json")
    mgr.user_preferences_path = str(tmp_data_dir / "user_preferences.json")
    mgr.order_history_path = str(tmp_data_dir / "order_history.json")
    return mgr


class TestCoffeeShops:
    def test_get_all_shops(self, data_manager):
        shops = data_manager.get_all_coffee_shops()
        assert len(shops) == 2
        assert shops[0]["name"] == "瑞幸咖啡"
        assert shops[1]["name"] == "星巴克"

    def test_get_shop_by_name_found(self, data_manager):
        shop = data_manager.get_coffee_shop_by_name("瑞幸咖啡")
        assert shop is not None
        assert shop["id"] == 1

    def test_get_shop_by_name_not_found(self, data_manager):
        shop = data_manager.get_coffee_shop_by_name("不存在")
        assert shop is None


class TestUserPreferences:
    def test_get_preferences(self, data_manager):
        prefs = data_manager.get_user_preferences()
        assert prefs["default_shop"] == "瑞幸咖啡"
        assert prefs["favorite_coffee"] == "拿铁"

    def test_update_preferences(self, data_manager):
        ok = data_manager.update_user_preferences({"favorite_coffee": "美式"})
        assert ok is True
        prefs = data_manager.get_user_preferences()
        assert prefs["favorite_coffee"] == "美式"
        # Existing keys preserved
        assert prefs["default_shop"] == "瑞幸咖啡"


class TestOrderHistory:
    def test_get_order_history(self, data_manager):
        orders = data_manager.get_order_history(limit=10)
        assert len(orders) == 2
        # Most recent first
        assert orders[0]["order_id"] == "CF1002"

    def test_get_order_history_with_limit(self, data_manager):
        orders = data_manager.get_order_history(limit=1)
        assert len(orders) == 1
        assert orders[0]["order_id"] == "CF1002"

    def test_add_order(self, data_manager):
        new_order = {
            "order_id": "CF1003",
            "shop_name": "Manner",
            "coffee_name": "澳白",
            "price": 18,
            "create_time": "2026-01-03 11:00:00",
            "status": "completed"
        }
        ok = data_manager.add_order(new_order)
        assert ok is True
        orders = data_manager.get_order_history(limit=10)
        assert len(orders) == 3
        assert orders[0]["order_id"] == "CF1003"


class TestEdgeCases:
    def test_missing_file_returns_default(self, tmp_data_dir, monkeypatch):
        import modules.data_manager as dm
        monkeypatch.setattr(dm, "DATA_DIR", str(tmp_data_dir))
        mgr = DataManager()
        mgr.coffee_shops_path = str(tmp_data_dir / "nonexistent.json")
        shops = mgr.get_all_coffee_shops()
        assert shops == []

    def test_corrupt_json_returns_default(self, tmp_data_dir, monkeypatch):
        import modules.data_manager as dm
        monkeypatch.setattr(dm, "DATA_DIR", str(tmp_data_dir))
        # Write invalid JSON
        with open(tmp_data_dir / "corrupt.json", "w") as f:
            f.write("{invalid json")
        mgr = DataManager()
        mgr.coffee_shops_path = str(tmp_data_dir / "corrupt.json")
        shops = mgr.get_all_coffee_shops()
        assert shops == []
