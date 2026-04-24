#!/usr/bin/env python3
"""向后兼容入口，推荐使用 agent.py 启动统一助手"""
from agent import UnifiedAgent

if __name__ == "__main__":
    agent = UnifiedAgent()
    agent.run()
