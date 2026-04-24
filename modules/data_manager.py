import json
import os
from typing import Dict, List, Any

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


class DataManager:
    def __init__(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        self.coffee_shops_path = os.path.join(DATA_DIR, "coffee_shops.json")
        self.user_preferences_path = os.path.join(DATA_DIR, "user_preferences.json")
        self.order_history_path = os.path.join(DATA_DIR, "order_history.json")

    def _load_json(self, file_path: str, default: Any = None) -> Any:
        if not os.path.exists(file_path):
            return default or {}
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return default or {}

    def _save_json(self, file_path: str, data: Any) -> bool:
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except IOError:
            return False

    # 咖啡店数据操作
    def get_all_coffee_shops(self) -> List[Dict]:
        data = self._load_json(self.coffee_shops_path, {"shops": []})
        return data.get("shops", [])

    def get_coffee_shop_by_name(self, name: str) -> Dict | None:
        shops = self.get_all_coffee_shops()
        for shop in shops:
            if shop["name"] == name:
                return shop
        return None

    # 用户偏好操作
    def get_user_preferences(self) -> Dict:
        return self._load_json(self.user_preferences_path, {})

    def update_user_preferences(self, new_preferences: Dict) -> bool:
        prefs = self.get_user_preferences()
        prefs.update(new_preferences)
        return self._save_json(self.user_preferences_path, prefs)

    # 订单历史操作
    def get_order_history(self, limit: int = 10) -> List[Dict]:
        data = self._load_json(self.order_history_path, {"orders": []})
        orders = data.get("orders", [])
        return orders[-limit:][::-1]

    def add_order(self, order: Dict) -> bool:
        data = self._load_json(self.order_history_path, {"orders": []})
        if "orders" not in data:
            data["orders"] = []
        data["orders"].append(order)
        return self._save_json(self.order_history_path, data)
