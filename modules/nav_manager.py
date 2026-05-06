"""NavigationManager - business logic using AmapClient for real API data."""
import time
import random
from typing import Dict, List, Optional
from .nav_data_manager import NavigationDataManager
from .amap_client import AmapClient


class NavigationManager:
    def __init__(self, amap_client: AmapClient = None, city: str = "北京"):
        self.amap = amap_client
        self.city = city
        self.data_manager = NavigationDataManager()
        self.nav_state = "idle"  # idle | planning | navigating
        self.current_route = None
        self.pending_destinations = None
        self.navigation_session = None
        self._origin_location = None  # Set when route is planned
        self._dest_location = None

    def _generate_route_id(self) -> str:
        timestamp = int(time.time())
        return f"NR{timestamp}"

    def _make_synthetic_route(self, destination: str, avoid_toll: bool = False) -> Dict:
        """Fallback synthetic route when API is unavailable."""
        distance = round(random.uniform(5, 30), 1)
        speed = random.choice([25, 30, 35, 40])
        duration = int(distance / speed * 60)
        traffic = random.choice(["smooth", "slow", "congested"])
        traffic_cn = {"smooth": "畅通", "slow": "缓行", "congested": "拥堵"}
        return {
            "id": self._generate_route_id(),
            "from": "当前位置",
            "to": destination,
            "distance_km": distance,
            "duration_min": duration,
            "toll": not avoid_toll and random.choice([True, False]),
            "traffic_level": traffic,
            "traffic_level_cn": traffic_cn[traffic],
            "steps": [
                {"instruction": f"沿当前道路行驶1公里", "distance": 1000},
                {"instruction": f"按导航指引前往{destination}", "distance": int(distance * 1000 * 0.8)},
                {"instruction": f"到达{destination}", "distance": 0}
            ]
        }

    def _format_route_response(self, route: Dict) -> Dict:
        traffic_cn = {"smooth": "畅通", "slow": "缓行", "congested": "拥堵"}.get(
            route.get("traffic_level", "smooth"), "畅通"
        )
        toll_str = "，含收费路段" if route.get("toll") else "，无收费路段"
        return {
            "response": (
                f"为您规划路线：\n"
                f"📍 终点：{route.get('to', '')}"
                f"{(' - ' + route.get('to_address', '')) if route.get('to_address') else ''}\n"
                f"📏 距离：约{route['distance_km']}公里\n"
                f"⏱ 预计用时：{route['duration_min']}分钟\n"
                f"🚦 路况：{traffic_cn}{toll_str}\n\n"
                f"是否开始导航？"
            )
        }

    def plan_route(self, params: Dict) -> Dict:
        destination = params.get("destination", "")
        if not destination:
            return {"response": "请问您要导航去哪里呢？", "needs_clarification": True}

        if self.amap:
            # Use real Amap API
            # 不限制城市搜索目的地，让高德自动匹配
            geocode_result = self.amap.geocode(destination)

            if geocode_result.get("status") != "1" or not geocode_result.get("geocodes"):
                # Geocode failed, use synthetic fallback
                route = self._make_synthetic_route(destination)
                self.current_route = route
                self.nav_state = "planning"
                self.pending_destinations = None
                return self._format_route_response(route)

            geocodes = geocode_result["geocodes"]
            city_in_name = self.city  # e.g., "北京"

            # 如果只有一个结果，也搜索POI检查是否有当前城市的替代选项
            if len(geocodes) == 1:
                # 搜索POI看看是否有当前城市的匹配
                poi_results = self.amap.search_poi(destination, city=self.city)
                if poi_results and len(poi_results) > 1:
                    # POI搜索返回多个结果，优先当前城市
                    city_pois = [p for p in poi_results if self.city and self.city in p.get("cityname", "")]
                    if city_pois:
                        # 有当前城市的结果，使用第一个
                        first_poi = city_pois[0]
                        location = first_poi.get("location", "")
                        if location:
                            geocodes = [{"location": location, "formatted_address": first_poi.get("name", destination)}]

            if len(geocodes) > 1:
                # Multiple matches: prioritize current city
                # Sort: current city first, others after
                def city_priority(g):
                    addr = g.get("formatted_address", "")
                    # 如果地址中包含当前城市，优先级高
                    if city_in_name and city_in_name in addr:
                        return 0
                    return 1

                geocodes_sorted = sorted(geocodes, key=city_priority)

                # 如果第一个结果就是当前城市的，直接使用
                first_addr = geocodes_sorted[0].get("formatted_address", "")
                if city_in_name and city_in_name in first_addr:
                    # 当前城市匹配，直接使用第一个
                    dest_location = geocodes_sorted[0]["location"]
                    self._dest_location = dest_location
                    geocodes = [geocodes_sorted[0]]
                else:
                    # 多个不同城市，需要用户选择
                    self.pending_destinations = [
                        {
                            "name": g.get("formatted_address", destination),
                            "address": g.get("formatted_address", ""),
                            "location": g["location"]
                        }
                        for g in geocodes_sorted[:5]
                    ]
                    self.nav_state = "planning"
                    options = "\n".join(
                        f"{i+1}. {m['name']}（{m.get('address', '')}）"
                        for i, m in enumerate(self.pending_destinations)
                    )
                    return {
                        "response": f"找到多个「{destination}」，请确认您要去哪一个：\n{options}",
                        "needs_clarification": True
                    }

            # Single match or city-prioritized match
            dest_location = geocodes[0]["location"]
            self._dest_location = dest_location

            origin = self._origin_location or "116.470,39.985"  # Default: 望京
            driving_result = self.amap.driving_direction(origin, dest_location)

            if driving_result.get("status") == "1":
                route = self.amap.format_route(driving_result, destination_name=destination)
                if route:
                    route["id"] = self._generate_route_id()
                else:
                    route = self._make_synthetic_route(destination)
            else:
                route = self._make_synthetic_route(destination)

            self.current_route = route
            self.nav_state = "planning"
            self.pending_destinations = None
            return self._format_route_response(route)
        else:
            # No AmapClient, use legacy local data + synthetic
            matches = self.data_manager.search_destination(destination)
            if len(matches) == 0:
                route = self._make_synthetic_route(destination)
            elif len(matches) == 1:
                dest = matches[0]
                route = self.data_manager.get_route(to_loc=dest.get("name", destination)) or self._make_synthetic_route(dest.get("name", destination))
                route["to"] = dest.get("name", destination)
                route["to_address"] = dest.get("address", "")
            else:
                self.pending_destinations = matches
                self.nav_state = "planning"
                options = "\n".join(
                    f"{i+1}. {m['name']}（{m.get('address', '')}）"
                    for i, m in enumerate(matches)
                )
                return {
                    "response": f"找到多个「{destination}」，请确认您要去哪一个：\n{options}",
                    "needs_clarification": True
                }

            self.current_route = route
            self.nav_state = "planning"
            self.pending_destinations = None
            return self._format_route_response(route)

    def select_destination(self, params: Dict) -> Dict:
        if not self.pending_destinations:
            return {"response": "当前没有待选择的目的地，请告诉我您要去哪里~"}

        selection = params.get("selection", 1)
        try:
            idx = int(selection) - 1
            if idx < 0 or idx >= len(self.pending_destinations):
                return {"response": f"请选择1-{len(self.pending_destinations)}之间的编号~"}
            dest = self.pending_destinations[idx]
        except (ValueError, TypeError):
            for d in self.pending_destinations:
                if str(selection) in d["name"]:
                    dest = d
                    break
            else:
                return {"response": f"请选择1-{len(self.pending_destinations)}之间的编号~"}

        self.pending_destinations = None

        if self.amap and dest.get("location"):
            origin = self._origin_location or "116.470,39.985"
            driving_result = self.amap.driving_direction(origin, dest["location"])
            if driving_result.get("status") == "1":
                route = self.amap.format_route(driving_result, destination_name=dest["name"])
                if route:
                    route["id"] = self._generate_route_id()
                else:
                    route = self._make_synthetic_route(dest["name"])
            else:
                route = self._make_synthetic_route(dest["name"])
        else:
            route = self.data_manager.get_route(to_loc=dest.get("name", "")) or self._make_synthetic_route(dest["name"])

        route["to"] = dest["name"]
        route["to_address"] = dest.get("address", "")

        self.current_route = route
        self.nav_state = "planning"
        return self._format_route_response(route)

    def confirm_navigation(self) -> Dict:
        if self.nav_state != "planning" or not self.current_route:
            return {"response": "当前没有待确认的路线哦~"}

        self.nav_state = "navigating"
        self.navigation_session = {
            "start_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "route": self.current_route,
            "eta_minutes": self.current_route["duration_min"],
            "progress": 0
        }

        return {
            "response": f"🚗 导航开始！目的地：{self.current_route.get('to', '')}，预计{self.current_route['duration_min']}分钟到达~",
            "start_simulation": True
        }

    def cancel_navigation(self) -> Dict:
        if self.nav_state == "idle":
            return {"response": "当前没有导航任务哦~"}
        self.nav_state = "idle"
        self.current_route = None
        self.navigation_session = None
        self.pending_destinations = None
        return {"response": "导航已取消，有需要随时告诉我~"}

    def add_waypoint(self, params: Dict) -> Dict:
        if self.nav_state not in ("planning", "navigating"):
            return {"response": "当前没有进行中的导航，无法添加途经点~"}
        waypoint = params.get("waypoint", "")
        if not waypoint:
            return {"response": "请问要添加哪里作为途经点呢？"}

        if self.amap and self._dest_location:
            # Geocode waypoint and replan with waypoints param
            wp_geocode = self.amap.geocode(waypoint)
            if wp_geocode.get("status") == "1" and wp_geocode.get("geocodes"):
                wp_location = wp_geocode["geocodes"][0]["location"]
                origin = self._origin_location or "116.470,39.985"
                result = self.amap.driving_direction(origin, self._dest_location, waypoints=wp_location)
                if result.get("status") == "1":
                    route = self.amap.format_route(result, destination_name=self.current_route.get("to", ""))
                    if route:
                        route["id"] = self._generate_route_id()
                        self.current_route = route
                        if self.navigation_session:
                            self.navigation_session["eta_minutes"] = route["duration_min"]
                        return {
                            "response": (
                                f"已添加途经点「{waypoint}」，路线已更新：\n"
                                f"📏 新距离：约{route['distance_km']}公里\n"
                                f"⏱ 预计用时：{route['duration_min']}分钟\n"
                                f"继续导航中..."
                            )
                        }

        # Fallback: synthetic update
        extra_km = round(random.uniform(2, 8), 1)
        extra_min = int(extra_km * random.uniform(1.5, 2.5))
        self.current_route["distance_km"] = round(self.current_route["distance_km"] + extra_km, 1)
        self.current_route["duration_min"] += extra_min
        if self.navigation_session:
            self.navigation_session["eta_minutes"] = self.current_route["duration_min"]
        return {
            "response": (
                f"已添加途经点「{waypoint}」，路线已更新：\n"
                f"📏 新距离：约{self.current_route['distance_km']}公里\n"
                f"⏱ 预计用时：{self.current_route['duration_min']}分钟\n"
                f"继续导航中..."
            )
        }

    def search_poi(self, params: Dict) -> Dict:
        poi_type = params.get("poi_type", "")
        keyword = params.get("keyword", "")

        if not poi_type and not keyword:
            return {"response": "请问您想找什么类型的地点呢？比如加油站、餐厅、停车场等~"}

        search_kw = poi_type or keyword

        if self.amap:
            pois = self.amap.search_poi(search_kw, city=self.city)
            if not pois:
                return {"response": f"附近没有找到{search_kw}，换个关键词试试~"}

            type_cn_map = {
                "gas_station": "加油站", "restaurant": "餐厅", "parking": "停车场",
                "charging_station": "充电站", "hospital": "医院", "bank": "银行",
                "supermarket": "超市", "shopping": "商场"
            }
            type_cn = type_cn_map.get(poi_type, poi_type if poi_type else keyword)
            response = f"附近{type_cn}：\n"
            for i, poi in enumerate(pois[:5], 1):
                rating_str = f" 评分{poi['rating']}" if poi.get("rating") else ""
                response += f"{i}. {poi['name']} - {poi.get('address', '')}{rating_str}\n"
            return {"response": response.strip()}

        # Legacy fallback
        if poi_type:
            pois = self.data_manager.get_pois_by_type(poi_type, limit=5)
        else:
            pois = self.data_manager.search_pois_by_name(keyword)[:5]

        if not pois:
            type_cn = poi_type if poi_type else keyword
            return {"response": f"附近没有找到{type_cn}，换个关键词试试~"}

        type_cn_map = {
            "gas_station": "加油站", "restaurant": "餐厅", "parking": "停车场",
            "charging_station": "充电站", "hospital": "医院", "bank": "银行",
            "supermarket": "超市", "shopping": "商场"
        }
        type_cn = type_cn_map.get(poi_type, poi_type)

        response = f"附近{type_cn}：\n"
        for i, poi in enumerate(pois, 1):
            rating_str = f" 评分{poi['rating']}" if poi.get("rating") else ""
            response += f"{i}. {poi['name']} - {poi['address']}{rating_str}\n"
        return {"response": response.strip()}

    def search_along_route(self, params: Dict) -> Dict:
        if self.nav_state != "navigating":
            return {"response": "当前没有进行中的导航，您可以使用「搜索附近」查找地点~"}

        poi_type = params.get("poi_type", "")
        if not poi_type:
            return {"response": "请问沿途想找什么类型的地点呢？比如加油站、餐厅等~"}

        if self.amap and self._origin_location and self._dest_location:
            pois = self.amap.search_along_route(poi_type, self._origin_location, self._dest_location)
        else:
            pois = self.data_manager.get_pois_by_type(poi_type, limit=5)

        if not pois:
            type_cn_map = {"gas_station": "加油站", "restaurant": "餐厅", "parking": "停车场",
                           "charging_station": "充电站", "hospital": "医院"}
            return {"response": f"沿途没有找到{type_cn_map.get(poi_type, poi_type)}~"}

        type_cn_map = {"gas_station": "加油站", "restaurant": "餐厅", "parking": "停车场",
                        "charging_station": "充电站"}
        type_cn = type_cn_map.get(poi_type, poi_type)

        response = f"沿途{type_cn}：\n"
        for i, poi in enumerate(pois[:5], 1):
            dist = poi.get("distance", round(random.uniform(0.3, 3.0), 1))
            response += f"{i}. {poi['name']} - 距路线{dist}公里\n"
        return {"response": response.strip()}

    def get_traffic_info(self, params: Dict) -> Dict:
        if self.nav_state == "navigating" and self.current_route:
            traffic_cn = {"smooth": "畅通", "slow": "缓行", "congested": "拥堵"}.get(
                self.current_route.get("traffic_level", "smooth"), "畅通"
            )
            road = self.current_route.get("to", "")
            return {"response": f"当前前往{road}的路况：{traffic_cn}"}

        road_name = params.get("road_name", "")
        if road_name:
            if self.amap:
                result = self.amap.traffic_info(city=self.city, road_name=road_name)
                if result.get("status") == "1" and result.get("trafficinfo"):
                    evaluation = result["trafficinfo"].get("evaluation", {})
                    expedite = evaluation.get("expedite", "未知")
                    return {"response": f"{road_name}当前路况：畅通率{expedite}"}
            traffic = random.choice(["畅通", "缓行", "拥堵"])
            return {"response": f"{road_name}当前路况：{traffic}"}

        return {"response": "请告诉我您想查询哪条路的路况？"}

    def avoid_route(self, params: Dict) -> Dict:
        if self.nav_state != "navigating" or not self.current_route:
            return {"response": "当前没有进行中的导航~"}

        avoid_type = params.get("avoid_type", "")
        avoid_cn_map = {"toll": "收费路段", "congestion": "拥堵路段", "highway": "高速公路"}
        avoid_cn = avoid_cn_map.get(avoid_type, avoid_type)

        # TODO: Use AmapClient avoid parameters when API supports strategy param
        extra_km = round(random.uniform(1, 5), 1)
        extra_min = int(extra_km * 2)
        self.current_route["distance_km"] = round(self.current_route["distance_km"] + extra_km, 1)
        self.current_route["duration_min"] += extra_min
        if avoid_type == "toll":
            self.current_route["toll"] = False

        if self.navigation_session:
            self.navigation_session["eta_minutes"] = self.current_route["duration_min"]

        return {
            "response": (
                f"已为您避开{avoid_cn}，路线已更新：\n"
                f"📏 新距离：约{self.current_route['distance_km']}公里\n"
                f"⏱ 预计用时：{self.current_route['duration_min']}分钟\n"
                f"继续导航中..."
            )
        }

    def query_eta(self) -> Dict:
        if self.nav_state != "navigating" or not self.navigation_session:
            return {"response": "当前没有进行中的导航~"}
        eta = self.navigation_session["eta_minutes"]
        dest = self.current_route.get("to", "目的地")
        traffic_cn = {"smooth": "畅通", "slow": "缓行", "congested": "拥堵"}.get(
            self.current_route.get("traffic_level", "smooth"), "畅通"
        )
        return {"response": f"预计还需{eta}分钟到达{dest}，当前路况{traffic_cn}"}

    def get_vehicle_status(self) -> Dict:
        status = self.data_manager.get_vehicle_status()
        vehicle_type = status.get("vehicle_type", "fuel")
        if vehicle_type == "fuel":
            level = status.get("fuel_level", 0)
            range_km = status.get("fuel_range_km", 0)
            response = f"当前油量：{level}%，预计续航{range_km}公里"
            if level < 30:
                response += "\n⚠️ 油量较低，建议尽快加油"
        else:
            level = status.get("battery_level", 0)
            range_km = status.get("battery_range_km", 0)
            response = f"当前电量：{level}%，预计续航{range_km}公里"
            if level < 20:
                response += "\n⚠️ 电量较低，建议尽快充电"
        return {"response": response}

    def navigate_home(self) -> Dict:
        home = self.data_manager.get_home()
        if not home:
            return {"response": "您还没有设置家的地址哦，请先设置~"}

        loc = home.get("location", {})
        if self.amap and loc:
            loc_str = f"{loc.get('lng', '')},{loc.get('lat', '')}"
            self._dest_location = loc_str
            origin = self._origin_location or "116.470,39.985"
            driving_result = self.amap.driving_direction(origin, loc_str)
            if driving_result.get("status") == "1":
                route = self.amap.format_route(driving_result, destination_name=home["name"])
                if route:
                    route["id"] = self._generate_route_id()
                    route["to_address"] = home.get("address", "")
                    self.current_route = route
                    self.nav_state = "planning"
                    return self._format_route_response(route)

        route = self.data_manager.get_route(to_loc=home.get("address", home["name"])) or self._make_synthetic_route(home["name"])
        route["to"] = home["name"]
        route["to_address"] = home.get("address", "")
        self.current_route = route
        self.nav_state = "planning"
        return self._format_route_response(route)

    def navigate_company(self) -> Dict:
        company = self.data_manager.get_company()
        if not company:
            return {"response": "您还没有设置公司的地址哦，请先设置~"}

        loc = company.get("location", {})
        if self.amap and loc:
            loc_str = f"{loc.get('lng', '')},{loc.get('lat', '')}"
            self._dest_location = loc_str
            origin = self._origin_location or "116.470,39.985"
            driving_result = self.amap.driving_direction(origin, loc_str)
            if driving_result.get("status") == "1":
                route = self.amap.format_route(driving_direction_result=driving_result, destination_name=company["name"])
                if route:
                    route["id"] = self._generate_route_id()
                    route["to_address"] = company.get("address", "")
                    self.current_route = route
                    self.nav_state = "planning"
                    return self._format_route_response(route)

        route = self.data_manager.get_route(to_loc=company.get("address", company["name"])) or self._make_synthetic_route(company["name"])
        route["to"] = company["name"]
        route["to_address"] = company.get("address", "")
        self.current_route = route
        self.nav_state = "planning"
        return self._format_route_response(route)

    def navigate_favorite(self, params: Dict) -> Dict:
        name = params.get("favorite_name", "")
        if not name:
            return {"response": "请问您想去哪个收藏地点呢？"}
        fav = self.data_manager.get_favorite_by_name(name)
        if not fav:
            return {"response": f"没有找到「{name}」的收藏地点哦~"}
        return self.plan_route({"destination": fav["name"]})
