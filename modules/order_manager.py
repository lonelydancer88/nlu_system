"""OrderManager - coffee order business logic with CoffeeAPIClient abstraction."""
import time
from typing import Dict, List, Optional
from .data_manager import DataManager
from .coffee_api_client import CoffeeAPIProtocol, MockCoffeeAPI


class OrderManager:
    def __init__(self, coffee_api: CoffeeAPIProtocol = None):
        self.data_manager = DataManager()
        self.coffee_api = coffee_api or MockCoffeeAPI()
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

    def search_shops(self, keyword: str) -> List[Dict]:
        return self.coffee_api.search_shops(keyword)

    def get_shop_menu(self, shop_id: str) -> List[Dict]:
        return self.coffee_api.get_shop_menu(shop_id)

    def create_order(self, params: Dict) -> Dict:
        prefs = self.data_manager.get_user_preferences()

        shop_name = params.get("shop_name", prefs.get("default_shop", "瑞幸咖啡"))
        coffee_name = params.get("coffee_name", prefs.get("favorite_coffee", "拿铁"))
        size = params.get("size", prefs.get("default_size", "大杯"))
        ice = params.get("ice", prefs.get("default_ice", "少冰"))
        sugar = params.get("sugar", prefs.get("default_sugar", "半糖"))
        toppings = params.get("toppings", prefs.get("default_toppings", []))

        # Resolve shop_id: use provided, or search by name
        shop_id = params.get("shop_id")
        if not shop_id:
            shops = self.coffee_api.search_shops(shop_name)
            shop_id = shops[0]["id"] if shops else "unknown"

        items = [{
            "coffee_name": coffee_name,
            "size": size,
            "ice": ice,
            "sugar": sugar,
            "toppings": toppings
        }]

        # Try API order creation
        api_order = self.coffee_api.create_order(
            shop_id=shop_id,
            items=items,
            delivery_info={"address": "当前位置"}
        )

        order = {
            "order_id": api_order.get("order_id", self._generate_order_id()),
            "shop_name": shop_name,
            "coffee_name": coffee_name,
            "size": size,
            "ice": ice,
            "sugar": sugar,
            "toppings": toppings,
            "price": api_order.get("total_price", 0),
            "create_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "status": "pending",
            "_api_order_id": api_order.get("order_id")
        }

        # Fallback price calculation if API didn't return one
        if order["price"] == 0:
            base_price = self._get_coffee_price(shop_name, coffee_name)
            toppings_price = len(toppings) * 3
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
        api_order_id = self.pending_order.get("_api_order_id")
        if api_order_id:
            self.coffee_api.cancel_order(api_order_id)
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
            shops = self.coffee_api.search_shops(shop_name)
        else:
            shops = self.coffee_api.search_shops("")

        recommendations = []
        for shop in shops[:3]:
            shop_id = shop.get("id", "")
            menu = self.coffee_api.get_shop_menu(shop_id)
            for item in menu[:3]:
                recommendations.append({
                    "shop_name": shop["name"],
                    "coffee_name": item["name"],
                    "price": item.get("price", 0)
                })
            if len(recommendations) >= 5:
                break

        return recommendations[:5]
