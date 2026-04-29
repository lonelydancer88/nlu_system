"""Tests for rewritten NavManager - using AmapClient for real API data."""
import json
import os
import pytest
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modules.nav_manager import NavigationManager
from modules.amap_client import AmapClient


@pytest.fixture
def mock_amap():
    """Create a mocked AmapClient."""
    return MagicMock(spec=AmapClient)


@pytest.fixture
def tmp_data_dir(tmp_path, monkeypatch):
    """Set up temp nav data files."""
    import modules.nav_data_manager as ndm
    monkeypatch.setattr(ndm, "DATA_DIR", str(tmp_path))

    favorites = {
        "home": {"name": "家", "address": "朝阳区望京西园四区", "location": {"lat": 39.985, "lng": 116.470}},
        "company": {"name": "公司", "address": "海淀区中关村软件园二期", "location": {"lat": 40.052, "lng": 116.302}},
        "favorites": [
            {"name": "健身房", "address": "朝阳区望京健身中心", "location": {"lat": 39.988, "lng": 116.475}}
        ]
    }
    with open(tmp_path / "nav_favorites.json", "w", encoding="utf-8") as f:
        json.dump(favorites, f, ensure_ascii=False)

    vehicle = {"vehicle_type": "fuel", "fuel_level": 65, "fuel_range_km": 480}
    with open(tmp_path / "nav_vehicle_status.json", "w", encoding="utf-8") as f:
        json.dump(vehicle, f, ensure_ascii=False)

    with open(tmp_path / "nav_pois.json", "w", encoding="utf-8") as f:
        json.dump({"pois": []}, f, ensure_ascii=False)
    with open(tmp_path / "nav_routes.json", "w", encoding="utf-8") as f:
        json.dump({"routes": []}, f, ensure_ascii=False)

    return tmp_path


@pytest.fixture
def nav_manager(mock_amap, tmp_data_dir):
    """Create NavManager with mocked AmapClient."""
    mgr = NavigationManager(amap_client=mock_amap)
    mgr.data_manager.favorites_path = str(tmp_data_dir / "nav_favorites.json")
    mgr.data_manager.vehicle_status_path = str(tmp_data_dir / "nav_vehicle_status.json")
    mgr.data_manager.pois_path = str(tmp_data_dir / "nav_pois.json")
    mgr.data_manager.routes_path = str(tmp_data_dir / "nav_routes.json")
    return mgr


class TestPlanRouteWithAmap:
    def test_plan_route_calls_geocode(self, nav_manager, mock_amap):
        mock_amap.geocode.return_value = {
            "status": "1",
            "geocodes": [{"formatted_address": "北京市海淀区中关村", "location": "116.310,40.048"}]
        }
        mock_amap.driving_direction.return_value = {
            "status": "1",
            "route": {"paths": [{"distance": "12500", "duration": "1500", "steps": [], "tolls": "5"}]}
        }
        nav_manager.plan_route({"destination": "中关村"})
        mock_amap.geocode.assert_called_once()

    def test_plan_route_calls_driving_direction(self, nav_manager, mock_amap):
        mock_amap.geocode.return_value = {
            "status": "1",
            "geocodes": [{"location": "116.310,40.048"}]
        }
        mock_amap.driving_direction.return_value = {
            "status": "1",
            "route": {"paths": [{"distance": "12500", "duration": "1500", "steps": [], "tolls": "5"}]}
        }
        nav_manager.plan_route({"destination": "中关村"})
        mock_amap.driving_direction.assert_called_once()
        # Origin should be "当前位置" placeholder or user location
        call_args = mock_amap.driving_direction.call_args
        assert call_args[0][1] == "116.310,40.048"  # destination

    def test_plan_route_returns_formatted_route(self, nav_manager, mock_amap):
        mock_amap.geocode.return_value = {
            "status": "1",
            "geocodes": [{"location": "116.310,40.048"}]
        }
        mock_amap.format_route.return_value = {
            "distance_km": 12.5, "duration_min": 25, "toll": True,
            "to": "中关村", "steps": [], "traffic_level": "smooth", "traffic_level_cn": "畅通"
        }
        mock_amap.driving_direction.return_value = {"status": "1", "route": {"paths": []}}
        result = nav_manager.plan_route({"destination": "中关村"})
        assert "公里" in result["response"]
        assert nav_manager.nav_state == "planning"

    def test_plan_route_no_destination(self, nav_manager):
        result = nav_manager.plan_route({})
        assert result.get("needs_clarification") is True

    def test_plan_route_geocode_fails_fallback(self, nav_manager, mock_amap):
        mock_amap.geocode.return_value = {"status": "0", "geocodes": []}
        # Should still try to plan with synthetic route as fallback
        result = nav_manager.plan_route({"destination": "未知地点"})
        assert "response" in result

    def test_plan_route_multiple_geocodes_needs_selection(self, nav_manager, mock_amap):
        mock_amap.geocode.return_value = {
            "status": "1",
            "geocodes": [
                {"formatted_address": "中关村软件园", "location": "116.310,40.048"},
                {"formatted_address": "中关村大街", "location": "116.320,40.050"}
            ]
        }
        result = nav_manager.plan_route({"destination": "中关村"})
        assert result.get("needs_clarification") is True
        assert nav_manager.pending_destinations is not None


class TestNavigateHomeWithAmap:
    def test_navigate_home_uses_favorite_coords(self, nav_manager, mock_amap):
        mock_amap.driving_direction.return_value = {"status": "1", "route": {"paths": []}}
        mock_amap.format_route.return_value = {
            "distance_km": 5.0, "duration_min": 15, "toll": False,
            "to": "家", "steps": [], "traffic_level": "smooth", "traffic_level_cn": "畅通"
        }
        result = nav_manager.navigate_home()
        # Should use home coordinates directly, not geocode
        mock_amap.geocode.assert_not_called()
        mock_amap.driving_direction.assert_called_once()

    def test_navigate_home_no_home_set(self, tmp_data_dir, mock_amap, monkeypatch):
        import modules.nav_data_manager as ndm
        monkeypatch.setattr(ndm, "DATA_DIR", str(tmp_data_dir))
        with open(tmp_data_dir / "nav_favorites.json", "w", encoding="utf-8") as f:
            json.dump({"company": {"name": "公司"}}, f, ensure_ascii=False)

        mgr = NavigationManager(amap_client=mock_amap)
        mgr.data_manager.favorites_path = str(tmp_data_dir / "nav_favorites.json")
        result = mgr.navigate_home()
        assert "没有设置" in result["response"]


class TestNavigateCompanyWithAmap:
    def test_navigate_company_uses_favorite_coords(self, nav_manager, mock_amap):
        mock_amap.driving_direction.return_value = {"status": "1", "route": {"paths": []}}
        mock_amap.format_route.return_value = {
            "distance_km": 15.0, "duration_min": 30, "toll": True,
            "to": "公司", "steps": [], "traffic_level": "smooth", "traffic_level_cn": "畅通"
        }
        result = nav_manager.navigate_company()
        mock_amap.geocode.assert_not_called()
        mock_amap.driving_direction.assert_called_once()


class TestSearchPOIWithAmap:
    def test_search_poi_calls_amap(self, nav_manager, mock_amap):
        mock_amap.search_poi.return_value = [
            {"name": "中石化望京加油站", "address": "望京西路8号", "distance": "500"}
        ]
        result = nav_manager.search_poi({"poi_type": "加油站"})
        mock_amap.search_poi.assert_called_once()
        assert "加油站" in result["response"]

    def test_search_poi_no_results(self, nav_manager, mock_amap):
        mock_amap.search_poi.return_value = []
        result = nav_manager.search_poi({"poi_type": "医院"})
        assert "没有" in result["response"]


class TestSearchAlongRouteWithAmap:
    def test_search_along_route_calls_amap(self, nav_manager, mock_amap):
        nav_manager.nav_state = "navigating"
        nav_manager.current_route = {"to": "目的地"}
        nav_manager.navigation_session = {"eta_minutes": 25}
        nav_manager._origin_location = "116.470,39.985"
        nav_manager._dest_location = "116.310,40.048"

        mock_amap.search_along_route.return_value = [
            {"name": "沿途加油站", "distance": "800"}
        ]
        result = nav_manager.search_along_route({"poi_type": "加油站"})
        mock_amap.search_along_route.assert_called_once()

    def test_search_along_route_not_navigating(self, nav_manager):
        result = nav_manager.search_along_route({"poi_type": "加油站"})
        assert "没有" in result["response"]


class TestTrafficInfoWithAmap:
    def test_traffic_info_calls_amap(self, nav_manager, mock_amap):
        mock_amap.traffic_info.return_value = {
            "status": "1",
            "trafficinfo": {"evaluation": {"expedite": "80%", "congested": "10%"}}
        }
        result = nav_manager.get_traffic_info({"road_name": "北五环"})
        mock_amap.traffic_info.assert_called_once()


class TestQueryETA:
    def test_query_eta_while_navigating(self, nav_manager):
        nav_manager.nav_state = "navigating"
        nav_manager.current_route = {"duration_min": 25, "to": "中关村", "traffic_level": "smooth"}
        nav_manager.navigation_session = {"eta_minutes": 25}
        result = nav_manager.query_eta()
        assert "分钟" in result["response"]


class TestVehicleStatus:
    def test_vehicle_status(self, nav_manager):
        result = nav_manager.get_vehicle_status()
        assert "油量" in result["response"]
        assert "65%" in result["response"]
