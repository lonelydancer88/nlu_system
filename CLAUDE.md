# 车载智能助手（咖啡订购 + 导航）

## 项目概述

LLM驱动的对话式Agent，支持咖啡订购和车载导航两个场景。自然语言交互，多轮对话，实时模拟。

## 运行

```bash
python agent.py
```

依赖：Python 3.10+，Ollama（gemma4:e2b 模型）

## 项目结构

```
agent.py                    # 主入口，UnifiedAgent
coffee_agent.py             # 向后兼容入口
modules/
  nlu.py                    # NLU：LLM主解析 + RuleNLU兜底
  order_manager.py          # 咖啡订单管理
  data_manager.py           # 咖啡数据层（JSON）
  simulation.py             # 订单状态模拟
  nav_manager.py            # 导航业务逻辑
  nav_data_manager.py       # 导航数据层（JSON）
  nav_simulation.py         # 导航过程模拟
data/
  coffee_shops.json         # 咖啡店菜单
  user_preferences.json     # 用户偏好
  order_history.json        # 订单历史
  nav_pois.json             # POI数据
  nav_favorites.json        # 家/公司/收藏
  nav_routes.json           # 预置路线
  nav_vehicle_status.json   # 车辆状态
```

## 架构

```
用户输入 → UnifiedAgent.process_input()
         → LLMNLU.parse() → intents数组（支持多意图）
         → 逐个处理intent → handler响应拼接
```

### 核心组件

- **UnifiedAgent**：统一调度，管理两个场景的状态机，处理confirm/cancel消歧
- **LLMNLU**：通过Ollama调用本地LLM解析意图和槽位，失败时可选降级到RuleNLU
- **OrderManager / NavManager**：各自场景的业务逻辑和状态管理
- **DataManager / NavDataManager**：JSON文件数据持久化
- **Simulation / NavSimulation**：线程+回调模拟订单/导航过程

### NLU设计

- **LLM优先**：意图识别和槽位提取全部由LLM完成（SYSTEM_PROMPT定义所有意图和参数）
- **RuleNLU兜底**：`enable_fallback` 控制（默认关闭），仅覆盖咖啡场景基本意图
- **输出格式**：`{"intents": [{"intent": "...", "params": {...}}, ...], ...}`，支持一条输入多个意图
- **confirm/cancel拆分**：LLM根据上下文区分 `confirm_order`/`confirm_nav`/`cancel_order`/`cancel_nav`
- **debug信息**：每次返回包含 `llm_request_messages`（输入）和 `llm_raw_response`（原始输出）

### 状态机

- 咖啡：`idle` → `waiting_confirm` → `idle`
- 导航：`idle` → `planning` → `navigating` → `idle`
- 消歧：`_resolve_ambiguous_intent()` 根据当前状态修正confirm/cancel归属

### 意图列表

**咖啡**：order, reorder, history, recommend, confirm_order, cancel_order
**导航**：navigate, confirm_nav, cancel_nav, add_waypoint, search_poi, search_along_route, traffic_info, avoid_route, query_eta, vehicle_status, nav_home, nav_company, nav_favorite, select_destination
**通用**：greeting, help, unknown

## 关键约定

- 咖啡场景：intent=order且缺少coffee_name时，Agent侧强制澄清
- 导航场景：目的地歧义时返回候选列表，用户选择后（select_destination）继续规划
- 回家/去公司：直接构建路线，不走search_destination（避免子串误匹配）
- 对话历史：在process_input之后记录（避免当前用户消息在LLM请求中重复）
- 所有响应包含debug字段：`{"response": "...", "debug": {"nlu": parse_result}}`

## 配置

LLMNLU构造参数：
- `model`：Ollama模型名，默认 `"gemma4:e2b"`
- `base_url`：Ollama API地址，默认 `"http://localhost:11434/api/chat"`
- `timeout`：请求超时秒数，默认 `520.0`
- `enable_fallback`：LLM失败时是否降级到RuleNLU，默认 `False`
