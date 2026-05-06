"""快速测试云端LLM API Key是否可用"""
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

from config import Config
from agent import UnifiedAgent

LOG_FILE = "test_output.log"


def log(msg):
    """同时输出到文件和终端"""
    print(msg)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(msg + "\n")


def test_cloud_llm():
    # 每次运行清空日志文件
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write(f"=== 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n\n")

    config = Config()

    log("=== Config 加载结果 ===")
    log(f"  llm_provider: {config.llm_provider}")
    log(f"  llm_model: {config.llm_model}")
    log(f"  llm_base_url: {config.llm_base_url}")
    log(f"  llm_api_key: {config.llm_api_key[:12]}..." if config.llm_api_key else "  llm_api_key: NOT SET")
    log("")

    if not config.llm_api_key:
        log("ERROR: llm_api_key 未设置！")
        log("请在 config.json 或环境变量 LLM_API_KEY 中设置")
        return False

    log("=== 创建 Agent ===")
    agent = UnifiedAgent(config=config)
    log("")

    # 测试用例
    test_cases = [
        ("点一杯拿铁", "order"),
        ("导航去望京SOHO", "navigate"),
        ("有什么推荐的吗", "recommend"),
        ("取消订单", "cancel_order"),
    ]

    log("=== 测试解析 ===")
    all_passed = True
    for text, expected_intent in test_cases:
        result = agent.nlu.parse(text, history=[])
        actual_intent = result["intents"][0]["intent"] if result["intents"] else "NONE"
        status = "✓" if actual_intent == expected_intent else "✗"
        if actual_intent != expected_intent:
            all_passed = False
        log(f"  {status} \"{text}\"")
        log(f"    期望: {expected_intent}, 实际: {actual_intent}, 来源: {result.get('source')}")
    log("")

    if all_passed:
        log("=== 全部测试通过 ===")
    else:
        log("=== 部分测试失败 ===")

    log(f"\n=== 测试完成: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")
    return all_passed


if __name__ == "__main__":
    success = test_cloud_llm()
    print(f"\n日志已写入: {LOG_FILE}")
    sys.exit(0 if success else 1)
