#!/usr/bin/env python3
import json
import sys
from typing import Dict
from modules.nlu import LLMNLU
from modules.order_manager import OrderManager
from modules.simulation import OrderSimulator
from modules.nav_manager import NavigationManager
from modules.nav_simulation import NavigationSimulator


class UnifiedAgent:
    def __init__(self):
        # NLU（共享）
        self.nlu = LLMNLU()

        # 咖啡场景
        self.order_manager = OrderManager()
        self.order_simulator = OrderSimulator()
        self.coffee_state = "idle"
        self.current_order = None

        # 导航场景
        self.nav_manager = NavigationManager()
        self.nav_simulator = NavigationSimulator()

        # 共享
        self.conversation_history = []

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

    def handle_nav_favorite_intent(self, params: Dict) -> str:
        result = self.nav_manager.navigate_favorite(params)
        return result.get("response", "")

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
        coffee_intents = {"order", "reorder", "history", "recommend", "confirm_order", "cancel_order"}
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
                                "nav_company", "nav_favorite", "search_poi", "vehicle_status",
                                "query_eta", "traffic_info", "avoid_route", "add_waypoint",
                                "search_along_route", "greeting", "help"):
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
            "nav_favorite": lambda: self.handle_nav_favorite_intent(params),
            "select_destination": lambda: self.handle_select_destination_intent(params),
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
    agent = UnifiedAgent()
    agent.run()
