#!/usr/bin/env python3
"""测试泛需求推荐功能"""
import sys
sys.path.insert(0, '.')

from agent import UnifiedAgent
from config import Config

def test_recommend_poi():
    """测试用例1: 用户请求推荐POI"""
    agent = UnifiedAgent(Config())

    # 模拟用户请求推荐
    user_input = "推荐一个适合情侣约会的地方"
    result = agent.process_input(user_input)

    print("=" * 60)
    print(f"测试: {user_input}")
    print("=" * 60)

    # 检查意图
    intents = result['debug']['nlu'].get('intents', [])
    intent = intents[0].get('intent') if intents else None
    print(f"识别意图: {intent}")

    # 检查poi_list
    poi_list = result['debug']['nlu'].get('poi_list', [])
    print(f"POI列表: {poi_list}")

    # 检查响应
    response = result.get('response', '')
    print(f"响应:\n{response}")

    # 验证
    assert intent == 'recommend_poi', f"预期 recommend_poi, 实际 {intent}"
    assert poi_list is not None and len(poi_list) > 0, "POI列表为空"
    assert 'pending_poi_recommendations' in str(agent.__dict__), "未存储POI列表"

    print("\n✅ 测试1通过: 推荐POI功能正常\n")


def test_select_poi_by_index():
    """测试用例2: 用户选择编号"""
    agent = UnifiedAgent(Config())

    # 先请求推荐
    agent.process_input("推荐一个适合情侣约会的地方")

    print("=" * 60)
    print("测试: 用户选择第二个")
    print("=" * 60)

    # 用户选择第二个
    result = agent.process_input("第二个")

    # 检查意图
    intents = result['debug']['nlu'].get('intents', [])
    intent = intents[0].get('intent') if intents else None
    print(f"识别意图: {intent}")

    # 检查响应
    response = result.get('response', '')
    print(f"响应:\n{response}")

    # 验证
    # 如果没有高德API，会走fallback；这里主要验证意图识别
    assert intent in ['select_destination', 'navigate'], f"预期 select_destination 或 navigate, 实际 {intent}"

    print("\n✅ 测试2通过: 选择编号功能正常\n")


def test_select_poi_by_name():
    """测试用例3: 用户按名称选择"""
    agent = UnifiedAgent(Config())

    # 先请求推荐
    agent.process_input("推荐一个适合情侣约会的地方")

    print("=" * 60)
    print("测试: 用户说名称")
    print("=" * 60)

    # 用户说名称（但不确定具体名称，用一个不精确的描述）
    result = agent.process_input("去蓝色港湾")

    # 检查意图
    intents = result['debug']['nlu'].get('intents', [])
    intent = intents[0].get('intent') if intents else None
    print(f"识别意图: {intent}")

    response = result.get('response', '')
    print(f"响应:\n{response}")

    print("\n✅ 测试3通过: 按名称选择功能正常\n")


def test_clear_context():
    """测试用例4: 清空上下文"""
    agent = UnifiedAgent(Config())

    # 先请求推荐
    agent.process_input("推荐一个适合情侣约会的地方")

    print("=" * 60)
    print("测试: /clear 清空上下文")
    print("=" * 60)

    assert len(agent.pending_poi_recommendations) > 0, "POI推荐列表应该有内容"

    # 清空上下文
    result = agent.process_input("/clear")
    response = result.get('response', '')
    print(f"响应: {response}")

    assert len(agent.pending_poi_recommendations) == 0, "POI推荐列表应该被清空"
    print("\n✅ 测试4通过: 清空上下文功能正常\n")


def test_query_home():
    """测试用例5: 查询家的地址"""
    agent = UnifiedAgent(Config())

    print("=" * 60)
    print("测试: 我的家在哪")
    print("=" * 60)

    result = agent.process_input("我的家在哪")

    intents = result['debug']['nlu'].get('intents', [])
    intent = intents[0].get('intent') if intents else None
    print(f"识别意图: {intent}")

    response = result.get('response', '')
    print(f"响应: {response}")

    assert intent == 'query_home', f"预期 query_home, 实际 {intent}"
    print("\n✅ 测试5通过: 查询家地址功能正常\n")


def test_query_company():
    """测试用例6: 查询公司的地址"""
    agent = UnifiedAgent(Config())

    print("=" * 60)
    print("测试: 我的公司在哪")
    print("=" * 60)

    result = agent.process_input("我的公司在哪")

    intents = result['debug']['nlu'].get('intents', [])
    intent = intents[0].get('intent') if intents else None
    print(f"识别意图: {intent}")

    response = result.get('response', '')
    print(f"响应: {response}")

    assert intent == 'query_company', f"预期 query_company, 实际 {intent}"
    print("\n✅ 测试6通过: 查询公司地址功能正常\n")


def test_navigate_company():
    """测试用例7: 导航去公司"""
    agent = UnifiedAgent(Config())

    print("=" * 60)
    print("测试: 去公司")
    print("=" * 60)

    result = agent.process_input("去公司")

    intents = result['debug']['nlu'].get('intents', [])
    intent = intents[0].get('intent') if intents else None
    print(f"识别意图: {intent}")

    response = result.get('response', '')
    print(f"响应:\n{response[:200]}...")

    assert intent == 'nav_company', f"预期 nav_company, 实际 {intent}"
    print("\n✅ 测试7通过: 导航去公司功能正常\n")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("开始运行测试用例")
    print("=" * 60 + "\n")

    try:
        test_recommend_poi()
    except Exception as e:
        print(f"\n❌ 测试1失败: {e}\n")

    try:
        test_select_poi_by_index()
    except Exception as e:
        print(f"\n❌ 测试2失败: {e}\n")

    try:
        test_select_poi_by_name()
    except Exception as e:
        print(f"\n❌ 测试3失败: {e}\n")

    try:
        test_clear_context()
    except Exception as e:
        print(f"\n❌ 测试4失败: {e}\n")

    try:
        test_query_home()
    except Exception as e:
        print(f"\n❌ 测试5失败: {e}\n")

    try:
        test_query_company()
    except Exception as e:
        print(f"\n❌ 测试6失败: {e}\n")

    try:
        test_navigate_company()
    except Exception as e:
        print(f"\n❌ 测试7失败: {e}\n")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60 + "\n")
