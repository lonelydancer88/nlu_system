"""Tests for UnifiedAgent - integration-level tests with mocked NLU."""
import json
import os
import sys
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agent import UnifiedAgent


@pytest.fixture
def agent():
    """Create agent with mocked NLU to avoid Ollama dependency."""
    with patch.object(UnifiedAgent, '__init__', lambda self: None):
        a = UnifiedAgent.__new__(UnifiedAgent)

    # Set up minimal state
    from modules.order_manager import OrderManager
    from modules.nav_manager import NavigationManager
    from modules.simulation import OrderSimulator
    from modules.nav_simulation import NavigationSimulator

    a.order_manager = MagicMock(spec=OrderManager)
    a.nav_manager = MagicMock(spec=NavigationManager)
    a.order_simulator = OrderSimulator()
    a.nav_simulator = NavigationSimulator()
    a.coffee_state = "idle"
    a.current_order = None
    a.conversation_history = []
    a.nlu = MagicMock()

    return a


class TestResolveAmbiguousIntent:
    def test_confirm_order_when_coffee_waiting(self, agent):
        agent.coffee_state = "waiting_confirm"
        result = agent._resolve_ambiguous_intent("confirm_order")
        assert result == "confirm_order"

    def test_confirm_order_when_nav_planning(self, agent):
        agent.coffee_state = "idle"
        agent.nav_manager.nav_state = "planning"
        result = agent._resolve_ambiguous_intent("confirm_order")
        assert result == "confirm_nav"

    def test_confirm_nav_when_coffee_waiting(self, agent):
        agent.coffee_state = "waiting_confirm"
        agent.nav_manager.nav_state = "idle"
        result = agent._resolve_ambiguous_intent("confirm_nav")
        assert result == "confirm_order"

    def test_cancel_order_when_nav_active(self, agent):
        agent.coffee_state = "idle"
        agent.nav_manager.nav_state = "navigating"
        result = agent._resolve_ambiguous_intent("cancel_order")
        assert result == "cancel_nav"

    def test_cancel_nav_when_coffee_waiting(self, agent):
        agent.coffee_state = "waiting_confirm"
        agent.nav_manager.nav_state = "idle"
        result = agent._resolve_ambiguous_intent("cancel_nav")
        assert result == "cancel_order"

    def test_no_ambiguity(self, agent):
        agent.coffee_state = "idle"
        agent.nav_manager.nav_state = "idle"
        assert agent._resolve_ambiguous_intent("order") == "order"
        assert agent._resolve_ambiguous_intent("navigate") == "navigate"


class TestCoffeeHandlers:
    def test_handle_order_no_coffee_name(self, agent):
        result = agent.handle_order_intent({})
        assert "什么咖啡" in result

    def test_handle_order_with_coffee_name(self, agent):
        agent.order_manager.create_order.return_value = {
            "order_id": "CF123",
            "shop_name": "瑞幸咖啡",
            "coffee_name": "拿铁",
            "size": "大杯",
            "ice": "少冰",
            "sugar": "半糖",
            "toppings": [],
            "price": 18,
        }
        result = agent.handle_order_intent({"coffee_name": "拿铁"})
        assert "拿铁" in result
        assert "18" in result
        assert agent.coffee_state == "waiting_confirm"

    def test_handle_confirm_not_waiting(self, agent):
        agent.coffee_state = "idle"
        result = agent.handle_confirm_order_intent()
        assert "没有" in result

    def test_handle_confirm_waiting(self, agent):
        agent.coffee_state = "waiting_confirm"
        agent.current_order = {"order_id": "CF123"}
        agent.order_manager.confirm_order.return_value = {"order_id": "CF123", "status": "confirmed"}
        result = agent.handle_confirm_order_intent()
        assert "CF123" in result
        assert agent.coffee_state == "idle"

    def test_handle_cancel_waiting(self, agent):
        agent.coffee_state = "waiting_confirm"
        agent.current_order = {"order_id": "CF123"}
        result = agent.handle_cancel_order_intent()
        assert "取消" in result
        assert agent.coffee_state == "idle"

    def test_handle_reorder_no_history(self, agent):
        agent.order_manager.reorder_last.return_value = None
        result = agent.handle_reorder_intent()
        assert "没有" in result

    def test_handle_reorder_with_history(self, agent):
        agent.order_manager.reorder_last.return_value = {
            "order_id": "CF456",
            "shop_name": "星巴克",
            "coffee_name": "美式",
            "size": "大杯",
            "ice": "正常冰",
            "sugar": "无糖",
            "toppings": [],
            "price": 25,
        }
        result = agent.handle_reorder_intent()
        assert "美式" in result
        assert agent.coffee_state == "waiting_confirm"

    def test_handle_history_empty(self, agent):
        agent.order_manager.get_order_history.return_value = []
        result = agent.handle_history_intent()
        assert "没有" in result

    def test_handle_history_with_data(self, agent):
        agent.order_manager.get_order_history.return_value = [
            {"create_time": "2026-01-01 09:00", "shop_name": "瑞幸", "coffee_name": "拿铁",
             "size": "大杯", "ice": "少冰", "sugar": "半糖", "toppings": [], "price": 18}
        ]
        result = agent.handle_history_intent()
        assert "拿铁" in result

    def test_handle_recommend(self, agent):
        agent.order_manager.get_recommendations.return_value = [
            {"shop_name": "瑞幸咖啡", "coffee_name": "拿铁", "price": 18}
        ]
        result = agent.handle_recommend_intent({})
        assert "拿铁" in result

    def test_handle_greeting(self, agent):
        result = agent.handle_greeting_intent()
        assert "你好" in result or "助手" in result


class TestNavHandlers:
    def test_handle_navigate(self, agent):
        agent.nav_manager.plan_route.return_value = {"response": "为您规划路线..."}
        result = agent.handle_navigate_intent({"destination": "中关村"})
        assert "规划" in result

    def test_handle_confirm_nav(self, agent):
        agent.nav_manager.confirm_navigation.return_value = {"response": "导航开始！", "start_simulation": False}
        result = agent.handle_confirm_nav_intent()
        assert "导航开始" in result

    def test_handle_cancel_nav(self, agent):
        agent.nav_manager.cancel_navigation.return_value = {"response": "导航已取消"}
        result = agent.handle_cancel_nav_intent()
        assert "取消" in result

    def test_handle_search_poi(self, agent):
        agent.nav_manager.search_poi.return_value = {"response": "附近加油站：\n1. 中石化"}
        result = agent.handle_search_poi_intent({"poi_type": "gas_station"})
        assert "加油站" in result

    def test_handle_query_eta(self, agent):
        agent.nav_manager.query_eta.return_value = {"response": "预计还需25分钟到达"}
        result = agent.handle_query_eta_intent()
        assert "分钟" in result

    def test_handle_vehicle_status(self, agent):
        agent.nav_manager.get_vehicle_status.return_value = {"response": "当前油量：65%"}
        result = agent.handle_vehicle_status_intent()
        assert "油量" in result


class TestProcessInput:
    def test_process_input_single_intent(self, agent):
        agent.nlu.parse.return_value = {
            "intents": [{"intent": "greeting", "params": {}}],
            "needs_clarification": False,
            "clarification_question": None
        }
        result = agent.process_input("你好")
        assert result["response"]  # non-empty
        assert "debug" in result

    def test_process_input_order_missing_coffee_name(self, agent):
        agent.nlu.parse.return_value = {
            "intents": [{"intent": "order", "params": {}}],
            "needs_clarification": False,
            "clarification_question": None
        }
        result = agent.process_input("点一杯咖啡")
        assert "什么咖啡" in result["response"]

    def test_process_input_exit(self, agent):
        with pytest.raises(SystemExit):
            agent.process_input("退出")


class TestConversationHistory:
    def test_add_to_history(self, agent):
        agent._add_to_history("user", "你好")
        agent._add_to_history("assistant", "你好呀~")
        assert len(agent.conversation_history) == 2

    def test_history_limit(self, agent):
        for i in range(15):
            agent._add_to_history("user", f"msg{i}")
        assert len(agent.conversation_history) <= 10
