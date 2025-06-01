#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
可视化调试脚本
==============
临时关闭无头模式，观察爬虫行为
"""

import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 在导入其他模块之前修改配置
from config.settings import Settings
Settings.CRAWLER['headless'] = False  # 关闭无头模式

from src.crawler.products import ProductLinksCrawler
from src.utils.browser_manager import create_browser_manager


def debug_visual():
    """可视化调试"""
    # 使用145产品的页面进行测试
    test_url = "https://www.traceparts.cn/en/search/traceparts-classification-electrical-electrical-protection-devices-circuit-breakers-transfer-switching-equipment-tse?CatalogPath=TRACEPARTS%3ATP09004001017"
    
    print("🔍 可视化调试模式")
    print("=" * 60)
    print("⚠️  已关闭无头模式，将打开浏览器窗口")
    print(f"测试URL: {test_url}")
    print("目标: 145个产品\n")
    
    # 创建单个浏览器实例
    browser_manager = create_browser_manager(pool_size=1)
    crawler = ProductLinksCrawler(browser_manager)
    
    try:
        print("🌐 正在打开浏览器...")
        print("👀 请观察浏览器的行为")
        print("-" * 60)
        
        start_time = time.time()
        products = crawler.extract_product_links(test_url)
        elapsed = time.time() - start_time
        
        print("-" * 60)
        print(f"\n✅ 完成!")
        print(f"  - 获取产品数: {len(products)}")
        print(f"  - 用时: {elapsed:.1f} 秒")
        print(f"  - 速度: {len(products)/elapsed:.1f} 个/秒")
        
        if len(products) < 145:
            print(f"\n⚠️  只获取了 {len(products)}/145 个产品")
            print("可能的问题：")
            print("  1. 'Show more' 按钮没有被正确点击")
            print("  2. 页面加载不完整")
            print("  3. 选择器不匹配")
        else:
            print(f"\n🎉 成功获取所有产品！")
            
        # 显示前5个产品链接
        print(f"\n📋 前5个产品链接:")
        for i, link in enumerate(products[:5], 1):
            print(f"  {i}. {link[:100]}...")
            
    finally:
        print("\n🔄 等待3秒后关闭浏览器...")
        time.sleep(3)
        browser_manager.shutdown()
        print("✅ 调试完成")


if __name__ == '__main__':
    debug_visual() 