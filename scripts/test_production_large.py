#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生产代码大页面测试
==================
直接测试生产代码，不加任何限制
"""

import sys
import os
import time
import signal
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.crawler.products import ProductLinksCrawler
from src.utils.browser_manager import create_browser_manager


# 设置超时处理
def timeout_handler(signum, frame):
    raise TimeoutError("测试超时")

# 设置5分钟超时
signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(300)  # 5分钟


def test_production_large():
    """测试生产代码在大页面上的表现"""
    # 5099产品的大页面
    test_url = "https://www.traceparts.cn/en/search/traceparts-classification-electrical-electrical-protection-devices-circuit-breakers-molded-case-circuit-breakers-mccb?CatalogPath=TRACEPARTS%3ATP09004001008"
    
    print("🎯 生产代码大页面测试")
    print("=" * 60)
    print(f"测试URL: {test_url}")
    print("目标: 5099个产品")
    print("限制: 5分钟超时")
    print("模式: 无头模式（生产环境）\n")
    
    # 创建爬取器
    browser_manager = create_browser_manager(pool_size=1)
    crawler = ProductLinksCrawler(browser_manager)
    
    try:
        print("⏳ 开始爬取...")
        print("提示: 按 Ctrl+C 可以提前结束\n")
        
        start_time = time.time()
        
        products = crawler.extract_product_links(test_url)
        
        elapsed = time.time() - start_time
        
        print(f"\n{'='*60}")
        print(f"✅ 完成!")
        print(f"  获取产品数: {len(products)}")
        print(f"  目标产品数: 5099")
        print(f"  完成率: {len(products)/5099*100:.1f}%")
        print(f"  用时: {elapsed:.1f} 秒 ({elapsed/60:.1f} 分钟)")
        print(f"  速度: {len(products)/elapsed:.1f} 个/秒")
        
        # 评估
        if len(products) >= 5000:
            print(f"\n🎉 完美！获取了几乎所有产品")
        elif len(products) >= 4000:
            print(f"\n✅ 优秀！获取了大部分产品")
        elif len(products) >= 2000:
            print(f"\n⚠️ 良好，但还有改进空间")
        elif len(products) >= 1000:
            print(f"\n⚠️ 一般，需要进一步优化")
        else:
            print(f"\n❌ 需要改进")
            
        # 对比参考
        print(f"\n📊 参考:")
        print(f"  - test_5099_improved.py: 5000个产品，243.8秒")
        if len(products) > 0:
            print(f"  - 当前效率: {len(products)/elapsed:.1f} 个/秒")
            print(f"  - 参考效率: {5000/243.8:.1f} 个/秒")
            
    except TimeoutError:
        elapsed = 300
        print(f"\n⏰ 测试超时（5分钟）")
        print("测试被中断，可能需要优化算法")
        
    except KeyboardInterrupt:
        elapsed = time.time() - start_time
        print(f"\n⚠️ 测试被用户中断")
        print(f"运行时间: {elapsed:.1f} 秒")
        
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        
    finally:
        # 取消超时
        signal.alarm(0)
        browser_manager.shutdown()
        print("\n✅ 测试结束")


if __name__ == '__main__':
    test_production_large() 