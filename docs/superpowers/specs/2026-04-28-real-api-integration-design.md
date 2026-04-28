# 真实API集成设计文档

## 背景

当前车载智能助手所有数据来自本地JSON文件模拟，需要集成真实的高德地图API（导航场景）和美团外卖API（咖啡场景），使系统具备真实的地理编码、路径规划、POI搜索、店铺搜索和下单能力。

## 约束

- 美团外卖API需要企业资质，个人开发者难以获取，采用接口抽象层+模拟实现方案
- 高德Web服务API个人开发者可申请，有免费配额
- 保持CLI优先运行方式，预留Web接口扩展能力

## 架构

```
用户输入 → UnifiedAgent.process_input()
         → LLMNLU.parse() → intents数组
         → 逐个处理intent → handler响应拼接
                           ↓
              ┌────────────┴────────────┐
              │                         │
        CoffeeManager              NavManager
        (美团接口抽象层)           (高德真实API)
              │                         │
        CoffeeAPIClient            AmapClient
        (模拟/真实切换)            (高德Web服务API)
              │                         │
        本地JSON模拟              高德REST API
```

## 新增文件

| 文件 | 用途 |
|------|------|
| `config.py` | API Key配置管理（环境变量 > config.json > 默认值） |
| `modules/api_client.py` | 统一HTTP客户端基类（重试、超时、错误处理） |
| `modules/amap_client.py` | 高德API封装 |
| `modules/coffee_api_client.py` | 美团接口抽象层（模拟实现+真实接口预留） |

## 修改文件

| 文件 | 修改内容 |
|------|---------|
| `modules/nav_manager.py` | 重写，对接AmapClient |
| `modules/nav_data_manager.py` | 简化为本地缓存（收藏、车辆状态） |
| `modules/order_manager.py` | 重写，对接CoffeeAPIClient |
| `modules/data_manager.py` | 简化为本地缓存（偏好、历史） |
| `modules/nlu.py` | 更新SYSTEM_PROMPT，增加新意图和参数 |
| `agent.py` | 适配新Manager接口，增加配置加载 |

## 保留不变

| 文件 | 原因 |
|------|------|
| `modules/simulation.py` | 咖啡制作过程仍需模拟 |
| `modules/nav_simulation.py` | 导航过程播报保留，但ETA/距离来自真实API |
| `data/nav_favorites.json` | 家/公司/收藏仍本地存储 |
| `data/nav_vehicle_status.json` | 车辆状态本地管理 |
| `data/user_preferences.json` | 用户偏好本地存储 |
| `data/order_history.json` | 订单历史本地存储 |

## 高德API集成

### 使用的API

| API | 用途 | 替换当前功能 |
|-----|------|-------------|
| 地理编码/逆地理编码 | 地址↔经纬度转换 | 目的地解析 |
| 路径规划（驾车） | 路线规划、距离、耗时 | nav_routes.json 预置路线 |
| POI搜索 | 搜索兴趣点 | nav_pois.json 静态数据 |
| 沿途搜索 | 沿路线搜索加油站等 | search_along_route 模拟 |
| 路况查询 | 实时路况信息 | traffic_info 模拟 |

### AmapClient

```python
class AmapClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://restapi.amap.com/v3"

    async def geocode(self, address: str, city: str = None) -> dict
    async def reverse_geocode(self, location: str) -> dict
    async def driving_direction(self, origin: str, destination: str, waypoints: str = None) -> dict
    async def search_poi(self, keywords: str, city: str = None, location: str = None, radius: int = None) -> dict
    async def search_along_route(self, keywords: str, origin: str, destination: str) -> dict
    async def traffic_info(self, city: str, road_name: str = None) -> dict
```

### NavManager 重写

- `navigate()` → 调用 `geocode()` + `driving_direction()`，返回真实路线（含多条备选）
- `search_poi()` → 调用 `search_poi()`，返回附近POI
- `search_along_route()` → 调用 `search_along_route()`，沿路线搜索
- `traffic_info()` → 调用 `traffic_info()`，获取真实路况
- `nav_home()` / `nav_company()` → 用收藏坐标直接调路径规划
- `add_waypoint()` → 调用含途经点的路径规划
- `query_eta()` → 从路径规划结果提取ETA
- 本地保留：`nav_favorites.json`（地址+坐标）、`nav_vehicle_status.json`

### 城市配置

新增 `AMAP_CITY` 配置项，默认 "北京"，用于POI搜索和地理编码范围限定。

## 美团接口抽象层

### 接口协议

```python
class CoffeeAPIProtocol(Protocol):
    async def search_shops(self, keyword: str, location: str, radius: int) -> list[dict]
    async def get_shop_menu(self, shop_id: str) -> list[dict]
    async def create_order(self, shop_id: str, items: list, delivery_info: dict) -> dict
    async def get_order_status(self, order_id: str) -> dict
    async def cancel_order(self, order_id: str) -> dict
```

### 模拟实现（MockCoffeeAPI）

- 从 `coffee_shops.json` 读取数据，模拟API响应格式
- 订单创建返回模拟的order_id和状态
- 保持当前体验不变

### 真实实现（MeituanCoffeeAPI）

- 预留接口，后续接入美团外卖API后实现
- 需要：AppKey、AppSecret、签名机制

### 切换机制

- `config.py` 中 `COFFEE_API_MODE = "mock" | "meituan"`
- 工厂函数根据配置创建对应实现

### CoffeeManager 重写

- `order()` → 调用 `search_shops()` + `get_shop_menu()`
- 创建订单 → 调用 `create_order()`
- 确认/取消 → 调用 `get_order_status()` / `cancel_order()`
- 模拟数据来源迁移到 MockCoffeeAPI 内部
- 保留 `user_preferences.json`、`order_history.json` 本地缓存

## 配置管理

### Config 数据结构

```python
@dataclass
class Config:
    # 高德
    amap_api_key: str           # 必填，AMAP_API_KEY
    amap_city: str = "北京"      # 默认城市

    # 咖啡API
    coffee_api_mode: str = "mock"  # "mock" | "meituan"
    meituan_api_key: str = ""      # 美团Key（可选）

    # LLM
    ollama_model: str = "gemma4:e2b"
    ollama_base_url: str = "http://localhost:11434/api/chat"
    ollama_timeout: float = 520.0
```

### 优先级

环境变量 > config.json > 默认值

### API Key获取引导

首次运行检测到无Key时，打印申请指引：
- 高德：https://lbs.amap.com/ 注册→控制台→创建应用→获取Web服务Key
- 美团：https://open.meituan.com/ （后续需要时）

## 错误处理

| 场景 | 处理方式 |
|------|---------|
| 高德API调用失败 | 降级到本地缓存/预置数据，提示"服务暂时不可用" |
| 高德Key无效/过期 | 启动时检测，提示用户更新Key |
| 网络超时 | 重试1次，失败后降级 |
| 美团API（真实模式）失败 | 同高德降级逻辑 |
| Mock模式 | 永远不会网络失败，保持当前体验 |

### 本地缓存策略

- 导航结果缓存到本地，离线时可查上次的路线
- POI搜索结果缓存（TTL 30分钟）
- 收藏/偏好始终本地存储

## NLU适配

### 新增参数

- `navigate` 意图增加 `city` 参数（默认取配置城市）
- `search_poi` 增加 `radius` 参数（搜索半径）

### 新增意图

- `select_shop` — 咖啡场景，当搜索到多个店铺时用户选择
- `change_route` — 导航场景，切换推荐路线（高德返回多条路线）

### 对话流程变更

- 导航：`navigate` → 返回多条路线 → 用户 `change_route` 选择 → `confirm_nav`
- 咖啡：`order` → 搜索店铺 → 用户 `select_shop` → 选择饮品 → `confirm_order`

### 消歧逻辑更新

- `confirm` 需区分：确认店铺选择 / 确认订单 / 确认路线
- `cancel` 同理

### NavSimulation 调整

- 保留导航过程播报（"前方200米左转"等）
- ETA和距离来自真实API数据
- 导航完成判断基于真实距离和速度，而非固定延时
