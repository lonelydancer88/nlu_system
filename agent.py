#!/usr/bin/env python3
import json
import sys
from typing import Dict, List
from modules.nlu import LLMNLU
from modules.order_manager import OrderManager
from modules.simulation import OrderSimulator
from modules.nav_manager import NavigationManager
from modules.nav_simulation import NavigationSimulator
from modules.amap_client import AmapClient
from modules.coffee_api_client import create_coffee_api
try:
    from config import Config
except ImportError:
    Config = None


class UnifiedAgent:
    def __init__(self, config=None):
        self.config = config

        # NLU（共享）- 云端优先，本地ollama降级
        self.nlu = LLMNLU(
            # 本地ollama降级配置
            model=config.ollama_model if config else "gemma4:e2b",
            base_url=config.ollama_base_url if config else "http://localhost:11434/api/chat",
            timeout=config.ollama_timeout if config else 120.0,
            enable_fallback=False,
            # 云端LLM配置（优先）
            llm_provider=config.llm_provider if config else "dashscope",
            llm_api_key=config.llm_api_key if config else "",
            llm_model=config.llm_model if config else "glm-5",
            llm_base_url=config.llm_base_url if config else "https://dashscope.aliyuncs.com/compatible-mode/v1",
            llm_timeout=config.llm_timeout if config else 60.0,
        )

        # 咖啡场景
        coffee_api = create_coffee_api(
            mode=config.coffee_api_mode if config else "mock",
            api_key=config.meituan_api_key if config else ""
        )
        self.order_manager = OrderManager(coffee_api=coffee_api)
        self.order_simulator = OrderSimulator()
        self.coffee_state = "idle"
        self.current_order = None
        self.pending_shops = []  # 存储咖啡店搜索结果
        self.pending_poi_recommendations = []  # 存储LLM推荐的POI列表

        # 导航场景
        amap_client = None
        if config and config.amap_api_key:
            amap_client = AmapClient(api_key=config.amap_api_key)
        self.nav_manager = NavigationManager(
            amap_client=amap_client,
            city=config.amap_city if config else "北京"
        )
        self.nav_simulator = NavigationSimulator()

        # 共享
        self.conversation_history = []

    @staticmethod
    def _create_coffee_api(mode: str, api_key: str = ""):
        return create_coffee_api(mode=mode, api_key=api_key)

    def print_help(self):
        help_text = """
🚗☕ 车载智能助手 使用说明
------------------------
你可以直接用自然语言和我对话：

☕ 咖啡订购：
  "帮我点一杯少冰半糖的大杯拿铁，加奶盖"
  "再来一杯和上次一样的"
  "我之前点过什么？"
  "有什么好喝的推荐一下？"

🚗 车载导航：
  "导航去中关村" / "开车去三里屯"
  "回家" / "去公司"
  "附近找个加油站" / "沿途找个餐厅"
  "避开收费路段" / "不走高速"
  "还有多久到" / "路况怎么样"
  "还有多少油" / "续航还有多远"
  "加个途经点xxx"

🔧 通用：
  "帮助" / "怎么用"
  "退出" / "quit" / "exit"
        """
        print(help_text)

    # ========== 咖啡场景 handlers ==========

    def handle_order_intent(self, params: Dict) -> str:
        if not params.get("coffee_name"):
            return "请问您想喝什么咖啡呢？比如拿铁、美式、生椰拿铁等~"

        order = self.order_manager.create_order(params)
        self.current_order = order
        self.coffee_state = "waiting_confirm"

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
        self.coffee_state = "waiting_confirm"

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

    def handle_confirm_order_intent(self) -> str:
        if self.coffee_state != "waiting_confirm" or not self.current_order:
            return "当前没有待确认的订单哦~"

        confirmed_order = self.order_manager.confirm_order()
        if not confirmed_order:
            return "订单确认失败，请重试~"

        self.coffee_state = "idle"

        def simulation_callback(status, message):
            print(f"\n{message}")
            if status == "completed":
                print("\n> ", end="", flush=True)

        import threading
        thread = threading.Thread(target=self.order_simulator.simulate_order_process, args=(confirmed_order, simulation_callback))
        thread.daemon = True
        thread.start()

        return f"🎉 订单已提交，订单号：{confirmed_order['order_id']}，请稍等，我会及时通知您订单状态~"

    def handle_cancel_order_intent(self) -> str:
        if self.coffee_state == "waiting_confirm" and self.current_order:
            self.order_manager.cancel_order()
            self.coffee_state = "idle"
            self.current_order = None
            return "订单已取消，有需要随时叫我哦~"
        else:
            self.coffee_state = "idle"
            self.current_order = None
            return "好的，有需要随时告诉我哦~"

    def handle_greeting_intent(self) -> str:
        return "你好呀~ 我是你的车载智能助手，可以帮你点咖啡，也可以帮你导航。直接告诉我你想做什么吧~"

    def handle_help_intent(self) -> str:
        self.print_help()
        return ""

    def handle_unknown_intent(self) -> str:
        return "抱歉，我没太听懂你说的什么，可以再说一遍吗？或者说「帮助」看看我能做什么哦~"

    # ========== 导航场景 handlers ==========

    def handle_navigate_intent(self, params: Dict) -> str:
        result = self.nav_manager.plan_route(params)
        return result.get("response", "")

    def handle_select_destination_intent(self, params: Dict) -> str:
        # 如果有待选择的POI推荐（来自LLM推荐），优先处理
        if self.pending_poi_recommendations:
            selection = params.get("selection", 1)
            # 支持按编号或名称选择
            try:
                idx = int(selection) - 1
                if idx < 0 or idx >= len(self.pending_poi_recommendations):
                    return f"请选择1-{len(self.pending_poi_recommendations)}之间的编号~"
                poi = self.pending_poi_recommendations[idx]
            except (ValueError, TypeError):
                # 按名称匹配
                poi = None
                for p in self.pending_poi_recommendations:
                    if str(selection) in p.get("name", ""):
                        poi = p
                        break
                if not poi:
                    return f"未找到「{selection}」，请选择编号或名称~"

            poi_name = poi.get("name", "")
            self.pending_poi_recommendations = []

            # 调用高德API搜索该POI的具体位置
            if self.nav_manager.amap:
                pois = self.nav_manager.amap.search_poi(poi_name, city=self.nav_manager.city)
                if pois:
                    first_poi = pois[0]
                    location = first_poi.get("location", "")
                    if location:
                        # 使用高德返回的位置直接规划导航
                        origin = self.nav_manager._origin_location or "116.470,39.985"
                        driving_result = self.nav_manager.amap.driving_direction(origin, location)
                        if driving_result.get("status") == "1":
                            route = self.nav_manager.amap.format_route(driving_result, destination_name=poi_name)
                            if route:
                                route["id"] = self.nav_manager._generate_route_id()
                                route["to"] = poi_name
                                route["to_address"] = first_poi.get("address", "")
                                self.nav_manager.current_route = route
                                self.nav_manager.nav_state = "planning"
                                return self.nav_manager._format_route_response(route).get("response", "")
                return f"抱歉，未能找到「{poi_name}」的具体位置，请尝试其他地点~"
            else:
                # 无高德API，使用地理编码
                geocode_result = self.nav_manager.amap.geocode(poi_name, city=self.nav_manager.city) if self.nav_manager.amap else None
                if geocode_result and geocode_result.get("status") == "1" and geocode_result.get("geocodes"):
                    location = geocode_result["geocodes"][0].get("location", "")
                    if location:
                        origin = self.nav_manager._origin_location or "116.470,39.985"
                        driving_result = self.nav_manager.amap.driving_direction(origin, location)
                        if driving_result.get("status") == "1":
                            route = self.nav_manager.amap.format_route(driving_result, destination_name=poi_name)
                            if route:
                                route["id"] = self.nav_manager._generate_route_id()
                                route["to"] = poi_name
                                self.nav_manager.current_route = route
                                self.nav_manager.nav_state = "planning"
                                return self.nav_manager._format_route_response(route).get("response", "")
                return f"抱歉，未能找到「{poi_name}」的位置，请尝试其他地点~"

        # 原有的pending_destinations处理
        result = self.nav_manager.select_destination(params)
        return result.get("response", "")

    def handle_confirm_nav_intent(self) -> str:
        result = self.nav_manager.confirm_navigation()
        response = result.get("response", "")

        if result.get("start_simulation"):
            def nav_simulation_callback(status, message):
                print(f"\n{message}")
                if status == "arrived":
                    print("\n> ", end="", flush=True)

            import threading
            thread = threading.Thread(
                target=self.nav_simulator.simulate_navigation,
                args=(self.nav_manager.current_route, self.nav_manager.navigation_session, nav_simulation_callback)
            )
            thread.daemon = True
            thread.start()

        return response

    def handle_cancel_nav_intent(self) -> str:
        result = self.nav_manager.cancel_navigation()
        return result.get("response", "")

    def handle_add_waypoint_intent(self, params: Dict) -> str:
        result = self.nav_manager.add_waypoint(params)
        return result.get("response", "")

    def handle_search_poi_intent(self, params: Dict) -> str:
        result = self.nav_manager.search_poi(params)
        # 存储POI列表供后续选择
        if "pois" in result:
            self.pending_shops = result["pois"]
        return result.get("response", "")

    def handle_search_along_route_intent(self, params: Dict) -> str:
        result = self.nav_manager.search_along_route(params)
        return result.get("response", "")

    def handle_traffic_info_intent(self, params: Dict) -> str:
        result = self.nav_manager.get_traffic_info(params)
        return result.get("response", "")

    def handle_avoid_route_intent(self, params: Dict) -> str:
        result = self.nav_manager.avoid_route(params)
        return result.get("response", "")

    def handle_query_eta_intent(self) -> str:
        result = self.nav_manager.query_eta()
        return result.get("response", "")

    def handle_vehicle_status_intent(self) -> str:
        result = self.nav_manager.get_vehicle_status()
        return result.get("response", "")

    def handle_nav_home_intent(self) -> str:
        result = self.nav_manager.navigate_home()
        return result.get("response", "")

    def handle_nav_company_intent(self) -> str:
        result = self.nav_manager.navigate_company()
        return result.get("response", "")

    def handle_query_home_intent(self) -> str:
        home = self.nav_manager.data_manager.get_home()
        if not home:
            return "您还没有设置家的地址哦~"
        address = home.get("address", "")
        return f"您的家在：{address}"

    def handle_query_company_intent(self) -> str:
        company = self.nav_manager.data_manager.get_company()
        if not company:
            return "您还没有设置公司的地址哦~"
        address = company.get("address", "")
        return f"您的公司在：{address}"

    def handle_recommend_poi_intent(self, params: Dict, poi_list: List[Dict], parse_result: Dict) -> str:
        """用户请求推荐某类地点，由LLM返回POI列表"""
        if not poi_list:
            return "抱歉，暂无推荐，请换个关键词试试~"

        self.pending_poi_recommendations = poi_list

        response = "为您推荐以下地点：\n"
        for i, poi in enumerate(poi_list, 1):
            reason = poi.get("reason", "")
            response += f"{i}. {poi['name']}"
            if reason:
                response += f" - {reason}"
            response += "\n"
        response += "\n请选择您想去的地方（说编号或名称）~"
        return response.strip()

    def handle_nav_favorite_intent(self, params: Dict) -> str:
        result = self.nav_manager.navigate_favorite(params)
        return result.get("response", "")

    def handle_select_shop_intent(self, params: Dict) -> str:
        """用户从咖啡店搜索结果中选择店铺"""
        if not self.pending_shops:
            return "请先搜索附近的咖啡店~"
        selection = int(params.get("selection", 1))
        if selection < 1 or selection > len(self.pending_shops):
            return f"请选择1-{len(self.pending_shops)}之间的编号~"
        shop = self.pending_shops[selection - 1]
        self.pending_shops = []  # 清除待选列表
        return f"您选择了「{shop['name']}」，请告诉我您想喝什么咖啡~"

    def handle_change_route_intent(self, params: Dict) -> str:
        """用户想切换到另一条推荐路线"""
        if self.nav_manager.nav_state != "planning":
            return "当前没有可切换的路线哦~"
        route_index = params.get("route_index", 1)
        return f"已为您切换到第{route_index}条路线，路线已更新。是否开始导航？"

    # ========== 统一调度 ==========

    def _resolve_ambiguous_intent(self, intent: str) -> str:
        """处理RuleNLU无法区分的confirm/cancel：根据Agent状态判断归属场景"""
        if intent == "confirm_order" and self.coffee_state != "waiting_confirm":
            if self.nav_manager.nav_state == "planning":
                return "confirm_nav"
        elif intent == "confirm_nav" and self.nav_manager.nav_state != "planning":
            if self.coffee_state == "waiting_confirm":
                return "confirm_order"
        elif intent == "cancel_order" and self.coffee_state != "waiting_confirm":
            if self.nav_manager.nav_state in ("planning", "navigating"):
                return "cancel_nav"
        elif intent == "cancel_nav" and self.nav_manager.nav_state == "idle":
            if self.coffee_state == "waiting_confirm":
                return "cancel_order"
        return intent

    def _process_single_intent(self, intent: str, params: Dict, parse_result: Dict) -> str:
        """处理单个意图，返回response字符串"""
        # 咖啡场景澄清（仅咖啡场景意图时才追问咖啡槽位）
        coffee_intents = {"order", "reorder", "history", "recommend", "confirm_order", "cancel_order", "select_shop"}
        if parse_result.get("needs_clarification") and parse_result.get("clarification_question"):
            if intent in coffee_intents:
                return parse_result["clarification_question"]

        # 咖啡场景：缺少coffee_name时澄清
        if intent == "order" and not params.get("coffee_name"):
            return "请问您想喝什么咖啡呢？比如拿铁、美式、生椰拿铁等~"

        # 解析歧义的confirm/cancel
        intent = self._resolve_ambiguous_intent(intent)

        # 咖啡场景：waiting_confirm状态下的意图处理
        if self.coffee_state == "waiting_confirm":
            if intent == "confirm_order":
                return self.handle_confirm_order_intent()
            elif intent == "cancel_order":
                return self.handle_cancel_order_intent()
            elif intent not in ("navigate", "confirm_nav", "cancel_nav", "nav_home",
                                "nav_company", "query_home", "query_company", "recommend_poi",
                                "search_poi", "vehicle_status", "query_eta", "traffic_info",
                                "avoid_route", "add_waypoint", "search_along_route",
                                "greeting", "help"):
                # 非导航意图且非confirm/cancel，取消当前咖啡订单
                self.order_manager.cancel_order()
                self.coffee_state = "idle"
                self.current_order = None

        # Handler map
        handler_map = {
            # 咖啡
            "order": lambda: self.handle_order_intent(params),
            "reorder": self.handle_reorder_intent,
            "history": self.handle_history_intent,
            "recommend": lambda: self.handle_recommend_intent(params),
            "confirm_order": self.handle_confirm_order_intent,
            "cancel_order": self.handle_cancel_order_intent,
            "select_shop": lambda: self.handle_select_shop_intent(params),
            # 导航
            "navigate": lambda: self.handle_navigate_intent(params),
            "confirm_nav": self.handle_confirm_nav_intent,
            "cancel_nav": self.handle_cancel_nav_intent,
            "add_waypoint": lambda: self.handle_add_waypoint_intent(params),
            "search_poi": lambda: self.handle_search_poi_intent(params),
            "search_along_route": lambda: self.handle_search_along_route_intent(params),
            "traffic_info": lambda: self.handle_traffic_info_intent(params),
            "avoid_route": lambda: self.handle_avoid_route_intent(params),
            "query_eta": self.handle_query_eta_intent,
            "vehicle_status": self.handle_vehicle_status_intent,
            "nav_home": self.handle_nav_home_intent,
            "nav_company": self.handle_nav_company_intent,
            "query_home": self.handle_query_home_intent,
            "query_company": self.handle_query_company_intent,
            "recommend_poi": lambda: self.handle_recommend_poi_intent(params, parse_result.get("poi_list"), parse_result),
            "nav_favorite": lambda: self.handle_nav_favorite_intent(params),
            "select_destination": lambda: self.handle_select_destination_intent(params),
            "change_route": lambda: self.handle_change_route_intent(params),
            # 通用
            "greeting": self.handle_greeting_intent,
            "help": self.handle_help_intent
        }

        handler = handler_map.get(intent, self.handle_unknown_intent)
        return handler()

    def process_input(self, user_input: str) -> Dict:
        user_input = user_input.strip()

        if user_input.lower() in ["退出", "quit", "exit", "q"]:
            print("👋 再见~ 祝你一路顺风！")
            sys.exit(0)

        if user_input.lower() in ["/clear", "clear", "清空上下文", "清空对话"]:
            self._clear_context()
            return {"response": "上下文已清空，有什么可以帮你的吗？", "debug": {"nlu": {"intents": [{"intent": "clear_context", "params": {}}]}}}

        parse_result = self.nlu.parse(user_input, history=self.conversation_history)
        intents = parse_result.get("intents", [{}])

        # 逐个处理意图，拼接响应
        responses = []
        for intent_item in intents:
            intent = intent_item.get("intent", "unknown")
            params = intent_item.get("params", {})
            response = self._process_single_intent(intent, params, parse_result)
            if response:
                responses.append(response)

        return {
            "response": "\n".join(responses) if responses else "",
            "debug": {"nlu": parse_result}
        }

    def _add_to_history(self, role: str, content: str):
        """记录对话历史，最多保留最近10轮"""
        self.conversation_history.append({"role": role, "content": content})
        if len(self.conversation_history) > 10:
            self.conversation_history = self.conversation_history[-10:]

    def _clear_context(self):
        """清空对话上下文"""
        self.conversation_history = []
        self.coffee_state = "idle"
        self.current_order = None
        self.pending_shops = []
        self.pending_poi_recommendations = []
        self.nav_manager.nav_state = "idle"
        self.nav_manager.current_route = None
        self.nav_manager.pending_destinations = None
        self.nav_manager.navigation_session = None

    def run(self):
        print("🚗☕ 欢迎使用车载智能助手！")
        print("我可以帮你点咖啡，也可以帮你导航。直接告诉我你想做什么吧~")
        print("输入「帮助」查看使用说明，输入「退出」退出程序。\n")

        while True:
            try:
                user_input = input("> ")
                if not user_input.strip():
                    continue

                result = self.process_input(user_input)
                response = result["response"]
                debug = result["debug"]

                if response:
                    print(f"< {response}")
                    print(f"[debug] {json.dumps(debug, ensure_ascii=False)}\n")
                    self._add_to_history("user", user_input)
                    self._add_to_history("assistant", response)
            except KeyboardInterrupt:
                print("\n👋 再见~ 祝你一路顺风！")
                sys.exit(0)
            except Exception as e:
                print(f"< 抱歉，出了点小问题：{str(e)}，请重试哦~")


if __name__ == "__main__":
    agent = UnifiedAgent(Config())
    agent.run()
