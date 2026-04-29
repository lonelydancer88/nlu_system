"""Tests for OrderSimulator and NavigationSimulator."""
import os
import sys
import time
import pytest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modules.simulation import OrderSimulator
from modules.nav_simulation import NavigationSimulator


class TestOrderSimulator:
    @pytest.fixture
    def simulator(self):
        return OrderSimulator()

    @patch('modules.simulation.time.sleep')
    def test_simulate_order_calls_callback(self, mock_sleep, simulator):
        callbacks = []
        def callback(status, message):
            callbacks.append((status, message))

        order = {"order_id": "CF_TEST_001"}
        simulator.simulate_order_process(order, callback)

        assert len(callbacks) == 5
        statuses = [c[0] for c in callbacks]
        assert statuses == ["pending", "confirmed", "making", "delivering", "completed"]

    @patch('modules.simulation.time.sleep')
    def test_simulate_order_messages_contain_order_id(self, mock_sleep, simulator):
        callbacks = []
        def callback(status, message):
            callbacks.append(message)

        order = {"order_id": "CF_123"}
        simulator.simulate_order_process(order, callback)

        for msg in callbacks:
            assert "CF_123" in msg

    @patch('modules.simulation.time.sleep')
    def test_simulate_completed_status(self, mock_sleep, simulator):
        last_callback = None
        def callback(status, message):
            nonlocal last_callback
            last_callback = (status, message)

        order = {"order_id": "CF_TEST"}
        simulator.simulate_order_process(order, callback)

        assert last_callback[0] == "completed"

    def test_status_flow_order(self, simulator):
        """Verify the status flow is sequential and correct."""
        expected_flow = [
            ("pending", "订单已提交，正在处理...", 1),
            ("confirmed", "商家已接单，正在制作咖啡...", 3),
            ("making", "咖啡制作完成，正在打包...", 2),
            ("delivering", "骑手已取餐，正在配送，预计15分钟到达...", 5),
            ("completed", "🛵 您的咖啡已送到，请享用~", 0)
        ]
        assert len(simulator.status_flow) == 5
        for i, (status, msg, delay) in enumerate(simulator.status_flow):
            assert status == expected_flow[i][0]

    @patch('modules.simulation.time.sleep')
    def test_sleep_called_with_correct_delays(self, mock_sleep, simulator):
        callbacks = []
        def callback(status, message):
            callbacks.append((status, message))

        order = {"order_id": "CF_TEST"}
        simulator.simulate_order_process(order, callback)

        # sleep is called with delays: 1, 3, 2, 5 (last has delay=0, no sleep)
        assert mock_sleep.call_count == 4
        assert mock_sleep.call_args_list[0][0][0] == 1
        assert mock_sleep.call_args_list[1][0][0] == 3
        assert mock_sleep.call_args_list[2][0][0] == 2
        assert mock_sleep.call_args_list[3][0][0] == 5


class TestNavigationSimulator:
    @pytest.fixture
    def simulator(self):
        return NavigationSimulator()

    @patch('modules.nav_simulation.time.sleep')
    def test_simulate_navigation_calls_callback(self, mock_sleep, simulator):
        callbacks = []
        def callback(status, message):
            callbacks.append((status, message))

        route = {"to": "中关村"}
        session = {"eta_minutes": 25, "progress": 0}
        simulator.simulate_navigation(route, session, callback)

        assert len(callbacks) == 6
        statuses = [c[0] for c in callbacks]
        assert "started" in statuses
        assert "arrived" in statuses

    @patch('modules.nav_simulation.time.sleep')
    def test_simulate_navigation_messages_contain_destination(self, mock_sleep, simulator):
        callbacks = []
        def callback(status, message):
            callbacks.append(message)

        route = {"to": "三里屯"}
        session = {"eta_minutes": 15, "progress": 0}
        simulator.simulate_navigation(route, session, callback)

        for msg in callbacks:
            assert "三里屯" in msg

    @patch('modules.nav_simulation.time.sleep')
    def test_simulate_final_status_is_arrived(self, mock_sleep, simulator):
        last_callback = None
        def callback(status, message):
            nonlocal last_callback
            last_callback = (status, message)

        route = {"to": "目的地"}
        session = {"eta_minutes": 10, "progress": 0}
        simulator.simulate_navigation(route, session, callback)

        assert last_callback[0] == "arrived"

    def test_status_flow_order(self, simulator):
        expected_statuses = [
            "started", "progress_30", "progress_60",
            "traffic_update", "progress_90", "arrived"
        ]
        actual_statuses = [s[0] for s in simulator.status_flow]
        assert actual_statuses == expected_statuses

    @patch('modules.nav_simulation.time.sleep')
    def test_route_without_to_key(self, mock_sleep, simulator):
        """Simulator should handle missing 'to' key gracefully."""
        callbacks = []
        def callback(status, message):
            callbacks.append(message)

        route = {}  # No 'to' key
        session = {"eta_minutes": 10, "progress": 0}
        simulator.simulate_navigation(route, session, callback)
        assert len(callbacks) == 6
