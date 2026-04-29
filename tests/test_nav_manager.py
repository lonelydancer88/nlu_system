"""Tests for NavigationManager - navigation business logic."""
import json
import os
import pytest
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modules.nav_manager import NavigationManager
from modules.nav_data_manager import NavigationDataManager


@pytest.fixture
def tmp_data_dir(tmp_path):
    pois = {
        "pois": [
            {"id": "POI001", "name": "中石化望京加油站", "type": "gas_station", "address": "朝阳区望京西路8号", "location": {"lat": 39.987, "lng": 116.474}, "rating": 4.2},
            {"id": "POI002", "name": "中石油北五环加油站", "type": "gas_station", "address": "海淀区北五环中路12号", "location": {"lat": 40.010, "lng": 116.380}, "rating": 4.0},
            {"id": "POI003", "name": "海底捞望京店", "type": "restaurant", "address": "朝阳区望京SOHO T1", "location": {"lat": 39.991, "lng": 116.478}, "rating": 4.5},
            {"id": "POI004", "name": "万达广场(CBD店)", "type": "shopping", "address": "朝阳区建国路93号", "location": {"lat": 39.908, "lng": 116.470}, "rating": 4.4},
            {"id": "POI005", "name": "万达广场(通州店)", "type": "shopping", "address": "通州区新华西街58号", "location": {"lat": 39.907, "lng": 116.660}, "rating": 4.2},
        ]
    }
    with open(tmp_path / "nav_pois.json", "w", encoding="utf-8") as f:
        json.dump(pois, f, ensure_ascii=False)

    favorites = {
        "home": {"name": "家", "address": "朝阳区望京西园四区", "location": {"lat": 39.985, "lng": 116.470}},
        "company": {"name": "公司", "address": "海淀区中关村软件园二期", "location": {"lat": 40.052, "lng": 116.302}},
        "favorites": [
            {"name": "健身房", "address": "朝阳区望京健身中心", "location": {"lat": 39.988, "lng": 116.475}},
        ]
    }
    with open(tmp_path / "nav_favorites.json", "w", encoding="utf-8") as f:
        json.dump(favorites, f, ensure_ascii=False)

    vehicle = {"vehicle_type": "fuel", "fuel_level": 65, "fuel_range_km": 480}
    with open(tmp_path / "nav_vehicle_status.json", "w", encoding="utf-8") as f:
        json.dump(vehicle, f, ensure_ascii=False)

    routes = {
        "routes": [
            {"id": "R001", "from": "当前位置", "to": "万达广场(CBD店)", "distance_km": 12.5, "duration_min": 25, "toll": True},
        ]
    }
    with open(tmp_path / "nav_routes.json", "w", encoding="utf-8") as f:
        json.dump(routes, f, ensure_ascii=False)

    return tmp_path


@pytest.fixture
def nav_manager(tmp_data_dir, monkeypatch):
    import modules.nav_data_manager as ndm
    monkeypatch.setattr(ndm, "DATA_DIR", str(tmp_data_dir))
    mgr = NavigationManager()
    mgr.data_manager.pois_path = str(tmp_data_dir / "nav_pois.json")
    mgr.data_manager.favorites_path = str(tmp_data_dir / "nav_favorites.json")
    mgr.data_manager.vehicle_status_path = str(tmp_data_dir / "nav_vehicle_status.json")
    mgr.data_manager.routes_path = str(tmp_data_dir / "nav_routes.json")
    return mgr


class TestPlanRoute:
    def test_plan_route_known_destination(self, nav_manager):
        result = nav_manager.plan_route({"destination": "万达广场(CBD店)"})
        assert "response" in result
        assert "公里" in result["response"]
        assert "分钟" in result["response"]
        assert nav_manager.nav_state == "planning"
        assert nav_manager.current_route is not None

    def test_plan_route_unknown_destination(self, nav_manager):
        result = nav_manager.plan_route({"destination": "某个不存在的地名"})
        assert "response" in result
        # Should generate synthetic route
        assert "公里" in result["response"]
        assert nav_manager.nav_state == "planning"

    def test_plan_route_no_destination(self, nav_manager):
        result = nav_manager.plan_route({})
        assert result.get("needs_clarification") is True
        assert "哪里" in result["response"]

    def test_plan_route_ambiguous_destination(self, nav_manager):
        result = nav_manager.plan_route({"destination": "万达广场"})
        # Multiple matches → needs_clarification
        assert result.get("needs_clarification") is True
        assert nav_manager.pending_destinations is not None
        assert len(nav_manager.pending_destinations) == 2


class TestSelectDestination:
    def test_select_destination_by_number(self, nav_manager):
        # First create ambiguity
        nav_manager.plan_route({"destination": "万达广场"})
        result = nav_manager.select_destination({"selection": 1})
        assert "response" in result
        assert nav_manager.nav_state == "planning"
        assert nav_manager.pending_destinations is None

    def test_select_destination_no_pending(self, nav_manager):
        result = nav_manager.select_destination({"selection": 1})
        assert "没有" in result["response"]

    def test_select_destination_out_of_range(self, nav_manager):
        nav_manager.plan_route({"destination": "万达广场"})
        result = nav_manager.select_destination({"selection": 99})
        assert "选择" in result["response"]


class TestConfirmNavigation:
    def test_confirm_navigation(self, nav_manager):
        nav_manager.plan_route({"destination": "万达广场(CBD店)"})
        result = nav_manager.confirm_navigation()
        assert nav_manager.nav_state == "navigating"
        assert result.get("start_simulation") is True
        assert "导航开始" in result["response"]

    def test_confirm_without_planning(self, nav_manager):
        result = nav_manager.confirm_navigation()
        assert "没有" in result["response"]

    def test_confirm_while_navigating(self, nav_manager):
        nav_manager.plan_route({"destination": "万达广场(CBD店)"})
        nav_manager.confirm_navigation()
        result = nav_manager.confirm_navigation()
        # nav_state is "navigating" not "planning"
        assert "没有" in result["response"]


class TestCancelNavigation:
    def test_cancel_while_planning(self, nav_manager):
        nav_manager.plan_route({"destination": "万达广场(CBD店)"})
        result = nav_manager.cancel_navigation()
        assert nav_manager.nav_state == "idle"
        assert "取消" in result["response"]

    def test_cancel_while_navigating(self, nav_manager):
        nav_manager.plan_route({"destination": "万达广场(CBD店)"})
        nav_manager.confirm_navigation()
        result = nav_manager.cancel_navigation()
        assert nav_manager.nav_state == "idle"

    def test_cancel_while_idle(self, nav_manager):
        result = nav_manager.cancel_navigation()
        assert "没有" in result["response"]


class TestAddWaypoint:
    def test_add_waypoint_while_navigating(self, nav_manager):
        nav_manager.plan_route({"destination": "万达广场(CBD店)"})
        nav_manager.confirm_navigation()
        old_dist = nav_manager.current_route["distance_km"]
        old_dur = nav_manager.current_route["duration_min"]
        result = nav_manager.add_waypoint({"waypoint": "加油站"})
        assert "途经点" in result["response"]
        assert nav_manager.current_route["distance_km"] > old_dist
        assert nav_manager.current_route["duration_min"] > old_dur

    def test_add_waypoint_not_navigating(self, nav_manager):
        result = nav_manager.add_waypoint({"waypoint": "加油站"})
        assert "没有" in result["response"]

    def test_add_waypoint_empty(self, nav_manager):
        nav_manager.plan_route({"destination": "万达广场(CBD店)"})
        nav_manager.confirm_navigation()
        result = nav_manager.add_waypoint({})
        assert "哪里" in result["response"]


class TestSearchPOI:
    def test_search_by_type(self, nav_manager):
        result = nav_manager.search_poi({"poi_type": "gas_station"})
        assert "加油站" in result["response"]
        assert "中石化" in result["response"]

    def test_search_by_keyword(self, nav_manager):
        result = nav_manager.search_poi({"keyword": "海底捞"})
        assert "海底捞" in result["response"]

    def test_search_no_params(self, nav_manager):
        result = nav_manager.search_poi({})
        assert "什么类型" in result["response"]

    def test_search_no_results(self, nav_manager):
        result = nav_manager.search_poi({"poi_type": "hospital"})
        assert "没有" in result["response"]


class TestSearchAlongRoute:
    def test_search_along_route(self, nav_manager):
        nav_manager.plan_route({"destination": "万达广场(CBD店)"})
        nav_manager.confirm_navigation()
        result = nav_manager.search_along_route({"poi_type": "gas_station"})
        assert "沿途" in result["response"]

    def test_search_along_route_not_navigating(self, nav_manager):
        result = nav_manager.search_along_route({"poi_type": "gas_station"})
        assert "没有" in result["response"]


class TestTrafficInfo:
    def test_traffic_while_navigating(self, nav_manager):
        nav_manager.plan_route({"destination": "万达广场(CBD店)"})
        nav_manager.confirm_navigation()
        result = nav_manager.get_traffic_info({})
        assert "路况" in result["response"]

    def test_traffic_by_road_name(self, nav_manager):
        result = nav_manager.get_traffic_info({"road_name": "北五环"})
        assert "北五环" in result["response"]
        assert "路况" in result["response"]

    def test_traffic_no_params_idle(self, nav_manager):
        result = nav_manager.get_traffic_info({})
        assert "哪条路" in result["response"]


class TestAvoidRoute:
    def test_avoid_toll(self, nav_manager):
        nav_manager.plan_route({"destination": "万达广场(CBD店)"})
        nav_manager.confirm_navigation()
        result = nav_manager.avoid_route({"avoid_type": "toll"})
        assert "避开" in result["response"]
        assert "收费" in result["response"]

    def test_avoid_not_navigating(self, nav_manager):
        result = nav_manager.avoid_route({"avoid_type": "toll"})
        assert "没有" in result["response"]


class TestQueryETA:
    def test_query_eta_while_navigating(self, nav_manager):
        nav_manager.plan_route({"destination": "万达广场(CBD店)"})
        nav_manager.confirm_navigation()
        result = nav_manager.query_eta()
        assert "分钟" in result["response"]

    def test_query_eta_not_navigating(self, nav_manager):
        result = nav_manager.query_eta()
        assert "没有" in result["response"]


class TestVehicleStatus:
    def test_vehicle_status_fuel(self, nav_manager):
        result = nav_manager.get_vehicle_status()
        assert "油量" in result["response"]
        assert "65%" in result["response"]

    def test_vehicle_status_low_fuel(self, tmp_data_dir, monkeypatch):
        import modules.nav_data_manager as ndm
        monkeypatch.setattr(ndm, "DATA_DIR", str(tmp_data_dir))
        vehicle = {"vehicle_type": "fuel", "fuel_level": 15, "fuel_range_km": 80}
        with open(tmp_data_dir / "nav_vehicle_status.json", "w", encoding="utf-8") as f:
            json.dump(vehicle, f, ensure_ascii=False)

        mgr = NavigationManager()
        mgr.data_manager.vehicle_status_path = str(tmp_data_dir / "nav_vehicle_status.json")
        result = mgr.get_vehicle_status()
        assert "油量较低" in result["response"]

    def test_vehicle_status_electric(self, tmp_data_dir, monkeypatch):
        import modules.nav_data_manager as ndm
        monkeypatch.setattr(ndm, "DATA_DIR", str(tmp_data_dir))
        vehicle = {"vehicle_type": "electric", "battery_level": 80, "battery_range_km": 300}
        with open(tmp_data_dir / "nav_vehicle_status.json", "w", encoding="utf-8") as f:
            json.dump(vehicle, f, ensure_ascii=False)

        mgr = NavigationManager()
        mgr.data_manager.vehicle_status_path = str(tmp_data_dir / "nav_vehicle_status.json")
        result = mgr.get_vehicle_status()
        assert "电量" in result["response"]


class TestNavigateHomeCompany:
    def test_navigate_home(self, nav_manager):
        result = nav_manager.navigate_home()
        assert "家" in result["response"]
        assert nav_manager.nav_state == "planning"

    def test_navigate_company(self, nav_manager):
        result = nav_manager.navigate_company()
        assert "公司" in result["response"]
        assert nav_manager.nav_state == "planning"


class TestNavigateFavorite:
    def test_navigate_favorite(self, nav_manager):
        result = nav_manager.navigate_favorite({"favorite_name": "健身房"})
        assert "response" in result

    def test_navigate_favorite_not_found(self, nav_manager):
        result = nav_manager.navigate_favorite({"favorite_name": "火星基地"})
        assert "没有找到" in result["response"]

    def test_navigate_favorite_no_name(self, nav_manager):
        result = nav_manager.navigate_favorite({})
        assert "哪个" in result["response"]


class TestFullFlow:
    def test_plan_confirm_cancel(self, nav_manager):
        # Plan
        result = nav_manager.plan_route({"destination": "万达广场(CBD店)"})
        assert nav_manager.nav_state == "planning"

        # Confirm
        result = nav_manager.confirm_navigation()
        assert nav_manager.nav_state == "navigating"

        # Cancel
        result = nav_manager.cancel_navigation()
        assert nav_manager.nav_state == "idle"

    def test_plan_confirm_navigate_cancel(self, nav_manager):
        nav_manager.plan_route({"destination": "万达广场(CBD店)"})
        nav_manager.confirm_navigation()

        # Add waypoint during navigation
        nav_manager.add_waypoint({"waypoint": "加油站"})

        # Query ETA
        eta = nav_manager.query_eta()
        assert "分钟" in eta["response"]

        # Cancel
        nav_manager.cancel_navigation()
        assert nav_manager.nav_state == "idle"
