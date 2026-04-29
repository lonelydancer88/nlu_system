"""Meituan coffee API abstraction layer with mock implementation."""
import json
import os
import time
from typing import Dict, List, Optional, Protocol

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


class CoffeeAPIProtocol(Protocol):
    def search_shops(self, keyword: str, location: str = "", radius: int = 5000) -> List[Dict]:
        ...

    def get_shop_menu(self, shop_id: str) -> List[Dict]:
        ...

    def create_order(self, shop_id: str, items: List[Dict], delivery_info: Dict) -> Dict:
        ...

    def get_order_status(self, order_id: str) -> Optional[Dict]:
        ...

    def cancel_order(self, order_id: str) -> Optional[Dict]:
        ...


class MockCoffeeAPI:
    """Mock implementation using local JSON data, simulating Meituan API format."""

    def __init__(self):
        self.data_path = os.path.join(DATA_DIR, "coffee_shops.json")
        self._orders: Dict[str, Dict] = {}

    def _load_shops(self) -> List[Dict]:
        if not os.path.exists(self.data_path):
            return []
        try:
            with open(self.data_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("shops", [])
        except (json.JSONDecodeError, IOError):
            return []

    def search_shops(self, keyword: str, location: str = "", radius: int = 5000) -> List[Dict]:
        shops = self._load_shops()
        if not keyword:
            return [
                {"id": s["id"], "name": s["name"], "address": s.get("address", ""),
                 "location": s.get("location", {})}
                for s in shops
            ]
        return [
            {"id": s["id"], "name": s["name"], "address": s.get("address", ""),
             "location": s.get("location", {})}
            for s in shops if keyword in s["name"]
        ]

    def get_shop_menu(self, shop_id: str) -> List[Dict]:
        shops = self._load_shops()
        for shop in shops:
            if shop["id"] == shop_id:
                return shop.get("menu", [])
        return []

    def create_order(self, shop_id: str, items: List[Dict], delivery_info: Dict) -> Dict:
        shops = self._load_shops()
        shop = next((s for s in shops if s["id"] == shop_id), None)

        total_price = 0
        for item in items:
            # Look up base price
            base_price = 0
            if shop:
                for menu_item in shop.get("menu", []):
                    if menu_item["name"] == item.get("coffee_name"):
                        base_price = menu_item["price"]
                        break
            toppings_price = len(item.get("toppings", [])) * 3
            total_price += base_price + toppings_price

        order_id = f"MOCK_{int(time.time())}"
        order = {
            "order_id": order_id,
            "shop_id": shop_id,
            "items": items,
            "delivery_info": delivery_info,
            "total_price": total_price,
            "status": "pending",
            "create_time": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        self._orders[order_id] = order
        return order

    def get_order_status(self, order_id: str) -> Optional[Dict]:
        order = self._orders.get(order_id)
        if not order:
            return None
        return {"order_id": order_id, "status": order["status"]}

    def cancel_order(self, order_id: str) -> Optional[Dict]:
        order = self._orders.get(order_id)
        if not order:
            return None
        order["status"] = "cancelled"
        return {"order_id": order_id, "status": "cancelled"}


class MeituanCoffeeAPI:
    """Real Meituan API implementation (placeholder for future integration)."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        # TODO: Initialize Meituan SDK when available

    def search_shops(self, keyword: str, location: str = "", radius: int = 5000) -> List[Dict]:
        raise NotImplementedError("Meituan API integration not yet available")

    def get_shop_menu(self, shop_id: str) -> List[Dict]:
        raise NotImplementedError("Meituan API integration not yet available")

    def create_order(self, shop_id: str, items: List[Dict], delivery_info: Dict) -> Dict:
        raise NotImplementedError("Meituan API integration not yet available")

    def get_order_status(self, order_id: str) -> Optional[Dict]:
        raise NotImplementedError("Meituan API integration not yet available")

    def cancel_order(self, order_id: str) -> Optional[Dict]:
        raise NotImplementedError("Meituan API integration not yet available")


def create_coffee_api(mode: str = "mock", api_key: str = "") -> CoffeeAPIProtocol:
    if mode == "meituan":
        return MeituanCoffeeAPI(api_key=api_key)
    return MockCoffeeAPI()
