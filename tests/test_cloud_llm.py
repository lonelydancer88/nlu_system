"""测试云端LLM（DashScope）和本地Ollama降级"""
import json
import os
import pytest
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modules.nlu import LLMNLU

# 测试用占位符，实际运行时通过环境变量设置真实API Key
TEST_API_KEY = os.environ.get("LLM_API_KEY", "")
TEST_MODEL = os.environ.get("LLM_MODEL", "glm-5")
TEST_BASE_URL = os.environ.get("LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")


class TestCloudLLMFallback:
    """测试云端优先，云端失败时降级到本地Ollama"""

    @pytest.fixture
    def cloud_nlu(self, monkeypatch):
        """带云端API Key的NLU实例"""
        if not TEST_API_KEY:
            pytest.skip("需要设置 LLM_API_KEY 环境变量来运行云端测试")
        monkeypatch.setenv("LLM_API_KEY", TEST_API_KEY)
        # 强制不使用本地ollama（测试云端）
        nlu = LLMNLU(
            llm_provider="dashscope",
            llm_api_key=TEST_API_KEY,
            llm_model=TEST_MODEL,
            llm_base_url=TEST_BASE_URL,
            llm_timeout=120.0,  # 云端API可能较慢
            model="",  # 空模型，不使用本地ollama
            enable_fallback=True
        )
        return nlu

    @pytest.fixture
    def fallback_nlu(self, monkeypatch):
        """本地ollama降级的NLU实例（用于测试降级）"""
        nlu = LLMNLU(
            model="gemma4:e2b",
            base_url="http://localhost:11434/api/chat",
            timeout=10.0,  # 短超时快速失败
            enable_fallback=True
        )
        return nlu

    def test_cloud_llm_coffee_order(self, cloud_nlu):
        """云端LLM解析咖啡订单"""
        result = cloud_nlu.parse("我要一杯美式咖啡", history=[])
        assert result["source"] == "cloud"
        assert len(result["intents"]) == 1
        assert result["intents"][0]["intent"] == "order"
        assert result["intents"][0]["params"]["coffee_name"] == "美式"

    def test_cloud_llm_navigate(self, cloud_nlu):
        """云端LLM解析导航"""
        result = cloud_nlu.parse("导航去望京SOHO", history=[])
        assert result["source"] == "cloud"
        assert len(result["intents"]) == 1
        assert result["intents"][0]["intent"] == "navigate"
        assert "望京" in result["intents"][0]["params"]["destination"]

    def test_cloud_llm_multi_intent(self, cloud_nlu):
        """云端LLM解析多意图"""
        result = cloud_nlu.parse("导航去中关村，顺便点杯拿铁", history=[])
        assert result["source"] == "cloud"
        assert len(result["intents"]) == 2
        intents = [i["intent"] for i in result["intents"]]
        assert "navigate" in intents
        assert "order" in intents

    def test_cloud_llm_cancel(self, cloud_nlu):
        """云端LLM解析取消"""
        result = cloud_nlu.parse("取消订单", history=[])
        assert result["source"] == "cloud"
        assert result["intents"][0]["intent"] == "cancel_order"

    def test_local_fallback_when_cloud_fails(self, fallback_nlu):
        """云端失败时降级到本地ollama"""
        # 这个测试在云端不可用时会触发本地降级
        result = fallback_nlu.parse("点一杯咖啡", history=[])
        # 结果可能是 cloud -> local -> rule_fallback
        assert "source" in result
        assert "intents" in result

    def test_cloud_llm_recommend(self, cloud_nlu):
        """云端LLM解析推荐"""
        result = cloud_nlu.parse("有什么推荐的吗", history=[])
        assert result["source"] == "cloud"
        assert result["intents"][0]["intent"] == "recommend"

    def test_cloud_llm_reorder(self, cloud_nlu):
        """云端LLM解析再来一单"""
        result = cloud_nlu.parse("再来一杯一样的", history=[])
        assert result["source"] == "cloud"
        assert result["intents"][0]["intent"] == "reorder"

    def test_cloud_llm_traffic_info(self, cloud_nlu):
        """云端LLM解析路况查询"""
        result = cloud_nlu.parse("现在路上堵不堵", history=[])
        assert result["source"] == "cloud"
        assert result["intents"][0]["intent"] == "traffic_info"

    def test_llm_response_contains_raw_content(self, cloud_nlu):
        """验证返回包含原始LLM响应"""
        result = cloud_nlu.parse("点一杯拿铁", history=[])
        assert "llm_raw_response" in result
        assert result["llm_raw_response"] is not None
        assert len(result["llm_raw_response"]) > 0


class TestLLMProviderSelection:
    """测试LLM Provider选择逻辑"""

    def test_cloud_used_when_api_key_present(self, monkeypatch):
        """当llm_api_key存在时使用云端"""
        if not TEST_API_KEY:
            pytest.skip("需要设置 LLM_API_KEY 环境变量")
        monkeypatch.setenv("LLM_API_KEY", TEST_API_KEY)
        nlu = LLMNLU(
            llm_api_key=TEST_API_KEY,
            llm_model=TEST_MODEL,
            llm_base_url=TEST_BASE_URL,
            model="",  # 无本地模型
        )
        # 检查云端API Key被正确设置
        assert nlu.llm_api_key == TEST_API_KEY
        assert nlu.llm_model == TEST_MODEL

    def test_local_used_when_no_cloud_key(self):
        """当没有云端API Key时使用本地ollama"""
        nlu = LLMNLU(
            model="gemma4:e2b",
            base_url="http://localhost:11434/api/chat",
            timeout=10.0,
            llm_api_key="",  # 无云端API Key
        )
        assert nlu.llm_api_key == ""
        assert nlu.model == "gemma4:e2b"
