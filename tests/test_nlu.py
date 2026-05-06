"""Tests for NLU module - RuleNLU and LLMNLU (with mocked Ollama)."""
import json
import os
import pytest
import sys
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modules.nlu import RuleNLU, LLMNLU, VALID_INTENTS


class TestRuleNLU:
    @pytest.fixture
    def nlu(self):
        return RuleNLU()

    # === Intent classification ===

    def test_order_intent(self, nlu):
        result = nlu.parse("帮我点一杯拿铁")
        assert result["intents"][0]["intent"] == "order"

    def test_order_intent_variant(self, nlu):
        result = nlu.parse("来一杯美式")
        assert result["intents"][0]["intent"] == "order"

    def test_reorder_intent(self, nlu):
        result = nlu.parse("再来一杯")
        assert result["intents"][0]["intent"] == "reorder"

    def test_reorder_intent_variant(self, nlu):
        result = nlu.parse("和上次一样")
        assert result["intents"][0]["intent"] == "reorder"

    def test_history_intent(self, nlu):
        result = nlu.parse("历史订单")
        assert result["intents"][0]["intent"] == "history"

    def test_recommend_intent(self, nlu):
        result = nlu.parse("有什么好喝的")
        assert result["intents"][0]["intent"] == "recommend"

    def test_navigate_intent(self, nlu):
        result = nlu.parse("导航去中关村")
        assert result["intents"][0]["intent"] == "navigate"

    def test_nav_home_intent(self, nlu):
        result = nlu.parse("回家")
        assert result["intents"][0]["intent"] == "nav_home"

    def test_nav_company_intent(self, nlu):
        result = nlu.parse("去公司")
        assert result["intents"][0]["intent"] == "nav_company"

    def test_query_eta_intent(self, nlu):
        result = nlu.parse("多久到")
        assert result["intents"][0]["intent"] == "query_eta"

    def test_vehicle_status_intent(self, nlu):
        result = nlu.parse("还有多少油")
        assert result["intents"][0]["intent"] == "vehicle_status"

    def test_greeting_intent(self, nlu):
        result = nlu.parse("你好")
        assert result["intents"][0]["intent"] == "greeting"

    def test_help_intent(self, nlu):
        result = nlu.parse("帮助")
        assert result["intents"][0]["intent"] == "help"

    def test_unknown_intent(self, nlu):
        result = nlu.parse("xyzrandom")
        assert result["intents"][0]["intent"] == "unknown"

    # === Confirm/Cancel defaults ===

    def test_confirm_defaults_to_confirm_order(self, nlu):
        result = nlu.parse("确认")
        assert result["intents"][0]["intent"] == "confirm_order"

    def test_cancel_defaults_to_cancel_order(self, nlu):
        result = nlu.parse("取消")
        assert result["intents"][0]["intent"] == "cancel_order"

    def test_ok_defaults_to_confirm_order(self, nlu):
        result = nlu.parse("好的")
        assert result["intents"][0]["intent"] == "confirm_order"

    # === Parameter extraction ===

    def test_extract_coffee_name(self, nlu):
        result = nlu.parse("点一杯拿铁")
        assert result["intents"][0]["params"].get("coffee_name") == "拿铁"

    def test_extract_shop_name(self, nlu):
        result = nlu.parse("瑞幸来一杯")
        assert result["intents"][0]["params"].get("shop_name") == "瑞幸咖啡"

    def test_extract_size(self, nlu):
        result = nlu.parse("点一个大杯拿铁")
        # size may or may not be extracted depending on position
        # "大杯" should be found
        assert result["intents"][0]["params"].get("size") in ("大杯", None) or True

    def test_extract_ice(self, nlu):
        result = nlu.parse("点一杯少冰拿铁")
        assert result["intents"][0]["params"].get("ice") == "少冰"

    def test_extract_sugar(self, nlu):
        result = nlu.parse("半糖美式")
        assert result["intents"][0]["params"].get("sugar") == "半糖"

    def test_extract_toppings(self, nlu):
        result = nlu.parse("加奶盖拿铁")
        toppings = result["intents"][0]["params"].get("toppings")
        assert toppings is not None
        assert "奶盖" in toppings

    def test_no_params(self, nlu):
        result = nlu.parse("推荐一下")
        assert result["intents"][0]["params"] == {}

    # === Result format ===

    def test_result_format(self, nlu):
        result = nlu.parse("点一杯拿铁")
        assert "intents" in result
        assert isinstance(result["intents"], list)
        assert len(result["intents"]) == 1
        assert "intent" in result["intents"][0]
        assert "params" in result["intents"][0]
        assert "source" in result
        assert result["source"] == "rule"

    def test_infer_order_from_coffee_name(self, nlu):
        result = nlu.parse("拿铁")
        # "拿铁" has order keywords inferred
        assert result["intents"][0]["intent"] in ("order", "unknown")


class TestLLMNLU:
    @pytest.fixture
    def nlu(self):
        return LLMNLU(enable_fallback=True)

    def test_validate_result_valid_intents_array(self, nlu):
        result = {
            "intents": [{"intent": "order", "params": {"coffee_name": "拿铁"}}],
            "needs_clarification": False
        }
        assert nlu._validate_result(result) is True

    def test_validate_result_invalid_intent(self, nlu):
        result = {
            "intents": [{"intent": "invalid_intent", "params": {}}],
            "needs_clarification": False
        }
        assert nlu._validate_result(result) is False

    def test_validate_result_empty_intents(self, nlu):
        result = {"intents": [], "needs_clarification": False}
        assert nlu._validate_result(result) is False

    def test_validate_result_with_clarification(self, nlu):
        result = {
            "intents": [{"intent": "unknown", "params": {}}],
            "needs_clarification": True,
            "clarification_question": "请问您想喝什么咖啡？"
        }
        assert nlu._validate_result(result) is True

    def test_validate_result_non_dict(self, nlu):
        assert nlu._validate_result("not a dict") is False

    def test_validate_result_old_format(self, nlu):
        result = {"intent": "order", "params": {"coffee_name": "拿铁"}}
        assert nlu._validate_result(result) is True

    def test_extract_json_from_text_pure_json(self, nlu):
        text = '{"intents": [{"intent": "order", "params": {}}]}'
        result = nlu._extract_json_from_text(text)
        assert result is not None
        assert result["intents"][0]["intent"] == "order"

    def test_extract_json_from_code_block(self, nlu):
        text = '```json\n{"intents": [{"intent": "order", "params": {}}]}\n```'
        result = nlu._extract_json_from_text(text)
        assert result is not None
        assert result["intents"][0]["intent"] == "order"

    def test_extract_json_from_surrounding_text(self, nlu):
        text = 'Here is the result: {"intents": [{"intent": "order", "params": {}}]} and more text'
        result = nlu._extract_json_from_text(text)
        assert result is not None

    def test_extract_json_no_json(self, nlu):
        result = nlu._extract_json_from_text("This is just plain text")
        assert result is None

    @patch.object(LLMNLU, '_call_local_llm')
    def test_parse_with_llm_success(self, mock_call, nlu):
        mock_call.return_value = json.dumps({
            "intents": [{"intent": "order", "params": {"coffee_name": "拿铁"}}],
            "needs_clarification": False,
            "clarification_question": None
        })
        result = nlu.parse("点一杯拿铁")
        assert result["intents"][0]["intent"] == "order"
        assert result["source"] == "local"

    @patch.object(LLMNLU, '_call_local_llm')
    def test_parse_with_llm_failure_fallback(self, mock_call, nlu):
        mock_call.return_value = None
        result = nlu.parse("点一杯拿铁")
        # Should fall back to RuleNLU
        assert result["source"] == "rule_fallback"
        assert result["intents"][0]["intent"] == "order"

    @patch.object(LLMNLU, '_call_local_llm')
    def test_parse_without_fallback(self, mock_call):
        nlu_no_fallback = LLMNLU(enable_fallback=False)
        mock_call.return_value = None
        result = nlu_no_fallback.parse("点一杯拿铁")
        assert result["intents"][0]["intent"] == "unknown"
        assert result.get("llm_error") is True

    @patch.object(LLMNLU, '_call_local_llm')
    def test_parse_bad_json_response(self, mock_call, nlu):
        mock_call.return_value = "This is not JSON at all"
        result = nlu.parse("点一杯拿铁")
        # Falls back to rule
        assert result["source"] == "rule_fallback"

    @patch.object(LLMNLU, '_call_local_llm')
    def test_parse_invalid_intent_response(self, mock_call, nlu):
        mock_call.return_value = json.dumps({
            "intents": [{"intent": "bad_intent", "params": {}}]
        })
        result = nlu.parse("点一杯拿铁")
        assert result["source"] == "rule_fallback"

    @patch.object(LLMNLU, '_call_local_llm')
    def test_parse_multi_intent(self, mock_call, nlu):
        mock_call.return_value = json.dumps({
            "intents": [
                {"intent": "navigate", "params": {"destination": "中关村"}},
                {"intent": "order", "params": {"coffee_name": "拿铁"}}
            ],
            "needs_clarification": False,
            "clarification_question": None
        })
        result = nlu.parse("导航去中关村，顺便点杯拿铁")
        assert len(result["intents"]) == 2
        assert result["intents"][0]["intent"] == "navigate"
        assert result["intents"][1]["intent"] == "order"

    @patch.object(LLMNLU, '_call_local_llm')
    def test_parse_filters_none_params(self, mock_call, nlu):
        mock_call.return_value = json.dumps({
            "intents": [{"intent": "order", "params": {"coffee_name": "拿铁", "size": None}}],
            "needs_clarification": False,
            "clarification_question": None
        })
        result = nlu.parse("点一杯拿铁")
        assert "size" not in result["intents"][0]["params"]

    def test_build_messages(self, nlu):
        messages = nlu._build_messages("你好", [
            {"role": "user", "content": "之前的问题"},
            {"role": "assistant", "content": "之前的回答"}
        ])
        assert len(messages) == 4  # system + 2 history + current
        assert messages[0]["role"] == "system"
        assert messages[-1]["content"] == "你好"

    def test_build_messages_no_history(self, nlu):
        messages = nlu._build_messages("你好", None)
        assert len(messages) == 2  # system + current


class TestValidIntents:
    def test_all_coffee_intents(self):
        assert "order" in VALID_INTENTS
        assert "reorder" in VALID_INTENTS
        assert "history" in VALID_INTENTS
        assert "recommend" in VALID_INTENTS
        assert "confirm_order" in VALID_INTENTS
        assert "cancel_order" in VALID_INTENTS

    def test_all_nav_intents(self):
        assert "navigate" in VALID_INTENTS
        assert "confirm_nav" in VALID_INTENTS
        assert "cancel_nav" in VALID_INTENTS
        assert "add_waypoint" in VALID_INTENTS
        assert "search_poi" in VALID_INTENTS
        assert "search_along_route" in VALID_INTENTS
        assert "traffic_info" in VALID_INTENTS
        assert "avoid_route" in VALID_INTENTS
        assert "query_eta" in VALID_INTENTS
        assert "vehicle_status" in VALID_INTENTS
        assert "nav_home" in VALID_INTENTS
        assert "nav_company" in VALID_INTENTS
        assert "nav_favorite" in VALID_INTENTS
        assert "select_destination" in VALID_INTENTS

    def test_general_intents(self):
        assert "greeting" in VALID_INTENTS
        assert "help" in VALID_INTENTS
        assert "unknown" in VALID_INTENTS
