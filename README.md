# NLU System - 车载智能助手

基于本地LLM的多场景对话式Agent，支持**咖啡订购**和**车载导航**两个场景，自然语言交互，多轮对话，实时模拟。

## 特性

- **LLM驱动的NLU**：意图识别和槽位提取由本地LLM完成，支持多意图（如"导航去中关村，顺便点杯美式"）
- **双场景统一调度**：咖啡订购 + 车载导航，LLM根据上下文自动区分场景
- **多轮对话**：信息不足时澄清追问，导航中可随时追加指令
- **实时模拟**：订单状态跟踪 / 导航过程推进
- **Debug可见**：每次交互输出LLM原始输入输出和NLU解析结果

## 快速开始

### 前置条件

- Python 3.10+
- [Ollama](https://ollama.ai) 已安装并运行
- 下载模型：`ollama pull gemma4:e2b`

### 运行

```bash
python agent.py
```

### 示例对话

```
🚗☕ 欢迎使用车载智能助手！
我可以帮你点咖啡，也可以帮你导航。直接告诉我你想做什么吧~

> 导航去中关村
< 为您规划路线：
  📍 终点：中关村
  📏 距离：约19.8公里
  ⏱ 预计用时：29分钟
  🚦 路况：缓行
  是否开始导航？

> 确认
< 🚗 导航开始！目的地：中关村，预计29分钟到达~

> 沿途找个加油站
< 沿途加油站：
  1. 中石化望京加油站 - 距路线0.8公里
  2. 中石油北五环加油站 - 距路线1.2公里

> 还有多久到
< 预计还需18分钟到达中关村，当前路况畅通

> 帮我点杯美式 少冰
< 好的，为您确认订单：
  📍 店铺：瑞幸咖啡
  ☕ 商品：大杯美式 少冰 无糖
  💰 价格：14元
  是否确认下单？

> 确认
< 🎉 订单已提交，订单号：CF1776996604~
```

## 项目结构

```
agent.py                    # 主入口（UnifiedAgent）
coffee_agent.py             # 向后兼容入口
modules/
  nlu.py                    # NLU模块（LLM + RuleNLU兜底）
  order_manager.py          # 咖啡订单管理
  data_manager.py           # 咖啡数据层
  simulation.py             # 订单状态模拟
  nav_manager.py            # 导航业务逻辑
  nav_data_manager.py       # 导航数据层
  nav_simulation.py         # 导航过程模拟
data/
  coffee_shops.json         # 咖啡店菜单（5家店）
  user_preferences.json     # 用户偏好
  order_history.json        # 订单历史
  nav_pois.json             # POI数据
  nav_favorites.json        # 家/公司/收藏地点
  nav_routes.json           # 预置路线
  nav_vehicle_status.json   # 车辆状态
```

## 架构

```
用户输入 → UnifiedAgent.process_input()
         → LLMNLU.parse() → intents数组（支持多意图）
         → 逐个处理intent → handler响应拼接
```

### NLU设计

| 特性 | 说明 |
|------|------|
| LLM优先 | 意图识别和槽位提取全部由LLM完成 |
| 多意图支持 | 一条输入可解析出多个意图，独立处理拼接响应 |
| confirm/cancel拆分 | LLM根据上下文区分 `confirm_order` / `confirm_nav` |
| RuleNLU兜底 | `enable_fallback` 控制（默认关闭） |
| Debug输出 | 包含 `llm_request_messages` 和 `llm_raw_response` |

### 支持意图

**咖啡场景**：点单(order)、重复上次(reorder)、查询历史(history)、推荐(recommend)、确认下单(confirm_order)、取消订单(cancel_order)

**导航场景**：导航去某地(navigate)、确认导航(confirm_nav)、取消导航(cancel_nav)、添加途经点(add_waypoint)、搜索附近POI(search_poi)、沿途搜索(search_along_route)、查询路况(traffic_info)、避让路线(avoid_route)、查询ETA(query_eta)、车辆状态(vehicle_status)、回家(nav_home)、去公司(nav_company)、收藏地点(nav_favorite)、选择目的地(select_destination)

**通用**：打招呼(greeting)、帮助(help)

### 状态机

```
咖啡：idle → waiting_confirm → idle
导航：idle → planning → navigating → idle
```

## 配置

LLMNLU 构造参数：

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `model` | Ollama 模型名 | `"gemma4:e2b"` |
| `base_url` | Ollama API 地址 | `"http://localhost:11434/api/chat"` |
| `timeout` | 请求超时（秒） | `520.0` |
| `enable_fallback` | LLM失败时是否降级到规则匹配 | `False` |

## License

MIT
