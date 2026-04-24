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
        order_id = order["order_id"]

        for status, message, delay in self.status_flow:
            if delay > 0:
                callback(status, f"[{order_id}] {message}")
                time.sleep(delay)
            else:
                callback(status, f"[{order_id}] {message}")
