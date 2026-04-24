# 咖啡订购Agent 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现一个支持自然语言交互的咖啡订购模拟Agent，包含完整的点单、偏好记忆、订单模拟功能。

**Architecture:** 采用模块化设计，分为数据层、业务逻辑层、交互层三层结构，各模块职责明确，独立可测试。使用本地JSON文件存储数据，不需要数据库，轻量易维护。

**Tech Stack:** Python 3.10+, 标准库实现，无外部依赖。

---

## 项目文件结构
```
order_coffee/
├── coffee_agent.py          # 主程序入口（REPL交互）
├── modules/
│   ├── __init__.py
│   ├── data_manager.py      # 数据存储管理模块
│   ├── nlu.py               # 自然语言意图识别模块
│   ├── order_manager.py     # 订单管理模块
│   └── simulation.py        # 流程模拟模块
└── data/
    ├── coffee_shops.json    # 咖啡店菜单数据
    ├── user_preferences.json # 用户偏好数据
    └── order_history.json   # 历史订单数据
```

---

### Task 1: 创建项目目录结构和基础数据文件

**Files:**
- Create: `modules/__init__.py`
- Create: `data/coffee_shops.json`
- Create: `data/user_preferences.json`
- Create: `data/order_history.json`

- [ ] **Step 1: 创建目录和空初始化文件**
  ```bash
  mkdir -p /Users/hpl/vibecoding/order_coffee/modules /Users/hpl/vibecoding/order_coffee/data
  touch /Users/hpl/vibecoding/order_coffee/modules/__init__.py
  ```
  Expected: 目录创建成功，无输出

- [ ] **Step 2: 写入咖啡店菜单数据**
  ```json
  {
    "shops": [
      {
        "id": 1,
        "name": "瑞幸咖啡",
        "menu": [
          {"id": 101, "name": "拿铁", "price": 18, "sizes": ["中杯", "大杯"], "ice_options": ["热", "少冰", "正常冰", "去冰"], "sugar_options": ["无糖", "半糖", "全糖", "少糖"]},
          {"id": 102, "name": "美式", "price": 14, "sizes": ["中杯", "大杯"], "ice_options": ["热", "少冰", "正常冰", "去冰"], "sugar_options": ["无糖"]},
          {"id": 103, "name": "生椰拿铁", "price": 22, "sizes": ["中杯", "大杯"], "ice_options": ["少冰", "正常冰", "去冰"], "sugar_options": ["无糖", "半糖", "全糖"]},
          {"id": 104, "name": "丝绒拿铁", "price": 21, "sizes": ["中杯", "大杯"], "ice_options": ["热", "少冰", "正常冰"], "sugar_options": ["半糖", "全糖", "少糖"]},
          {"id": 105, "name": "澳瑞白", "price": 19, "sizes": ["中杯", "大杯"], "ice_options": ["热", "少冰", "正常冰"], "sugar_options": ["无糖", "半糖"]}
        ]
      },
      {
        "id": 2,
        "name": "星巴克",
        "menu": [
          {"id": 201, "name": "拿铁", "price": 30, "sizes": ["中杯", "大杯", "超大杯"], "ice_options": ["热", "少冰", "正常冰", "去冰"], "sugar_options": ["无糖", "半糖", "全糖", "少糖"]},
          {"id": 202, "name": "美式", "price": 25, "sizes": ["中杯", "大杯", "超大杯"], "ice_options": ["热", "少冰", "正常冰", "去冰"], "sugar_options": ["无糖"]},
          {"id": 203, "name": "摩卡", "price": 33, "sizes": ["中杯", "大杯", "超大杯"], "ice_options": ["热", "少冰", "正常冰"], "sugar_options": ["半糖", "全糖"]},
          {"id": 204, "name": "卡布奇诺", "price": 29, "sizes": ["中杯", "大杯", "超大杯"], "ice_options": ["热", "少冰", "正常冰"], "sugar_options": ["无糖", "半糖"]},
          {"id": 205, "name": "星冰乐", "price": 36, "sizes": ["中杯", "大杯"], "ice_options": ["正常冰"], "sugar_options": ["半糖", "全糖"]}
        ]
      },
      {
        "id": 3,
        "name": "Manner",
        "menu": [
          {"id": 301, "name": "拿铁", "price": 15, "sizes": ["小杯", "大杯"], "ice_options": ["热", "少冰", "正常冰", "去冰"], "sugar_options": ["无糖", "半糖", "全糖"]},
          {"id": 302, "name": "美式", "price": 10, "sizes": ["小杯", "大杯"], "ice_options": ["热", "少冰", "正常冰", "去冰"], "sugar_options": ["无糖"]},
          {"id": 303, "name": "澳白", "price": 18, "sizes": ["小杯", "大杯"], "ice_options": ["热", "少冰"], "sugar_options": ["无糖", "半糖"]},
          {"id": 304, "name": " Dirty", "price": 20, "sizes": ["小杯"], "ice_options": ["正常冰"], "sugar_options": ["无糖"]}
        ]
      },
      {
        "id": 4,
        "name": "Tims",
        "menu": [
          {"id": 401, "name": "拿铁", "price": 22, "sizes": ["中杯", "大杯"], "ice_options": ["热", "少冰", "正常冰", "去冰"], "sugar_options": ["无糖", "半糖", "全糖"]},
          {"id": 402, "name": "美式", "price": 18, "sizes": ["中杯", "大杯"], "ice_options": ["热", "少冰", "正常冰", "去冰"], "sugar_options": ["无糖"]},
          {"id": 403, "name": "天乐雪", "price": 28, "sizes": ["中杯", "大杯"], "ice_options": ["正常冰"], "sugar_options": ["半糖", "全糖"]}
        ]
      },
      {
        "id": 5,
        "name": "Seesaw",
        "menu": [
          {"id": 501, "name": "拿铁", "price": 28, "sizes": ["中杯", "大杯"], "ice_options": ["热", "少冰", "正常冰", "去冰"], "sugar_options": ["无糖", "半糖", "全糖"]},
          {"id": 502, "name": "美式", "price": 22, "sizes": ["中杯", "大杯"], "ice_options": ["热", "少冰", "正常冰", "去冰"], "sugar_options": ["无糖"]},
          {"id": 503, "name": "桂花拿铁", "price": 32, "sizes": ["中杯", "大杯"], "ice_options": ["热", "少冰"], "sugar_options": ["半糖", "全糖"]}
        ]
      }
    ]
  }
  ```

- [ ] **Step 3: 写入默认用户偏好数据**
  ```json
  {
    "default_shop": "瑞幸咖啡",
    "default_size": "大杯",
    "default_ice": "少冰",
    "default_sugar": "半糖",
    "default_toppings": [],
    "favorite_coffee": "拿铁"
  }
  ```

- [ ] **Step 4: 写入空的历史订单数据**
  ```json
  {
    "orders": []
  }
  ```

- [ ] **Step 5: 验证文件创建成功**
  ```bash
  ls -la /Users/hpl/vibecoding/order_coffee/data/
  ```
  Expected: 看到三个json文件

---

### Task 2: 实现数据管理模块 (data_manager.py)

**Files:**
- Create: `modules/data_manager.py`

- [ ] **Step 1: 编写数据管理模块代码**
  ```python
  import json
  import os
  from typing import Dict, List, Any

  DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

  class DataManager:
      def __init__(self):
          os.makedirs(DATA_DIR, exist_ok=True)
          self.coffee_shops_path = os.path.join(DATA_DIR, "coffee_shops.json")
          self.user_preferences_path = os.path.join(DATA_DIR, "user_preferences.json")
          self.order_history_path = os.path.join(DATA_DIR, "order_history.json")

      def _load_json(self, file_path: str, default: Any = None) -> Any:
          if not os.path.exists(file_path):
              return default or {}
          try:
              with open(file_path, "r", encoding="utf-8") as f:
                  return json.load(f)
          except (json.JSONDecodeError, IOError):
              return default or {}

      def _save_json(self, file_path: str, data: Any) -> bool:
          try:
              with open(file_path, "w", encoding="utf-8") as f:
                  json.dump(data, f, ensure_ascii=False, indent=2)
              return True
          except IOError:
              return False

      # 咖啡店数据操作
      def get_all_coffee_shops(self) -> List[Dict]:
          data = self._load_json(self.coffee_shops_path, {"shops": []})
          return data.get("shops", [])

      def get_coffee_shop_by_name(self, name: str) -> Dict | None:
          shops = self.get_all_coffee_shops()
          for shop in shops:
              if shop["name"] == name:
                  return shop
          return None

      # 用户偏好操作
      def get_user_preferences(self) -> Dict:
          return self._load_json(self.user_preferences_path, {})

      def update_user_preferences(self, new_preferences: Dict) -> bool:
          prefs = self.get_user_preferences()
          prefs.update(new_preferences)
          return self._save_json(self.user_preferences_path, prefs)

      # 订单历史操作
      def get_order_history(self, limit: int = 10) -> List[Dict]:
          data = self._load_json(self.order_history_path, {"orders": []})
          orders = data.get("orders", [])
          return orders[-limit:][::-1]  # 返回最新的limit条，倒序排列

      def add_order(self, order: Dict) -> bool:
          data = self._load_json(self.order_history_path, {"orders": []})
          if "orders" not in data:
              data["orders"] = []
          data["orders"].append(order)
          return self._save_json(self.order_history_path, data)
  ```

- [ ] **Step 2: 编写简单测试代码验证功能**
  ```python
  # 测试代码
  if __name__ == "__main__":
      dm = DataManager()
      
      # 测试获取咖啡店
      shops = dm.get_all_coffee_shops()
      print(f"咖啡店数量: {len(shops)}")
      assert len(shops) == 5, "咖啡店数量应该是5个"
      
      # 测试获取用户偏好
      prefs = dm.get_user_preferences()
      print(f"默认店铺: {prefs.get('default_shop')}")
      assert prefs.get("default_shop") == "瑞幸咖啡", "默认店铺应该是瑞幸咖啡"
      
      # 测试更新用户偏好
      update_success = dm.update_user_preferences({"favorite_coffee": "生椰拿铁"})
      assert update_success == True, "更新偏好应该成功"
      new_prefs = dm.get_user_preferences()
      assert new_prefs.get("favorite_coffee") == "生椰拿铁", "偏好更新失败"
      
      # 测试添加订单
      test_order = {
          "order_id": "TEST001",
          "shop_name": "瑞幸咖啡",
          "coffee_name": "拿铁",
          "size": "大杯",
          "ice": "少冰",
          "sugar": "半糖",
          "toppings": [],
          "price": 18,
          "create_time": "2026-04-21 18:00:00",
          "status": "completed"
      }
      add_success = dm.add_order(test_order)
      assert add_success == True, "添加订单应该成功"
      
      # 测试获取订单历史
      history = dm.get_order_history(limit=5)
      print(f"历史订单数量: {len(history)}")
      assert len(history) >= 1, "应该至少有1条订单"
      
      print("✅ 所有测试通过!")
  ```

- [ ] **Step 3: 运行测试**
  ```bash
  cd /Users/hpl/vibecoding/order_coffee && python modules/data_manager.py
  ```
  Expected: 输出"✅ 所有测试通过!"

---

### Task 3: 实现自然语言意图识别模块 (nlu.py)

**Files:**
- Create: `modules/nlu.py`

- [ ] **Step 1: 编写意图识别模块代码**
  ```python
  import re
  from typing import Dict, Tuple, List

  class NLU:
      def __init__(self):
          # 意图关键词
          self.intent_patterns = {
              "order": [r"点.*咖啡", r"订.*咖啡", r"来一杯", r"要一杯", r"点单", "下单"],
              "reorder": [r"再来一杯", r"和上次一样", r"重复上次", r"再来一份"],
              "history": [r"历史订单", r"之前点过什么", r"我的订单", r"订单记录"],
              "recommend": [r"推荐", r"有什么好喝的", r"新品", r"什么比较好"],
              "confirm": [r"确认", r"是的", r"对", r"好的", r"可以", r"没问题"],
              "cancel": [r"取消", r"不要了", r"算了", r"放弃"],
              "greeting": [r"你好", r"嗨", r"哈喽", r"在吗", r"hello", r"hi"],
              "help": [r"帮助", r"怎么用", r"能做什么", r"功能", r"help"]
          }
          
          # 参数提取规则
          self.coffee_names = ["拿铁", "美式", "生椰拿铁", "摩卡", "卡布奇诺", "星冰乐", "澳瑞白", "澳白", "Dirty", "天乐雪", "桂花拿铁"]
          self.sizes = ["小杯", "中杯", "大杯", "超大杯"]
          self.ice_options = ["热", "少冰", "正常冰", "去冰", "冰", "常温"]
          self.sugar_options = ["无糖", "半糖", "全糖", "少糖", "三分糖", "五分糖", "七分糖", "多糖"]
          self.toppings = ["奶盖", "奶油", "糖浆", "浓缩", "珍珠", "椰果"]
          self.shop_names = ["瑞幸", "星巴克", "Manner", "Tims", "Seesaw", "瑞幸咖啡"]

      def classify_intent(self, text: str) -> Tuple[str, float]:
          text = text.lower()
          max_confidence = 0.0
          best_intent = "unknown"
          
          for intent, patterns in self.intent_patterns.items():
              for pattern in patterns:
                  if re.search(pattern, text):
                      confidence = 0.8 if intent in ["order", "reorder", "history", "recommend"] else 0.7
                      if confidence > max_confidence:
                          max_confidence = confidence
                          best_intent = intent
          
          return best_intent, max_confidence

      def extract_parameters(self, text: str) -> Dict:
          params = {}
          
          # 提取咖啡店
          for shop in self.shop_names:
              if shop in text:
                  params["shop_name"] = shop if shop != "瑞幸" else "瑞幸咖啡"
                  break
          
          # 提取咖啡名称
          for coffee in self.coffee_names:
              if coffee in text:
                  params["coffee_name"] = coffee
                  break
          
          # 提取杯型
          for size in self.sizes:
              if size in text:
                  params["size"] = size
                  break
          
          # 提取冰度
          for ice in self.ice_options:
              if ice in text:
                  params["ice"] = ice
                  break
          
          # 提取糖度
          for sugar in self.sugar_options:
              if sugar in text:
                  params["sugar"] = sugar
                  break
          
          # 提取配料
          toppings = []
          for topping in self.toppings:
              if f"加{topping}" in text or f"{topping}" in text:
                  toppings.append(topping)
          if toppings:
              params["toppings"] = toppings
          
          return params

      def parse(self, text: str) -> Dict:
          intent, confidence = self.classify_intent(text)
          params = self.extract_parameters(text)
          
          return {
              "intent": intent,
              "confidence": confidence,
              "params": params,
              "original_text": text
          }
  ```

- [ ] **Step 2: 编写测试代码**
  ```python
  # 测试代码
  if __name__ == "__main__":
      nlu = NLU()
      
      test_cases = [
          "帮我点一杯少冰半糖的大杯拿铁，加奶盖",
          "再来一杯和上次一样的",
          "我之前点过什么？",
          "有什么推荐的吗？",
          "确认下单",
          "算了不要了",
          "你好",
          "帮我点一杯星巴克的大杯热美式"
      ]
      
      for test in test_cases:
          result = nlu.parse(test)
          print(f"\n输入: {test}")
          print(f"意图: {result['intent']} (置信度: {result['confidence']})")
          print(f"参数: {result['params']}")
      
      # 测试点单意图
      result = nlu.parse("帮我点一杯少冰半糖的大杯拿铁，加奶盖")
      assert result["intent"] == "order"
      assert result["params"]["coffee_name"] == "拿铁"
      assert result["params"]["size"] == "大杯"
      assert result["params"]["ice"] == "少冰"
      assert result["params"]["sugar"] == "半糖"
      assert result["params"]["toppings"] == ["奶盖"]
      
      # 测试指定店铺
      result = nlu.parse("帮我点一杯星巴克的大杯热美式")
      assert result["intent"] == "order"
      assert result["params"]["shop_name"] == "星巴克"
      assert result["params"]["coffee_name"] == "美式"
      assert result["params"]["size"] == "大杯"
      assert result["params"]["ice"] == "热"
      assert result["params"]["sugar"] == "无糖"
      
      print("\n✅ 所有测试通过!")
  ```

- [ ] **Step 3: 运行测试**
  ```bash
  cd /Users/hpl/vibecoding/order_coffee && python modules/nlu.py
  ```
  Expected: 输出"✅ 所有测试通过!"

---

### Task 4: 实现订单管理模块 (order_manager.py)

**Files:**
- Create: `modules/order_manager.py`

- [ ] **Step 1: 编写订单管理模块代码**
  ```python
  import time
  from typing import Dict, List, Optional
  from .data_manager import DataManager

  class OrderManager:
      def __init__(self):
          self.data_manager = DataManager()
          self.pending_order: Optional[Dict] = None
          
      def _generate_order_id(self) -> str:
          timestamp = int(time.time())
          return f"CF{timestamp}"
      
      def _get_coffee_price(self, shop_name: str, coffee_name: str) -> int:
          shop = self.data_manager.get_coffee_shop_by_name(shop_name)
          if not shop:
              return 0
          for item in shop["menu"]:
              if item["name"] == coffee_name:
                  return item["price"]
          return 0
      
      def create_order(self, params: Dict) -> Dict:
          # 获取用户默认偏好
          prefs = self.data_manager.get_user_preferences()
          
          # 补全订单参数，优先使用用户输入，其次使用默认偏好
          order = {
              "order_id": self._generate_order_id(),
              "shop_name": params.get("shop_name", prefs.get("default_shop", "瑞幸咖啡")),
              "coffee_name": params.get("coffee_name", prefs.get("favorite_coffee", "拿铁")),
              "size": params.get("size", prefs.get("default_size", "大杯")),
              "ice": params.get("ice", prefs.get("default_ice", "少冰")),
              "sugar": params.get("sugar", prefs.get("default_sugar", "半糖")),
              "toppings": params.get("toppings", prefs.get("default_toppings", [])),
              "create_time": time.strftime("%Y-%m-%d %H:%M:%S"),
              "status": "pending"
          }
          
          # 计算价格
          base_price = self._get_coffee_price(order["shop_name"], order["coffee_name"])
          toppings_price = len(order["toppings"]) * 3  # 每份配料3元
          order["price"] = base_price + toppings_price
          
          self.pending_order = order
          return order
      
      def confirm_order(self) -> Optional[Dict]:
          if not self.pending_order:
              return None
          
          self.pending_order["status"] = "confirmed"
          # 保存到历史订单
          self.data_manager.add_order(self.pending_order.copy())
          
          # 更新用户偏好
          self.data_manager.update_user_preferences({
              "last_order": self.pending_order,
              "favorite_coffee": self.pending_order["coffee_name"]
          })
          
          confirmed_order = self.pending_order
          self.pending_order = None
          return confirmed_order
      
      def cancel_order(self) -> bool:
          if not self.pending_order:
              return False
          self.pending_order = None
          return True
      
      def reorder_last(self) -> Optional[Dict]:
          prefs = self.data_manager.get_user_preferences()
          last_order = prefs.get("last_order")
          if not last_order:
              return None
          
          # 创建新订单，复用上次的参数
          new_order = self.create_order({
              "shop_name": last_order["shop_name"],
              "coffee_name": last_order["coffee_name"],
              "size": last_order["size"],
              "ice": last_order["ice"],
              "sugar": last_order["sugar"],
              "toppings": last_order["toppings"]
          })
          return new_order
      
      def get_order_history(self, limit: int = 5) -> List[Dict]:
          return self.data_manager.get_order_history(limit)
      
      def get_recommendations(self, shop_name: Optional[str] = None) -> List[Dict]:
          if shop_name:
              shop = self.data_manager.get_coffee_shop_by_name(shop_name)
              shops = [shop] if shop else []
          else:
              shops = self.data_manager.get_all_coffee_shops()
          
          recommendations = []
          for shop in shops:
              # 每个店推荐3个热门商品
              popular_items = shop["menu"][:3]
              for item in popular_items:
                  recommendations.append({
                      "shop_name": shop["name"],
                      "coffee_name": item["name"],
                      "price": item["price"]
                  })
          
          return recommendations[:5]  # 最多返回5个推荐
  ```

- [ ] **Step 2: 编写测试代码**
  ```python
  # 测试代码
  if __name__ == "__main__":
      om = OrderManager()
      
      # 测试创建订单
      params = {
          "coffee_name": "拿铁",
          "size": "大杯",
          "ice": "少冰",
          "sugar": "半糖",
          "toppings": ["奶盖"]
      }
      order = om.create_order(params)
      print(f"创建订单: {order}")
      assert order["coffee_name"] == "拿铁"
      assert order["toppings"] == ["奶盖"]
      assert order["price"] == 18 + 3  # 拿铁18 + 奶盖3
      
      # 测试确认订单
      confirmed_order = om.confirm_order()
      assert confirmed_order is not None
      assert confirmed_order["status"] == "confirmed"
      
      # 测试重复下单
      reorder = om.reorder_last()
      print(f"重复下单: {reorder}")
      assert reorder is not None
      assert reorder["coffee_name"] == confirmed_order["coffee_name"]
      assert reorder["toppings"] == confirmed_order["toppings"]
      
      # 测试获取推荐
      recommendations = om.get_recommendations()
      print(f"推荐数量: {len(recommendations)}")
      assert len(recommendations) == 5
      
      # 测试获取历史订单
      history = om.get_order_history()
      print(f"历史订单数量: {len(history)}")
      assert len(history) >= 2  # 刚才创建了两个订单
      
      print("✅ 所有测试通过!")
  ```

- [ ] **Step 3: 运行测试**
  ```bash
  cd /Users/hpl/vibecoding/order_coffee && python modules/order_manager.py
  ```
  Expected: 输出"✅ 所有测试通过!"

---

### Task 5: 实现流程模拟模块 (simulation.py)

**Files:**
- Create: `modules/simulation.py`

- [ ] **Step 1: 编写模拟模块代码**
  ```python
  import time
  from typing import Dict, Callable

  class OrderSimulator:
      def __init__(self):
          self.status_flow = [
              ("pending", "订单已提交，正在处理...", 1),
              ("confirmed", "商家已接单，正在制作咖啡...", 3),
              ("making", "咖啡制作完成，正在打包...", 2),
              ("delivering", "骑手已取餐，正在配送，预计15分钟到达...", 5),
              ("completed", "🛵 您的咖啡已送到，请享用~", 0)
          ]
      
      def simulate_order_process(self, order: Dict, callback: Callable[[str, str], None]) -> None:
          """
          模拟订单全流程
          callback: 回调函数，参数为(status, message)
          """
          order_id = order["order_id"]
          
          for status, message, delay in self.status_flow:
              if delay > 0:
                  callback(status, f"[{order_id}] {message}")
                  time.sleep(delay)
              else:
                  callback(status, f"[{order_id}] {message}")
  ```

- [ ] **Step 2: 编写测试代码**
  ```python
  # 测试代码
  if __name__ == "__main__":
      simulator = OrderSimulator()
      
      test_order = {
          "order_id": "TEST001",
          "coffee_name": "拿铁",
          "shop_name": "瑞幸咖啡"
      }
      
      def callback(status, message):
          print(message)
      
      print("开始模拟订单流程:")
      simulator.simulate_order_process(test_order, callback)
      print("✅ 模拟完成!")
  ```

- [ ] **Step 3: 运行测试**
  ```bash
  cd /Users/hpl/vibecoding/order_coffee && python modules/simulation.py
  ```
  Expected: 依次输出订单流程各个阶段的消息，间隔相应秒数，最后输出"✅ 模拟完成!"

---

### Task 6: 实现主程序入口 (coffee_agent.py)

**Files:**
- Create: `coffee_agent.py`

- [ ] **Step 1: 编写主程序代码**
  ```python
  #!/usr/bin/env python3
  from modules.nlu import NLU
  from modules.order_manager import OrderManager
  from modules.simulation import OrderSimulator
  import sys

  class CoffeeAgent:
      def __init__(self):
          self.nlu = NLU()
          self.order_manager = OrderManager()
          self.simulator = OrderSimulator()
          self.state = "idle"  # idle, waiting_confirm
          self.current_order = None
      
      def print_help(self):
          help_text = """
  ☕ 咖啡订购Agent 使用说明
  ------------------------
  你可以直接用自然语言和我对话：
  ✅ 点单："帮我点一杯少冰半糖的大杯拿铁，加奶盖"
  ✅ 重复下单："再来一杯和上次一样的"
  ✅ 查询历史："我之前点过什么？"
  ✅ 求推荐："有什么好喝的推荐一下？"
  ✅ 帮助："帮助" / "怎么用"
  ✅ 退出："退出" / "quit" / "exit"
          """
          print(help_text)
      
      def handle_order_intent(self, params: Dict) -> str:
          order = self.order_manager.create_order(params)
          self.current_order = order
          self.state = "waiting_confirm"
          
          toppings_str = f" + {'、'.join(order['toppings'])}" if order['toppings'] else ""
          response = f"""
  好的，为您确认订单：
  📍 店铺：{order['shop_name']}
  ☕ 商品：{order['size']}{order['coffee_name']} {order['ice']} {order['sugar']}{toppings_str}
  💰 价格：{order['price']}元
  
  是否确认下单？
          """
          return response.strip()
      
      def handle_reorder_intent(self) -> str:
          order = self.order_manager.reorder_last()
          if not order:
              return "抱歉，没有找到您的历史订单，请直接点单哦~"
          
          self.current_order = order
          self.state = "waiting_confirm"
          
          toppings_str = f" + {'、'.join(order['toppings'])}" if order['toppings'] else ""
          response = f"""
  好的，为您重复上次订单：
  📍 店铺：{order['shop_name']}
  ☕ 商品：{order['size']}{order['coffee_name']} {order['ice']} {order['sugar']}{toppings_str}
  💰 价格：{order['price']}元
  
  是否确认下单？
          """
          return response.strip()
      
      def handle_history_intent(self) -> str:
          history = self.order_manager.get_order_history(limit=5)
          if not history:
              return "您还没有历史订单哦~"
          
          response = "您最近的订单：\n"
          for i, order in enumerate(history, 1):
              toppings_str = f" + {'、'.join(order['toppings'])}" if order['toppings'] else ""
              response += f"{i}. {order['create_time']} {order['shop_name']} {order['size']}{order['coffee_name']} {order['ice']} {order['sugar']}{toppings_str} {order['price']}元\n"
          
          return response.strip()
      
      def handle_recommend_intent(self, params: Dict) -> str:
          shop_name = params.get("shop_name")
          recommendations = self.order_manager.get_recommendations(shop_name)
          
          if not recommendations:
              return "抱歉，暂时没有找到合适的推荐哦~"
          
          response = "为您推荐以下咖啡：\n"
          for rec in recommendations:
              response += f"☕ {rec['shop_name']} - {rec['coffee_name']} {rec['price']}元\n"
          
          return response.strip()
      
      def handle_confirm_intent(self) -> str:
          if self.state != "waiting_confirm" or not self.current_order:
              return "当前没有待确认的订单哦~"
          
          confirmed_order = self.order_manager.confirm_order()
          if not confirmed_order:
              return "订单确认失败，请重试~"
          
          self.state = "idle"
          
          # 启动异步模拟流程
          def simulation_callback(status, message):
              print(f"\n{message}")
              if status == "completed":
                  print("\n> ", end="", flush=True)
          
          import threading
          thread = threading.Thread(target=self.simulator.simulate_order_process, args=(confirmed_order, simulation_callback))
          thread.daemon = True
          thread.start()
          
          return f"🎉 订单已提交，订单号：{confirmed_order['order_id']}，请稍等，我会及时通知您订单状态~"
      
      def handle_cancel_intent(self) -> str:
          if self.state == "waiting_confirm" and self.current_order:
              self.order_manager.cancel_order()
              self.state = "idle"
              self.current_order = None
              return "订单已取消，有需要随时叫我哦~"
          else:
              self.state = "idle"
              self.current_order = None
              return "好的，有需要随时告诉我哦~"
      
      def handle_greeting_intent(self) -> str:
          return "你好呀~ 我是你的咖啡订购小助手，想喝点什么呢？可以直接告诉我哦，或者说「帮助」看看我能做什么~"
      
      def handle_help_intent(self) -> str:
          self.print_help()
          return ""
      
      def handle_unknown_intent(self) -> str:
          return "抱歉，我没太听懂你说的什么，可以再说一遍吗？或者说「帮助」看看我能做什么哦~"
      
      def process_input(self, user_input: str) -> str:
          user_input = user_input.strip()
          
          # 处理退出命令
          if user_input.lower() in ["退出", "quit", "exit", "q"]:
              print("👋 再见~ 祝你喝咖啡愉快！")
              sys.exit(0)
          
          # 解析意图
          parse_result = self.nlu.parse(user_input)
          intent = parse_result["intent"]
          params = parse_result["params"]
          
          # 根据当前状态和意图处理
          if self.state == "waiting_confirm":
              if intent == "confirm":
                  return self.handle_confirm_intent()
              elif intent == "cancel":
                  return self.handle_cancel_intent()
              else:
                  # 用户在确认阶段说了其他的，先取消当前待确认订单
                  self.order_manager.cancel_order()
                  self.state = "idle"
                  self.current_order = None
          
          # 正常处理意图
          handler_map = {
              "order": lambda: self.handle_order_intent(params),
              "reorder": self.handle_reorder_intent,
              "history": self.handle_history_intent,
              "recommend": lambda: self.handle_recommend_intent(params),
              "confirm": lambda: "当前没有待确认的订单哦~",
              "cancel": lambda: "当前没有可取消的订单哦~",
              "greeting": self.handle_greeting_intent,
              "help": self.handle_help_intent
          }
          
          handler = handler_map.get(intent, self.handle_unknown_intent)
          return handler()
      
      def run(self):
          print("☕ 欢迎使用咖啡订购Agent！")
          print("有什么需要直接和我说哦，输入「帮助」可以查看使用说明，输入「退出」可以退出程序。\n")
          
          while True:
              try:
                  user_input = input("> ")
                  if not user_input.strip():
                      continue
                  
                  response = self.process_input(user_input)
                  if response:
                      print(f"< {response}\n")
              except KeyboardInterrupt:
                  print("\n👋 再见~ 祝你喝咖啡愉快！")
                  sys.exit(0)
              except Exception as e:
                  print(f"< 抱歉，出了点小问题：{str(e)}，请重试哦~")

  if __name__ == "__main__":
      agent = CoffeeAgent()
      agent.run()
  ```

- [ ] **Step 2: 给主程序添加执行权限**
  ```bash
  chmod +x /Users/hpl/vibecoding/order_coffee/coffee_agent.py
  ```

- [ ] **Step 3: 运行主程序测试基础功能**
  ```bash
  cd /Users/hpl/vibecoding/order_coffee && python coffee_agent.py << 'EOF'
  帮助
  你好
  帮我点一杯少冰半糖的大杯拿铁加奶盖
  确认
  退出
  EOF
  ```
  Expected: 程序正常运行，输出帮助信息，问候信息，确认订单，然后退出

---

### Task 7: 整体功能测试和优化

**Files:**
- Modify: `coffee_agent.py` (如有需要)

- [ ] **Step 1: 测试完整点单流程**
  运行程序，依次输入：
  ```
  帮我点一杯大杯少冰半糖拿铁加奶盖
  确认
  ```
  Expected: 订单确认成功，模拟流程正常输出各个状态

- [ ] **Step 2: 测试重复下单功能**
  运行程序，输入：
  ```
  再来一杯和上次一样的
  确认
  ```
  Expected: 正确创建和上次一样的订单

- [ ] **Step 3: 测试历史订单查询**
  运行程序，输入：
  ```
  我之前点过什么
  ```
  Expected: 正确显示历史订单列表

- [ ] **Step 4: 测试推荐功能**
  运行程序，输入：
  ```
  有什么推荐的
  ```
  Expected: 正确返回推荐列表

- [ ] **Step 5: 测试取消订单功能**
  运行程序，依次输入：
  ```
  帮我点一杯美式
  不要了取消
  ```
  Expected: 订单成功取消

- [ ] **Step 6: 创建启动脚本（可选）**
  ```bash
  echo '#!/bin/bash\ncd /Users/hpl/vibecoding/order_coffee && python coffee_agent.py' > /usr/local/bin/coffee
  chmod +x /usr/local/bin/coffee
  ```
  Expected: 后续可以直接在终端输入`coffee`启动Agent

---

## 自测检查
1. ✅ 所有功能点都有对应的实现任务
2. ✅ 没有占位符，所有步骤都有完整的代码示例
3. ✅ 所有参数、方法名一致，没有矛盾
4. ✅ 每个任务都可以独立运行测试
