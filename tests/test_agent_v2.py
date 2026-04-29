"""Tests for agent.py updates - new handlers and config integration."""
import json
import os
import pytest
import sys
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agent import UnifiedAgent


@pytest.fixture
def agent_with_config():
    """Create agent with config-loaded components (mocked)."""
    with patch.object(UnifiedAgent, '__init__', lambda self: None):
        a = UnifiedAgent.__new__(UnifiedAgent)

    from modules.order_manager import OrderManager
    from modules.nav_manager import NavigationManager
    from modules.simulation import OrderSimulator
    from modules.nav_simulation import NavigationSimulator
    from modules.amap_client import AmapClient
    from modules.coffee_api_client import MockCoffeeAPI
    from config import Config

    a.order_manager = MagicMock(spec=OrderManager)
    a.nav_manager = MagicMock(spec=NavigationManager)
    a.nav_manager.nav_state = "planning"  # allow change_route check
    a.order_simulator = OrderSimulator()
    a.nav_simulator = NavigationSimulator()
    a.coffee_state = "idle"
    a.current_order = None
    a.conversation_history = []
    a.nlu = MagicMock()
    a.config = MagicMock(spec=Config)
    a.config.amap_api_key = "test_key"
    a.config.amap_city = "北京"
    a.config.coffee_api_mode = "mock"
    return a


class TestHandleSelectShop:
    def test_handle_select_shop(self, agent_with_config):
        agent_with_config.order_manager.search_shops.return_value = [
            {"id": "shop_1", "name": "瑞幸咖啡", "address": "望京SOHO"}
        ]
        # After selecting a shop, user should be able to continue ordering
        result = agent_with_config.handle_select_shop_intent({"selection": 1})
        assert isinstance(result, str)


class TestHandleChangeRoute:
    def test_handle_change_route(self, agent_with_config):
        agent_with_config.nav_manager.plan_route.return_value = {
            "response": "为您规划新路线：\n📏 距离：约8公里"
        }
        result = agent_with_config.handle_change_route_intent({})
        assert isinstance(result, str)


class TestConfigIntegration:
    def test_agent_creates_amap_client_with_config(self):
        """Agent should create AmapClient from config when key is available."""
        from modules.amap_client import AmapClient
        # Verify AmapClient accepts api_key
        client = AmapClient(api_key="test_key")
        assert client.api_key == "test_key"

    def test_agent_creates_coffee_api_from_config(self):
        """Agent should create MockCoffeeAPI when config mode is 'mock'."""
        with patch.object(UnifiedAgent, '__init__', lambda self: None):
            a = UnifiedAgent.__new__(UnifiedAgent)

        from modules.coffee_api_client import MockCoffeeAPI

        api = a._create_coffee_api(mode="mock")
        assert isinstance(api, MockCoffeeAPI)

    def test_agent_creates_meituan_api_from_config(self):
        """Agent should create MeituanCoffeeAPI when config mode is 'meituan'."""
        with patch.object(UnifiedAgent, '__init__', lambda self: None):
            a = UnifiedAgent.__new__(UnifiedAgent)

        from modules.coffee_api_client import MeituanCoffeeAPI

        api = a._create_coffee_api(mode="meituan", api_key="test_key")
        assert isinstance(api, MeituanCoffeeAPI)


class TestProcessInputWithNewIntents:
    def test_process_select_shop_intent(self, agent_with_config):
        agent_with_config.nlu.parse.return_value = {
            "intents": [{"intent": "select_shop", "params": {"selection": 1}}],
            "needs_clarification": False,
            "clarification_question": None
        }
        result = agent_with_config.process_input("第一个")
        assert result["response"]  # non-empty

    def test_process_change_route_intent(self, agent_with_config):
        agent_with_config.nlu.parse.return_value = {
            "intents": [{"intent": "change_route", "params": {}}],
            "needs_clarification": False,
            "clarification_question": None
        }
        result = agent_with_config.process_input("换条路")
        assert result["response"]  # non-empty


class TestNewIntentHandlerMap:
    def test_select_shop_in_handler_map(self, agent_with_config):
        # Verify the agent can route select_shop intent
        agent_with_config.order_manager.search_shops.return_value = [
            {"id": "1", "name": "瑞幸咖啡", "address": "望京"}
        ]
        response = agent_with_config._process_single_intent(
            "select_shop", {"selection": 1},
            {"needs_clarification": False, "clarification_question": None}
        )
        assert isinstance(response, str)

    def test_change_route_in_handler_map(self, agent_with_config):
        agent_with_config.nav_manager.plan_route.return_value = {
            "response": "新路线规划中..."
        }
        response = agent_with_config._process_single_intent(
            "change_route", {},
            {"needs_clarification": False, "clarification_question": None}
        )
        assert isinstance(response, str)
