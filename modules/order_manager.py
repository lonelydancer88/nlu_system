import time
from typing import Dict, List, Optional
from .data_manager import DataManager


class OrderManager:
    def __init__(self):
        self.data_manager = DataManager()
        self.pending_order: Optional[Dict] = None

    def _generate_order_id(self) -> str:
        timestamp = int(time.time())
        return f"CF{timestamp}"

    def _get_coffee_price(self, shop_name: str, coffee_name: str) -> int:
        shop = self.data_manager.get_coffee_shop_by_name(shop_name)
        if not shop:
            return 0
        for item in shop["menu"]:
            if item["name"] == coffee_name:
                return item["price"]
        return 0

    def create_order(self, params: Dict) -> Dict:
        prefs = self.data_manager.get_user_preferences()

        order = {
            "order_id": self._generate_order_id(),
            "shop_name": params.get("shop_name", prefs.get("default_shop", "瑞幸咖啡")),
            "coffee_name": params.get("coffee_name", prefs.get("favorite_coffee", "拿铁")),
            "size": params.get("size", prefs.get("default_size", "大杯")),
            "ice": params.get("ice", prefs.get("default_ice", "少冰")),
            "sugar": params.get("sugar", prefs.get("default_sugar", "半糖")),
            "toppings": params.get("toppings", prefs.get("default_toppings", [])),
            "create_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "status": "pending"
        }

        base_price = self._get_coffee_price(order["shop_name"], order["coffee_name"])
        toppings_price = len(order["toppings"]) * 3
        order["price"] = base_price + toppings_price

        self.pending_order = order
        return order

    def confirm_order(self) -> Optional[Dict]:
        if not self.pending_order:
            return None

        self.pending_order["status"] = "confirmed"
        self.data_manager.add_order(self.pending_order.copy())

        self.data_manager.update_user_preferences({
            "last_order": self.pending_order,
            "favorite_coffee": self.pending_order["coffee_name"]
        })

        confirmed_order = self.pending_order
        self.pending_order = None
        return confirmed_order

    def cancel_order(self) -> bool:
        if not self.pending_order:
            return False
        self.pending_order = None
        return True

    def reorder_last(self) -> Optional[Dict]:
        prefs = self.data_manager.get_user_preferences()
        last_order = prefs.get("last_order")
        if not last_order:
            return None

        new_order = self.create_order({
            "shop_name": last_order["shop_name"],
            "coffee_name": last_order["coffee_name"],
            "size": last_order["size"],
            "ice": last_order["ice"],
            "sugar": last_order["sugar"],
            "toppings": last_order["toppings"]
        })
        return new_order

    def get_order_history(self, limit: int = 5) -> List[Dict]:
        return self.data_manager.get_order_history(limit)

    def get_recommendations(self, shop_name: Optional[str] = None) -> List[Dict]:
        if shop_name:
            shop = self.data_manager.get_coffee_shop_by_name(shop_name)
            shops = [shop] if shop else []
        else:
            shops = self.data_manager.get_all_coffee_shops()

        recommendations = []
        for shop in shops:
            popular_items = shop["menu"][:3]
            for item in popular_items:
                recommendations.append({
                    "shop_name": shop["name"],
                    "coffee_name": item["name"],
                    "price": item["price"]
                })

        return recommendations[:5]
