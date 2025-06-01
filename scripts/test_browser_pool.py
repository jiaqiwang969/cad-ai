#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
浏览器池测试脚本
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import threading
from src.utils.browser_manager import create_browser_manager

def test_browser_pool():
    """测试浏览器池功能"""
    print("🧪 测试浏览器池...")
    
    # 创建小池进行测试
    manager = create_browser_manager(pool_size=3)
    
    def worker(worker_id):
        """工作线程"""
        try:
            print(f"Worker {worker_id}: 请求浏览器...")
            with manager.get_browser() as browser:
                print(f"Worker {worker_id}: 获得浏览器，访问页面...")
                browser.get("https://www.example.com")
                time.sleep(2)  # 模拟工作
                print(f"Worker {worker_id}: 完成工作")
        except Exception as e:
            print(f"Worker {worker_id}: 错误 - {e}")
    
    # 创建多个线程
    threads = []
    for i in range(6):  # 创建6个线程，超过池大小
        t = threading.Thread(target=worker, args=(i,))
        threads.append(t)
        t.start()
        time.sleep(0.5)  # 稍微错开启动时间
    
    # 等待所有线程完成
    for t in threads:
        t.join()
    
    # 查看统计
    stats = manager.get_stats()
    print(f"\n📊 池统计:")
    print(f"  - 池大小: {stats['pool_size']}")
    print(f"  - 已创建: {stats['created_count']}")
    print(f"  - 可用数: {stats['available_count']}")
    
    # 清理
    manager.shutdown()
    print("✅ 测试完成")


if __name__ == '__main__':
    test_browser_pool() 