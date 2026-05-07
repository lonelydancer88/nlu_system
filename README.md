# 车载智能助手

基于LLM的多场景对话式Agent，支持**咖啡订购**和**车载导航**两个场景，自然语言交互，多轮对话，实时模拟。

## 特性

- **LLM驱动的NLU**：意图识别和槽位提取由LLM完成，支持多意图（如"导航去中关村，顺便点杯美式"）
- **双场景统一调度**：咖啡订购 + 车载导航，LLM根据上下文自动区分场景
- **多轮对话**：信息不足时澄清追问，导航中可随时追加指令
- **实时模拟**：订单状态跟踪 / 导航过程推进
- **Debug可见**：每次交互输出LLM原始输入输出和NLU解析结果
- **泛需求推荐**：LLM原生知识推荐POI，选择后调用高德API导航

## 快速开始

### 前置条件

- Python 3.10+
- 云端LLM（DashScope兼容）或本地Ollama

### 运行

```bash
python agent.py
```

### 示例对话

```
🚗☕ 欢迎使用车载智能助手！
直接告诉我你想做什么吧~

> 推荐一个适合情侣约会的地方
< 为您推荐以下地点：
  1. 蓝色港湾 - 环境浪漫，有湖畔美景，适合散步和晚餐
  2. 三里屯太古里 - 时尚地标，餐厅酒吧众多
  3. 什刹海 - 湖光山色，可以划船游览
  请选择您想去的地方（说编号或名称）~

> 第二个
< 为您规划路线：
  📍 终点：三里屯太古里
  📏 距离：约8.1公里
  ⏱ 预计用时：24分钟
  🚦 路况：畅通
  是否开始导航？

> 我的家在哪
< 您的家在：朝阳区望京西园四区

> 去公司
< 为您规划路线：
  📍 终点：公司 - 海淀区中关村软件园二期
  📏 距离：约23.9公里
  ⏱ 预计用时：57分钟
  是否开始导航？

> /clear
< 上下文已清空，有什么可以帮你的吗？
```

## 项目结构

```
agent.py                    # 主入口（UnifiedAgent）
modules/
  nlu.py                    # NLU模块（LLM + RuleNLU兜底）
  order_manager.py           # 咖啡订单管理
  data_manager.py           # 咖啡数据层
  simulation.py             # 订单状态模拟
  nav_manager.py            # 导航业务逻辑
  nav_data_manager.py       # 导航数据层
  nav_simulation.py         # 导航过程模拟
  amap_client.py            # 高德API客户端
data/
  coffee_shops.json         # 咖啡店菜单
  user_preferences.json     # 用户偏好
  order_history.json        # 订单历史
  nav_pois.json             # POI数据
  nav_favorites.json         # 家/公司/收藏地点
  nav_routes.json           # 预置路线
  nav_vehicle_status.json    # 车辆状态
config.json                 # API密钥配置
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
| RuleNLU兜底 | `enable_fallback` 控制（默认关闭），仅LLM不可用时启用 |
| Debug输出 | 包含 `llm_request_messages` 和 `llm_raw_response` |

### 支持意图

**咖啡场景**：`order`、`reorder`、`history`、`recommend`、`confirm_order`、`cancel_order`、`select_shop`

**导航场景**：
- 导航：`navigate`、`confirm_nav`、`cancel_nav`、`add_waypoint`
- POI搜索：`search_poi`（高德API）、`search_along_route`、`recommend_poi`（LLM原生推荐）
- 选择：`select_destination`、`change_route`
- 查询：`traffic_info`、`query_eta`、`query_home`、`query_company`、`vehicle_status`
- 快捷导航：`nav_home`、`nav_company`、`nav_favorite`

**通用**：`greeting`、`help`

### 状态机

```
咖啡：idle → waiting_confirm → idle
导航：idle → planning → navigating → idle
```

### 泛需求推荐流程

```
用户: "推荐一个适合情侣约会的地方"
  ↓
LLM解析为 recommend_poi，返回 POI 列表（名称+理由）
  ↓
用户选择（如"第二个"）
  ↓
调用高德API搜索该POI获取具体位置
  ↓
规划导航路线
```

## 配置

`config.json` 配置文件：

```json
{
  "llm_api_key": "your-dashscope-api-key",
  "llm_provider": "dashscope",
  "llm_model": "glm-5",
  "llm_base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
  "amap_api_key": "your-amap-api-key",
  "amap_city": "北京"
}
```

LLMNLU 构造参数：

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `model` | Ollama 模型名 | `"gemma4:e2b"` |
| `base_url` | Ollama API 地址 | `"http://localhost:11434/api/chat"` |
| `timeout` | 请求超时（秒） | `520.0` |
| `enable_fallback` | LLM失败时是否降级到规则匹配 | `False` |

## 命令

- `/clear` 或 `清空上下文`：清空对话历史和所有待处理状态
- `退出` / `quit`：退出程序

## License

MIT
