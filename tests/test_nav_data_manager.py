"""Tests for NavigationDataManager - navigation data persistence layer."""
import json
import os
import pytest
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modules.nav_data_manager import NavigationDataManager


@pytest.fixture
def tmp_data_dir(tmp_path):
    pois = {
        "pois": [
            {"id": "POI001", "name": "中石化望京加油站", "type": "gas_station", "address": "朝阳区望京西路8号", "location": {"lat": 39.987, "lng": 116.474}, "rating": 4.2},
            {"id": "POI002", "name": "海底捞望京店", "type": "restaurant", "address": "朝阳区望京SOHO T1", "location": {"lat": 39.991, "lng": 116.478}, "rating": 4.5},
            {"id": "POI003", "name": "望京SOHO停车场", "type": "parking", "address": "朝阳区望京SOHO地下停车场", "location": {"lat": 39.992, "lng": 116.477}, "rating": 4.1},
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
            {"id": "R002", "from": "当前位置", "to": "家", "distance_km": 5.0, "duration_min": 15, "toll": False, "avoid_toll": True},
        ]
    }
    with open(tmp_path / "nav_routes.json", "w", encoding="utf-8") as f:
        json.dump(routes, f, ensure_ascii=False)

    return tmp_path


@pytest.fixture
def nav_data_manager(tmp_data_dir, monkeypatch):
    import modules.nav_data_manager as ndm
    monkeypatch.setattr(ndm, "DATA_DIR", str(tmp_data_dir))
    mgr = NavigationDataManager()
    mgr.pois_path = str(tmp_data_dir / "nav_pois.json")
    mgr.favorites_path = str(tmp_data_dir / "nav_favorites.json")
    mgr.vehicle_status_path = str(tmp_data_dir / "nav_vehicle_status.json")
    mgr.routes_path = str(tmp_data_dir / "nav_routes.json")
    return mgr


class TestPOI:
    def test_get_all_pois(self, nav_data_manager):
        pois = nav_data_manager.get_all_pois()
        assert len(pois) == 5

    def test_get_pois_by_type_english(self, nav_data_manager):
        pois = nav_data_manager.get_pois_by_type("gas_station")
        assert len(pois) == 1
        assert pois[0]["type"] == "gas_station"

    def test_get_pois_by_type_chinese(self, nav_data_manager):
        pois = nav_data_manager.get_pois_by_type("加油站")
        assert len(pois) == 1
        assert pois[0]["type"] == "gas_station"

    def test_get_pois_by_type_with_limit(self, nav_data_manager):
        pois = nav_data_manager.get_pois_by_type("shopping", limit=1)
        assert len(pois) == 1

    def test_search_pois_by_name(self, nav_data_manager):
        pois = nav_data_manager.search_pois_by_name("万达")
        assert len(pois) == 2

    def test_get_pois_by_type_empty(self, nav_data_manager):
        pois = nav_data_manager.get_pois_by_type("hospital")
        assert pois == []


class TestFavorites:
    def test_get_home(self, nav_data_manager):
        home = nav_data_manager.get_home()
        assert home is not None
        assert home["name"] == "家"

    def test_get_company(self, nav_data_manager):
        company = nav_data_manager.get_company()
        assert company is not None
        assert company["name"] == "公司"

    def test_get_favorites(self, nav_data_manager):
        favs = nav_data_manager.get_favorites()
        assert len(favs) == 1
        assert favs[0]["name"] == "健身房"

    def test_get_favorite_by_name(self, nav_data_manager):
        fav = nav_data_manager.get_favorite_by_name("健身房")
        assert fav is not None
        assert fav["name"] == "健身房"

    def test_get_favorite_by_name_partial(self, nav_data_manager):
        fav = nav_data_manager.get_favorite_by_name("健身")
        assert fav is not None

    def test_get_favorite_by_name_not_found(self, nav_data_manager):
        fav = nav_data_manager.get_favorite_by_name("不存在")
        assert fav is None

    def test_add_favorite(self, nav_data_manager):
        ok = nav_data_manager.add_favorite({"name": "超市", "address": "望京超市"})
        assert ok is True
        favs = nav_data_manager.get_favorites()
        assert len(favs) == 2


class TestVehicleStatus:
    def test_get_vehicle_status(self, nav_data_manager):
        status = nav_data_manager.get_vehicle_status()
        assert status["vehicle_type"] == "fuel"
        assert status["fuel_level"] == 65

    def test_update_vehicle_status(self, nav_data_manager):
        nav_data_manager.update_vehicle_status({"fuel_level": 30})
        status = nav_data_manager.get_vehicle_status()
        assert status["fuel_level"] == 30
        assert status["fuel_range_km"] == 480  # preserved


class TestRoutes:
    def test_get_all_routes(self, nav_data_manager):
        routes = nav_data_manager.get_all_routes()
        assert len(routes) == 2

    def test_get_route_by_destination(self, nav_data_manager):
        route = nav_data_manager.get_route(to_loc="万达广场(CBD店)")
        assert route is not None
        assert route["id"] == "R001"

    def test_get_route_avoid_toll(self, nav_data_manager):
        route = nav_data_manager.get_route(to_loc="家", avoid_toll=True)
        assert route is not None
        assert route.get("avoid_toll") is True

    def test_get_route_not_found(self, nav_data_manager):
        route = nav_data_manager.get_route(to_loc="不存在", avoid_toll=True)
        assert route is None


class TestSearchDestination:
    def test_search_shopping_poi(self, nav_data_manager):
        results = nav_data_manager.search_destination("万达广场")
        # Both shopping POIs match
        assert len(results) == 2
        assert all(r["type"] == "poi" for r in results)

    def test_search_non_shopping_poi_exact_match(self, nav_data_manager):
        results = nav_data_manager.search_destination("中石化望京加油站")
        assert len(results) == 1
        assert results[0]["type"] == "poi"

    def test_search_non_shopping_poi_prefix_no_match(self, nav_data_manager):
        # Non-shopping POI with prefix match should NOT appear
        results = nav_data_manager.search_destination("中石化")
        assert len(results) == 0

    def test_search_home(self, nav_data_manager):
        results = nav_data_manager.search_destination("家")
        assert len(results) >= 1
        assert any(r["type"] == "home" for r in results)

    def test_search_favorite(self, nav_data_manager):
        results = nav_data_manager.search_destination("健身房")
        assert len(results) >= 1
        assert any(r["type"] == "favorite" for r in results)

    def test_search_no_results(self, nav_data_manager):
        results = nav_data_manager.search_destination("火星")
        assert len(results) == 0
