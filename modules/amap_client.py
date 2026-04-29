"""Amap (Gaode) Web Services API client."""
from typing import Dict, List, Optional
from .api_client import APIClientBase


class AmapClient(APIClientBase):
    def __init__(self, api_key: str, timeout: int = 10, max_retries: int = 1):
        super().__init__(
            base_url="https://restapi.amap.com/v3",
            api_key=api_key,
            timeout=timeout,
            max_retries=max_retries
        )

    def geocode(self, address: str, city: str = None) -> Dict:
        params = {"address": address}
        if city:
            params["city"] = city
        return self.get("/geocode/geo", params)

    def reverse_geocode(self, location: str) -> Dict:
        return self.get("/regeo", {"location": location})

    def driving_direction(self, origin: str, destination: str, waypoints: str = None) -> Dict:
        params = {
            "origin": origin,
            "destination": destination,
            "extensions": "base"
        }
        if waypoints:
            params["waypoints"] = waypoints
        return self.get("/direction/driving", params)

    def search_poi(self, keywords: str, city: str = None, location: str = None, radius: int = None) -> List[Dict]:
        params = {"keywords": keywords}
        if city:
            params["city"] = city
        if location:
            params["location"] = location
        if radius:
            params["radius"] = radius
        result = self.get("/place/text", params)
        if result.get("status") == "1":
            return result.get("pois", [])
        return []

    def search_along_route(self, keywords: str, origin: str, destination: str) -> List[Dict]:
        params = {
            "keywords": keywords,
            "origin": origin,
            "destination": destination
        }
        result = self.get("/place/text", params)
        if result.get("status") == "1":
            return result.get("pois", [])
        return []

    def traffic_info(self, city: str, road_name: str = None) -> Dict:
        params = {"city": city, "extensions": "all"}
        if road_name:
            params["roadName"] = road_name
        return self.get("/trafficstatus/rect", params)

    def format_route(self, api_response: Dict, destination_name: str = "") -> Optional[Dict]:
        paths = api_response.get("route", {}).get("paths", [])
        if not paths:
            return None
        path = paths[0]
        return self._format_single_path(path, destination_name)

    def format_routes(self, api_response: Dict, destination_name: str = "") -> List[Dict]:
        paths = api_response.get("route", {}).get("paths", [])
        return [self._format_single_path(p, destination_name) for p in paths]

    def _format_single_path(self, path: Dict, destination_name: str) -> Dict:
        distance_m = int(path.get("distance", "0"))
        duration_s = int(path.get("duration", "0"))
        tolls = int(path.get("tolls", "0"))

        steps = []
        for step in path.get("steps", []):
            steps.append({
                "instruction": step.get("instruction", ""),
                "distance": int(step.get("distance", "0"))
            })

        return {
            "id": "",
            "from": "当前位置",
            "to": destination_name,
            "to_address": "",
            "distance_km": round(distance_m / 1000, 1),
            "duration_min": round(duration_s / 60),
            "toll": tolls > 0,
            "traffic_level": "smooth",
            "traffic_level_cn": "畅通",
            "steps": steps
        }
