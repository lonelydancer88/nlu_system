import json
import re
import time
from typing import Dict, List, Tuple, Optional
import urllib.request
import urllib.error


SYSTEM_PROMPT = """你是车载智能助手的意图理解模块。你同时处理咖啡订购和车载导航两个场景，任务是分析用户输入，识别意图并提取参数。

## 咖啡场景意图：
- order: 用户想要点单/订购咖啡
- reorder: 用户想要重复上次的订单
- history: 用户想要查看历史订单
- recommend: 用户想要获得推荐
- confirm_order: 用户确认咖啡下单（在咖啡下单确认场景中的"确认/对/好的/可以"）
- cancel_order: 用户取消咖啡订单
- select_shop: 用户从搜索结果中选择某个咖啡店

## 导航场景意图：
- navigate: 用户要导航去某地
- confirm_nav: 用户确认开始导航（在路线确认场景中的"确认/对/好的/开始吧"）
- cancel_nav: 用户取消导航
- add_waypoint: 用户要在当前路线添加途经点
- search_poi: 用户要搜索附近地点（加油站、餐厅、停车场等）
- search_along_route: 用户要沿当前路线搜索地点
- traffic_info: 用户要查询路况
- avoid_route: 用户要避开某类路线（收费/拥堵/高速）
- query_eta: 用户要查询预计到达时间
- vehicle_status: 用户要查看车辆状态（油量/电量）
- nav_home: 用户要导航回家
- nav_company: 用户要导航去公司
- query_home: 用户询问家的地址（如"我的家在哪"、"家在哪儿"）
- query_company: 用户询问公司的地址（如"我的公司在哪"、"公司在哪儿"）
- nav_favorite: 用户要导航到收藏地点
- select_destination: 用户从多个候选目的地中选择某一个
- recommend_poi: 用户请求推荐某类地点（如情侣约会、朋友聚餐、周末游玩等），返回POI列表供选择后导航
- change_route: 用户想切换推荐路线（当有多条路线可选时）

## 通用意图：
- greeting: 用户打招呼
- help: 用户请求帮助
- unknown: 无法识别

## 咖啡场景可提取参数：
- shop_name: 咖啡店名称（瑞幸咖啡、星巴克、Manner、Tims、Seesaw）
- coffee_name: 咖啡名称（拿铁、美式、生椰拿铁、摩卡、卡布奇诺、星冰乐、澳瑞白、澳白、Dirty、天乐雪、桂花拿铁）
- size: 杯型（小杯、中杯、大杯、超大杯）
- ice: 冰度（热、少冰、正常冰、去冰、常温）
- sugar: 糖度（无糖、半糖、全糖、少糖、三分糖、五分糖、七分糖、多糖）
- toppings: 配料列表（奶盖、奶油、糖浆、浓缩、珍珠、椰果）
- selection: 用户选择的店铺编号（select_shop时使用）

## 导航场景可提取参数：
- destination: 目的地名称/地址
- city: 城市名称（默认当前城市）
- waypoint: 途经点名称
- poi_type: POI类型（加油站/餐厅/停车场/充电站/医院/银行/超市/商场）
- keyword: POI搜索关键词
- poi_keyword: POI推荐关键词（如"情侣约会"、"朋友聚餐"、"周末游玩"等）
- radius: 搜索半径（米，默认3000）
- avoid_type: 避让类型（toll=收费/congestion=拥堵/highway=高速）
- favorite_name: 收藏地点名称
- route_preference: 路线偏好（最快/最短/省油）
- road_name: 路名
- selection: 用户选择的目的地编号（当从候选中选择时）
- route_index: 用户选择的路线编号（change_route时使用）

## 关键规则：
1. 如果用户提到了具体信息，提取到params中；如果缺失，不要猜测，params中不包含该字段
2. 结合对话历史理解上下文。例如用户先说"帮我点杯咖啡"，然后说"瑞幸的"，则第二个意图仍是order，shop_name为瑞幸咖啡
3. confirm_order和confirm_nav必须根据上下文区分：如果上一轮是咖啡下单确认，则"确认"=confirm_order；如果上一轮是路线确认，则"确认"=confirm_nav
4. cancel_order和cancel_nav同理：根据上下文区分
5. 咖啡场景：缺少coffee_name时设置needs_clarification=true并追问
6. 导航场景：缺少destination时设置needs_clarification=true并追问
7. 口语化表达也要理解，如"老样子"=reorder，"随便来一杯"=order。注意：行动 vs 询问的区别："回家"=nav_home（导航去家）vs "我的家在哪"/"家在哪儿"=query_home（询问家的地址）；"去公司"/"到公司"=nav_company（导航去公司）vs "我的公司在哪"/"公司在哪儿"=query_company（询问公司地址）。"多久到"=query_eta，"还有多少油"=vehicle_status
8. select_shop用于用户从咖啡店搜索结果中选择，如"第一个"、"就这家"、"选第2个"。仅当对话上下文是咖啡店搜索时使用
9. select_destination用于用户从导航目的地搜索结果或POI搜索结果中选择，如"第四个"、"选第3个"、"就这个"。当对话上下文是导航/POI搜索时，类似的"第N个"表达应识别为select_destination
10. change_route用于用户想换一条路线，如"换条路"、"走另一条"、"不走这条"

请严格输出以下JSON格式，不要有任何其他文字：
{"intents": [{"intent": "...", "params": {...}}, ...], "poi_list": null, "needs_clarification": false, "clarification_question": null}

注意：
- intents是一个数组，包含1个或多个意图。即使用户只表达了一个意图，也用数组格式返回
- 每个意图都有独立的intent和params
- poi_list字段：当intent为recommend_poi时，必须包含POI推荐列表；其他intent时poi_list为null或省略
- 推荐POI时请根据用户所在城市推荐真实存在的地点，返回不超过8个，每个包含name（名称）和reason（推荐理由）
- 例如"导航去中关村，顺便帮我点杯拿铁"应返回：{"intents": [{"intent": "navigate", "params": {"destination": "中关村"}}, {"intent": "order", "params": {"coffee_name": "拿铁"}}], "poi_list": null, "needs_clarification": false, "clarification_question": null}
- 例如"推荐一个适合情侣约会的地方"应返回：{"intents": [{"intent": "recommend_poi", "params": {"poi_keyword": "情侣约会"}}], "poi_list": [{"name": "蓝色港湾", "reason": "环境浪漫，适合散步和晚餐"}, {"name": "三里屯太古里", "reason": "时尚地标，餐厅众多"}], "needs_clarification": false, "clarification_question": null}
"""

VALID_INTENTS = {
    # 咖啡场景
    "order", "reorder", "history", "recommend", "confirm_order", "cancel_order", "select_shop",
    # 导航场景
    "navigate", "confirm_nav", "cancel_nav", "add_waypoint",
    "search_poi", "search_along_route", "traffic_info", "avoid_route",
    "query_eta", "vehicle_status", "nav_home", "nav_company", "nav_favorite",
    "query_home", "query_company", "recommend_poi",
    "select_destination", "change_route",
    # 通用
    "greeting", "help", "unknown"
}


class RuleNLU:
    """基于规则匹配的NLU，仅作为LLM的兜底fallback"""

    def __init__(self):
        self.intent_patterns = {
            # 咖啡场景
            "order": [r"点.*咖啡", r"订.*咖啡", r"来一杯", r"要一杯", r"点单", r"下单"],
            "reorder": [r"再来一杯", r"和上次一样", r"重复上次", r"再来一份"],
            "history": [r"历史订单", r"之前点过什么", r"我的订单", r"订单记录"],
            "recommend": [r"推荐", r"有什么好喝的"],
            "confirm_order": [r"确认下单", r"确认订单"],
            "cancel_order": [r"取消订单"],
            "select_shop": [r"第[一二三四五1-5]个店", r"就这家", r"选第\d+个", r"第\d+家"],
            # 导航场景（仅基础关键词兜底，精细意图由LLM处理）
            "navigate": [r"导航去", r"导航到", r"开车去", r"怎么走"],
            "nav_home": [r"回家"],
            "nav_company": [r"去公司", r"去单位"],
            "query_eta": [r"多久到", r"还要多久"],
            "vehicle_status": [r"还有多少油", r"还有多少电", r"油量", r"电量"],
            "cancel_nav": [r"取消导航", r"结束导航"],
            "search_poi": [r"附近找", r"找.*加油站", r"找.*餐厅", r"找.*停车场", r"附近.*公里"],
            "change_route": [r"换条路", r"换.*路线", r"走另一条", r"不走这条", r"换条路线"],
            # 通用
            "greeting": [r"你好", r"嗨", r"hello", r"hi"],
            "help": [r"帮助", r"怎么用", r"能做什么"]
        }

        # 咖啡实体（兜底用）
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
                    if intent == "reorder":
                        confidence = 0.9
                    elif intent in ["order", "history", "recommend"]:
                        confidence = 0.8
                    else:
                        confidence = 0.7
                    if confidence > max_confidence:
                        max_confidence = confidence
                        best_intent = intent

        return best_intent, max_confidence

    def extract_parameters(self, text: str) -> Dict:
        """提取参数，包括咖啡和新增的select_shop/change_route参数"""
        params = {}

        # select_shop: extract selection number
        import re as _re
        sel_match = _re.search(r"第([一二三四五1-5])个", text) or _re.search(r"选第(\d+)", text)
        if sel_match:
            num_map = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5}
            num_str = sel_match.group(1)
            params["selection"] = num_map.get(num_str, int(num_str) if num_str.isdigit() else 1)

        for shop in self.shop_names:
            if shop in text:
                params["shop_name"] = shop if shop != "瑞幸" else "瑞幸咖啡"
                break

        for coffee in self.coffee_names:
            if coffee in text:
                params["coffee_name"] = coffee
                break

        for size in self.sizes:
            if size in text:
                params["size"] = size
                break

        for ice in self.ice_options:
            if ice in text:
                params["ice"] = ice
                break

        for sugar in self.sugar_options:
            if sugar in text:
                params["sugar"] = sugar
                break

        toppings = []
        for topping in self.toppings:
            if f"加{topping}" in text or topping in text:
                toppings.append(topping)
        if toppings:
            params["toppings"] = toppings

        return params

    def parse(self, text: str, history: List[Dict] = None) -> Dict:
        intent, confidence = self.classify_intent(text)
        params = self.extract_parameters(text)

        if intent == "unknown":
            order_keywords = ["点", "来", "要", "订", "喝", "想", "杯"]
            has_order_keyword = any(kw in text for kw in order_keywords)
            has_coffee = params.get("coffee_name") is not None
            if has_order_keyword or has_coffee:
                intent = "order"
                confidence = 0.6

        # 简单"确认/取消"默认confirm_order，Agent侧根据状态修正
        if text.strip() in ("确认", "对", "好的", "可以", "没问题", "是的", "行"):
            intent = "confirm_order"
            confidence = 0.5
        elif text.strip() in ("取消", "不要了", "算了"):
            intent = "cancel_order"
            confidence = 0.5

        return {
            "intents": [{"intent": intent, "params": params}],
            "needs_clarification": False,
            "clarification_question": None,
            "source": "rule"
        }


class LLMNLU:
    """基于LLM的NLU，云端优先，失败时降级到本地Ollama，再失败则降级到RuleNLU"""

    def __init__(self,
                 model: str = "gemma4:e2b",
                 base_url: str = "http://localhost:11434/api/chat",
                 timeout: float = 520.0,
                 enable_fallback: bool = False,
                 # 云端LLM配置
                 llm_provider: str = "dashscope",
                 llm_api_key: str = "",
                 llm_model: str = "glm-5",
                 llm_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1",
                 llm_timeout: float = 60.0):
        # 本地ollama配置（降级用）
        self.model = model
        self.base_url = base_url
        self.timeout = timeout
        # 云端LLM配置（优先）
        self.llm_provider = llm_provider
        self.llm_api_key = llm_api_key
        self.llm_model = llm_model
        self.llm_base_url = llm_base_url
        self.llm_timeout = llm_timeout
        self.enable_fallback = enable_fallback
        self.fallback = RuleNLU()

    def _build_messages(self, text: str, history: Optional[List[Dict]]) -> List[Dict]:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        if history:
            # 只保留最近5轮对话，避免prompt过长
            recent_history = history[-10:]
            messages.extend(recent_history)

        messages.append({"role": "user", "content": text})
        return messages

    def _call_cloud_llm(self, messages: List[Dict]) -> Optional[str]:
        """调用云端LLM API（DashScope/OpenAI兼容）"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.llm_api_key}"
        }
        payload = {
            "model": self.llm_model,
            "messages": messages,
            "stream": False
        }

        req = urllib.request.Request(
            self.llm_base_url + "/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=self.llm_timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("choices", [{}])[0].get("message", {}).get("content", "")
        except TimeoutError:
            print(f"[debug] 云端LLM请求超时 (timeout={self.llm_timeout}s)")
            return None
        except urllib.error.HTTPError as e:
            print(f"[debug] 云端LLM HTTP错误: {e.code} {e.reason}")
            return None
        except urllib.error.URLError as e:
            print(f"[debug] 云端LLM网络连接错误: {e.reason}")
            return None
        except json.JSONDecodeError as e:
            print(f"[debug] 云端LLM返回结果JSON解析错误: {e}")
            return None
        except Exception as e:
            print(f"[debug] 云端LLM请求未知错误: {type(e).__name__}: {e}")
            return None

    def _call_local_llm(self, messages: List[Dict]) -> Optional[str]:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False
        }

        req = urllib.request.Request(
            self.base_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("message", {}).get("content", "")
        except TimeoutError:
            print(f"[debug] LLM请求超时 (timeout={self.timeout}s)")
            return None
        except urllib.error.HTTPError as e:
            print(f"[debug] LLM服务HTTP错误: {e.code} {e.reason}")
            return None
        except urllib.error.URLError as e:
            print(f"[debug] LLM网络连接错误: {e.reason}")
            return None
        except json.JSONDecodeError as e:
            print(f"[debug] LLM返回结果JSON解析错误: {e}")
            return None
        except Exception as e:
            print(f"[debug] LLM请求未知错误: {type(e).__name__}: {e}")
            return None

    def _extract_json_from_text(self, text: str) -> Optional[Dict]:
        """尝试从非标准JSON响应中提取JSON"""
        text = text.strip()

        # 尝试匹配代码块中的JSON
        match = re.search(r'```(?:json)?\s*({.*?})\s*```', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        # 尝试匹配整个文本为JSON
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 尝试匹配文本中的JSON对象（支持嵌套）
        # 使用括号匹配来找最外层的{}
        depth = 0
        start = -1
        for i, ch in enumerate(text):
            if ch == '{':
                if depth == 0:
                    start = i
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0 and start >= 0:
                    try:
                        return json.loads(text[start:i+1])
                    except json.JSONDecodeError:
                        pass

        return None

    def _validate_result(self, result: Dict) -> bool:
        """验证LLM返回结果是否合法（支持intents数组格式和旧版单intent格式）"""
        if not isinstance(result, dict):
            return False

        # 如果有澄清请求，允许通过（intent可能是unknown）
        if result.get("needs_clarification") and result.get("clarification_question"):
            return True

        # 新格式：intents数组
        if "intents" in result:
            if not isinstance(result["intents"], list) or len(result["intents"]) == 0:
                return False
            for item in result["intents"]:
                if not isinstance(item, dict):
                    return False
                if item.get("intent") not in VALID_INTENTS:
                    return False
                if not isinstance(item.get("params"), dict):
                    return False
            return True

        # 旧格式兼容：单intent
        if result.get("intent") not in VALID_INTENTS:
            return False
        if not isinstance(result.get("params"), dict):
            return False
        return True

    def _make_error_result(self, text: str, history: List[Dict], messages: List[Dict],
                           error_type: str, content: str = None) -> Dict:
        """构建LLM错误时的返回结果，根据enable_fallback决定是否降级"""
        result = {
            "intents": [{"intent": "unknown", "params": {}}],
            "poi_list": None,
            "needs_clarification": False,
            "clarification_question": None,
            "llm_error": True,
            "llm_error_type": error_type,
            "llm_request_messages": messages,
            "source": "llm"
        }
        if content:
            result["llm_raw_response"] = content

        if self.enable_fallback:
            fallback_result = self.fallback.parse(text, history)
            result["intents"] = fallback_result["intents"]
            result["source"] = "rule_fallback"

        return result

    def parse(self, text: str, history: List[Dict] = None) -> Dict:
        messages = self._build_messages(text, history)
        content = None
        llm_source = None

        # 优先调用云端LLM
        if self.llm_api_key:
            content = self._call_cloud_llm(messages)
            if content:
                llm_source = "cloud"
                print(f"[debug] 使用云端LLM ({self.llm_provider}/{self.llm_model})")

        # 云端失败，降级到本地Ollama
        if content is None and self.model:
            print("[debug] 云端LLM不可用，降级到本地Ollama...")
            content = self._call_local_llm(messages)
            if content:
                llm_source = "local"

        if content is None:
            print("[debug] LLM调用失败(网络/超时/服务错误)" +
                  ("，降级到规则匹配" if self.enable_fallback else ""))
            return self._make_error_result(text, history, messages, "call_failed", None)

        # 尝试从LLM返回的文本中解析JSON
        result = self._extract_json_from_text(content)

        if result is None:
            print(f"[debug] LLM返回内容无法解析为JSON，原始内容: {content[:200]}" +
                  ("，降级到规则匹配" if self.enable_fallback else ""))
            return self._make_error_result(text, history, messages, "parse_error", content)

        if not self._validate_result(result):
            print(f"[debug] LLM返回结果校验失败，intent无效或params格式错误: {result}" +
                  ("，降级到规则匹配" if self.enable_fallback else ""))
            return self._make_error_result(text, history, messages, "validation_error", content)

        # 统一为intents数组格式（兼容旧版单intent格式）
        if "intents" in result:
            intents = []
            for item in result["intents"]:
                intents.append({
                    "intent": item["intent"],
                    "params": {k: v for k, v in item.get("params", {}).items() if v is not None}
                })
        else:
            # 旧格式兼容：单intent转为数组
            intents = [{
                "intent": result["intent"],
                "params": {k: v for k, v in result.get("params", {}).items() if v is not None}
            }]

        return {
            "intents": intents,
            "poi_list": result.get("poi_list"),
            "needs_clarification": result.get("needs_clarification", False),
            "clarification_question": result.get("clarification_question"),
            "source": llm_source or "llm",
            "llm_request_messages": messages,
            "llm_raw_response": content
        }
