import json
import os
from typing import Dict, List, Any, Optional

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


class NavigationDataManager:
    def __init__(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        self.pois_path = os.path.join(DATA_DIR, "nav_pois.json")
        self.favorites_path = os.path.join(DATA_DIR, "nav_favorites.json")
        self.vehicle_status_path = os.path.join(DATA_DIR, "nav_vehicle_status.json")
        self.routes_path = os.path.join(DATA_DIR, "nav_routes.json")

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

    # POI 操作
    def get_all_pois(self) -> List[Dict]:
        data = self._load_json(self.pois_path, {"pois": []})
        return data.get("pois", [])

    def get_pois_by_type(self, poi_type: str, limit: int = 5) -> List[Dict]:
        pois = self.get_all_pois()
        type_map = {
            "gas_station": "gas_station",
            "加油站": "gas_station",
            "restaurant": "restaurant",
            "餐厅": "restaurant",
            "parking": "parking",
            "停车场": "parking",
            "charging_station": "charging_station",
            "充电站": "charging_station",
            "hospital": "hospital",
            "医院": "hospital",
            "bank": "bank",
            "银行": "bank",
            "supermarket": "supermarket",
            "超市": "supermarket",
            "shopping": "shopping",
            "商场": "shopping",
        }
        mapped_type = type_map.get(poi_type, poi_type)
        filtered = [p for p in pois if p["type"] == mapped_type]
        return filtered[:limit]

    def search_pois_by_name(self, keyword: str) -> List[Dict]:
        pois = self.get_all_pois()
        return [p for p in pois if keyword in p["name"]]

    # 收藏地点操作
    def get_home(self) -> Optional[Dict]:
        data = self._load_json(self.favorites_path, {})
        return data.get("home")

    def get_company(self) -> Optional[Dict]:
        data = self._load_json(self.favorites_path, {})
        return data.get("company")

    def get_favorites(self) -> List[Dict]:
        data = self._load_json(self.favorites_path, {"favorites": []})
        return data.get("favorites", [])

    def get_favorite_by_name(self, name: str) -> Optional[Dict]:
        favorites = self.get_favorites()
        for fav in favorites:
            if name in fav["name"]:
                return fav
        return None

    def add_favorite(self, place: Dict) -> bool:
        data = self._load_json(self.favorites_path, {"favorites": []})
        if "favorites" not in data:
            data["favorites"] = []
        data["favorites"].append(place)
        return self._save_json(self.favorites_path, data)

    # 车辆状态操作
    def get_vehicle_status(self) -> Dict:
        return self._load_json(self.vehicle_status_path, {
            "fuel_level": 0,
            "fuel_range_km": 0,
            "vehicle_type": "fuel"
        })

    def update_vehicle_status(self, updates: Dict) -> bool:
        status = self.get_vehicle_status()
        status.update(updates)
        return self._save_json(self.vehicle_status_path, status)

    # 路线数据操作
    def get_all_routes(self) -> List[Dict]:
        data = self._load_json(self.routes_path, {"routes": []})
        return data.get("routes", [])

    def get_route(self, from_loc: str = None, to_loc: str = None, avoid_toll: bool = False) -> Optional[Dict]:
        routes = self.get_all_routes()
        for route in routes:
            match = True
            if from_loc and from_loc not in route.get("from", ""):
                match = False
            if to_loc and to_loc not in route.get("to", ""):
                match = False
            if avoid_toll and not route.get("avoid_toll"):
                match = False
            if not avoid_toll and route.get("avoid_toll"):
                match = False
            if match:
                return route
        # 没有精确匹配时，返回第一条路线
        if routes and not avoid_toll:
            return routes[0]
        return None

    # 目的地搜索（跨POI和收藏）
    def search_destination(self, name: str) -> List[Dict]:
        results = []

        # 搜索POI：只匹配POI名称以目标开头且类型为shopping（商场类区域名）
        # 其他POI（加油站、餐厅等）不作为目的地匹配
        for poi in self.get_all_pois():
            poi_name = poi["name"]
            if poi_name == name or poi_name.startswith(name):
                # 只有商场类或精确匹配才作为目的地
                if poi.get("type") == "shopping" or poi_name == name:
                    results.append({
                        "name": poi_name,
                        "address": poi["address"],
                        "location": poi["location"],
                        "type": "poi"
                    })

        # 搜索收藏
        home = self.get_home()
        if home and home.get("name") == name:
            results.append({**home, "type": "home"})
        company = self.get_company()
        if company and company.get("name") == name:
            results.append({**company, "type": "company"})
        for fav in self.get_favorites():
            if name in fav["name"]:
                results.append({**fav, "type": "favorite"})

        return results
