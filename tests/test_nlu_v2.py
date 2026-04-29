"""Tests for NLU updates - new intents (select_shop, change_route) and params (city, radius)."""
import json
import os
import pytest
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modules.nlu import RuleNLU, LLMNLU, VALID_INTENTS


class TestNewValidIntents:
    def test_select_shop_in_valid_intents(self):
        assert "select_shop" in VALID_INTENTS

    def test_change_route_in_valid_intents(self):
        assert "change_route" in VALID_INTENTS


class TestRuleNLUSelectShop:
    @pytest.fixture
    def nlu(self):
        return RuleNLU()

    def test_select_shop_by_number(self, nlu):
        result = nlu.parse("第一个店")
        assert result["intents"][0]["intent"] == "select_shop"
        assert result["intents"][0]["params"].get("selection") in (1, "1")

    def test_select_shop_this_one(self, nlu):
        result = nlu.parse("就这家吧")
        assert result["intents"][0]["intent"] == "select_shop"

    def test_select_shop_with_selection_number(self, nlu):
        result = nlu.parse("选第2个")
        assert result["intents"][0]["intent"] == "select_shop"
        assert result["intents"][0]["params"].get("selection") in (2, "2")


class TestRuleNLUChangeRoute:
    @pytest.fixture
    def nlu(self):
        return RuleNLU()

    def test_change_route_shortcut(self, nlu):
        result = nlu.parse("换条路线")
        assert result["intents"][0]["intent"] == "change_route"

    def test_change_route_another(self, nlu):
        result = nlu.parse("走另一条路")
        assert result["intents"][0]["intent"] == "change_route"


class TestLLMNLUValidateNewIntents:
    @pytest.fixture
    def nlu(self):
        return LLMNLU(enable_fallback=False)

    def test_validate_select_shop(self, nlu):
        result = {
            "intents": [{"intent": "select_shop", "params": {"selection": 1}}],
            "needs_clarification": False
        }
        assert nlu._validate_result(result) is True

    def test_validate_change_route(self, nlu):
        result = {
            "intents": [{"intent": "change_route", "params": {}}],
            "needs_clarification": False
        }
        assert nlu._validate_result(result) is True

    @patch.object(LLMNLU, '_call_ollama')
    def test_parse_select_shop_from_llm(self, mock_call, nlu):
        mock_call.return_value = json.dumps({
            "intents": [{"intent": "select_shop", "params": {"selection": 1}}],
            "needs_clarification": False,
            "clarification_question": None
        })
        result = nlu.parse("第一家")
        assert result["intents"][0]["intent"] == "select_shop"
        assert result["source"] == "llm"

    @patch.object(LLMNLU, '_call_ollama')
    def test_parse_change_route_from_llm(self, mock_call, nlu):
        mock_call.return_value = json.dumps({
            "intents": [{"intent": "change_route", "params": {}}],
            "needs_clarification": False,
            "clarification_question": None
        })
        result = nlu.parse("换条路")
        assert result["intents"][0]["intent"] == "change_route"
        assert result["source"] == "llm"


class TestNewParamsInRules:
    @pytest.fixture
    def nlu(self):
        return RuleNLU()

    def test_navigate_with_city(self, nlu):
        result = nlu.parse("导航去上海南京路")
        # Should extract navigate intent, city param from LLM side
        # RuleNLU just extracts the basic intent
        assert result["intents"][0]["intent"] == "navigate"

    def test_search_poi_with_radius(self, nlu):
        # Radius is primarily an LLM-extracted param
        result = nlu.parse("附近3公里找加油站")
        assert result["intents"][0]["intent"] == "search_poi"
