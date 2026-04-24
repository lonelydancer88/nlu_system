import time
from typing import Dict, Callable


class NavigationSimulator:
    def __init__(self):
        self.status_flow = [
            ("started", "导航开始，沿当前道路行驶...", 2),
            ("progress_30", "已行驶约30%路程，前方路况正常", 3),
            ("progress_60", "已行驶约60%路程，预计还需15分钟", 3),
            ("traffic_update", "前方路段车流增大，建议注意车速", 2),
            ("progress_90", "即将到达目的地，请注意右侧路口", 2),
            ("arrived", "📍 已到达目的地，导航结束", 0)
        ]

    def simulate_navigation(self, route: Dict, session: Dict,
                            callback: Callable[[str, str], None]) -> None:
        dest = route.get("to", "目的地")

        for status, message, delay in self.status_flow:
            if delay > 0:
                callback(status, f"[导航→{dest}] {message}")
                time.sleep(delay)
            else:
                callback(status, f"[导航→{dest}] {message}")
