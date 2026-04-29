"""Tests for AmapClient - Amap (Gaode) Web Services API wrapper."""
import json
import os
import pytest
import sys
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture
def amap():
    from modules.amap_client import AmapClient
    return AmapClient(api_key="test_amap_key")


class TestGeocode:
    def test_geocode_success(self, amap):
        mock_response = {
            "status": "1",
            "geocodes": [{"formatted_address": "北京市海淀区中关村", "location": "116.310,40.048"}]
        }
        with patch.object(amap, 'get', return_value=mock_response):
            result = amap.geocode("中关村")
            assert result["status"] == "1"
            assert len(result["geocodes"]) == 1
            assert result["geocodes"][0]["location"] == "116.310,40.048"

    def test_geocode_with_city(self, amap):
        with patch.object(amap, 'get', return_value={"status": "1", "geocodes": []}) as mock:
            amap.geocode("中关村", city="北京")
            mock.assert_called_once_with("/geocode/geo", {"address": "中关村", "city": "北京"})

    def test_reverse_geocode(self, amap):
        mock_response = {
            "status": "1",
            "regeocode": {"formatted_address": "北京市海淀区中关村大街"}
        }
        with patch.object(amap, 'get', return_value=mock_response):
            result = amap.reverse_geocode("116.310,40.048")
            assert result["status"] == "1"
            assert "中关村" in result["regeocode"]["formatted_address"]


class TestDrivingDirection:
    def test_driving_direction_success(self, amap):
        mock_response = {
            "status": "1",
            "route": {
                "paths": [{
                    "distance": "12500",
                    "duration": "1500",
                    "steps": [
                        {"instruction": "沿当前道路行驶", "distance": "1000"},
                        {"instruction": "左转进入中关村大街", "distance": "2000"}
                    ],
                    "tolls": "5"
                }]
            }
        }
        with patch.object(amap, 'get', return_value=mock_response):
            result = amap.driving_direction("116.470,39.985", "116.310,40.048")
            assert result["status"] == "1"
            paths = result["route"]["paths"]
            assert len(paths) == 1
            assert paths[0]["distance"] == "12500"

    def test_driving_direction_with_waypoints(self, amap):
        with patch.object(amap, 'get', return_value={"status": "1", "route": {"paths": []}}) as mock:
            amap.driving_direction("116.470,39.985", "116.310,40.048", waypoints="116.400,40.000")
            call_args = mock.call_args
            assert call_args[0][1]["waypoints"] == "116.400,40.000"

    def test_driving_direction_returns_formatted_route(self, amap):
        mock_response = {
            "status": "1",
            "route": {
                "paths": [{
                    "distance": "12500",
                    "duration": "1500",
                    "steps": [
                        {"instruction": "沿当前道路行驶", "distance": "1000"},
                    ],
                    "tolls": "5"
                }]
            }
        }
        with patch.object(amap, 'get', return_value=mock_response):
            result = amap.driving_direction("116.470,39.985", "116.310,40.048")
            route = amap.format_route(result, destination_name="中关村")
            assert route["distance_km"] == 12.5
            assert route["duration_min"] == 25
            assert route["toll"] is True
            assert route["to"] == "中关村"
            assert len(route["steps"]) == 1


class TestSearchPOI:
    def test_search_poi_by_keyword(self, amap):
        mock_response = {
            "status": "1",
            "pois": [
                {"name": "中石化望京加油站", "address": "朝阳区望京西路8号", "location": "116.474,39.987", "type": "加油站"},
                {"name": "中石油北五环加油站", "address": "海淀区北五环中路12号", "location": "116.380,40.010", "type": "加油站"}
            ]
        }
        with patch.object(amap, 'get', return_value=mock_response):
            result = amap.search_poi("加油站")
            assert len(result) == 2
            assert result[0]["name"] == "中石化望京加油站"

    def test_search_poi_with_city(self, amap):
        with patch.object(amap, 'get', return_value={"status": "1", "pois": []}) as mock:
            amap.search_poi("加油站", city="北京")
            mock.assert_called_once_with("/place/text", {"keywords": "加油站", "city": "北京"})

    def test_search_poi_with_location_and_radius(self, amap):
        with patch.object(amap, 'get', return_value={"status": "1", "pois": []}) as mock:
            amap.search_poi("加油站", location="116.470,39.985", radius=3000)
            call_args = mock.call_args[0][1]
            assert call_args["location"] == "116.470,39.985"
            assert call_args["radius"] == 3000


class TestSearchAlongRoute:
    def test_search_along_route(self, amap):
        mock_response = {
            "status": "1",
            "pois": [
                {"name": "沿途加油站1", "distance": "500"},
                {"name": "沿途加油站2", "distance": "2000"}
            ]
        }
        with patch.object(amap, 'get', return_value=mock_response) as mock:
            result = amap.search_along_route("加油站", "116.470,39.985", "116.310,40.048")
            assert len(result) == 2
            call_args = mock.call_args[0][1]
            assert call_args["keywords"] == "加油站"


class TestTrafficInfo:
    def test_traffic_info_by_city(self, amap):
        mock_response = {
            "status": "1",
            "trafficinfo": {"evaluation": {"expedite": "80%", "congested": "10%", "blocked": "5%"}}
        }
        with patch.object(amap, 'get', return_value=mock_response):
            result = amap.traffic_info(city="北京")
            assert result["status"] == "1"
            assert "trafficinfo" in result

    def test_traffic_info_by_road(self, amap):
        with patch.object(amap, 'get', return_value={"status": "1", "trafficinfo": {}}) as mock:
            amap.traffic_info(city="北京", road_name="北五环")
            call_args = mock.call_args[0][1]
            assert call_args["roadName"] == "北五环"


class TestFormatRoute:
    def test_format_route_basic(self, amap):
        api_response = {
            "status": "1",
            "route": {
                "paths": [{
                    "distance": "5000",
                    "duration": "600",
                    "steps": [
                        {"instruction": "沿道路行驶", "distance": "1000"},
                        {"instruction": "到达终点", "distance": "0"}
                    ],
                    "tolls": "0"
                }]
            }
        }
        route = amap.format_route(api_response, destination_name="三里屯")
        assert route["distance_km"] == 5.0
        assert route["duration_min"] == 10
        assert route["toll"] is False
        assert route["to"] == "三里屯"
        assert len(route["steps"]) == 2

    def test_format_route_multiple_paths(self, amap):
        api_response = {
            "status": "1",
            "route": {
                "paths": [
                    {"distance": "5000", "duration": "600", "steps": [], "tolls": "0"},
                    {"distance": "8000", "duration": "900", "steps": [], "tolls": "10"}
                ]
            }
        }
        routes = amap.format_routes(api_response, destination_name="目的地")
        assert len(routes) == 2
        assert routes[0]["distance_km"] == 5.0
        assert routes[1]["distance_km"] == 8.0

    def test_format_route_empty_paths(self, amap):
        api_response = {"status": "1", "route": {"paths": []}}
        route = amap.format_route(api_response, destination_name="x")
        assert route is None


class TestAPIError:
    def test_api_returns_error_status(self, amap):
        mock_response = {"status": "0", "info": "INVALID_USER_KEY"}
        with patch.object(amap, 'get', return_value=mock_response):
            result = amap.geocode("北京")
            assert result["status"] == "0"

    def test_api_key_injected(self, amap):
        # Key is injected at _build_request level, not at get() level
        url, params = amap._build_request("GET", "/geocode/geo", {"address": "北京"})
        assert params["key"] == "test_amap_key"
