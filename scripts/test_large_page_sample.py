#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大页面采样测试
==============
测试大页面（5099产品）的部分产品加载性能
"""

import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.crawler.products import ProductLinksCrawler
from src.utils.browser_manager import create_browser_manager


def test_large_page():
    """测试大页面性能"""
    # 5099产品的大页面
    test_url = "https://www.traceparts.cn/en/search/traceparts-classification-electrical-electrical-protection-devices-circuit-breakers-molded-case-circuit-breakers-mccb?CatalogPath=TRACEPARTS%3ATP09004001008"
    
    print("🎯 大页面采样测试")
    print("=" * 60)
    print(f"测试URL: {test_url}")
    print("目标: 测试前500个产品的加载速度")
    print("模式: 无头模式（生产环境）\n")
    
    # 创建爬取器
    browser_manager = create_browser_manager(pool_size=1)
    crawler = ProductLinksCrawler(browser_manager)
    
    # 临时修改爬取器，在达到500个产品时停止
    original_load_all = crawler._load_all_results
    
    def limited_load(driver):
        """限制加载到500个产品"""
        # 初始滚动
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(0.5)
        
        last_count = len(driver.find_elements(By.CSS_SELECTOR, "a[href*='&Product=']"))
        no_change_count = 0
        click_count = 0
        
        while True:
            current_count = len(driver.find_elements(By.CSS_SELECTOR, "a[href*='&Product=']"))
            
            # 达到500个就停止
            if current_count >= 500:
                print(f"✓ 达到500个产品，停止加载")
                break
                
            if current_count == last_count:
                no_change_count += 1
                if no_change_count >= 5:
                    print(f"✓ 产品数不再变化，停止加载（当前: {current_count}）")
                    break
            else:
                no_change_count = 0
                last_count = current_count
                
            # 调用原始的点击逻辑
            original_load_all(driver)
            break
    
    # 临时替换方法
    crawler._load_all_results = limited_load
    
    try:
        print("⏳ 开始爬取（限制500个产品）...")
        start_time = time.time()
        
        # 导入必要的模块
        from selenium.webdriver.common.by import By
        
        products = crawler.extract_product_links(test_url)
        
        elapsed = time.time() - start_time
        
        print(f"\n{'='*60}")
        print(f"✅ 完成!")
        print(f"  获取产品数: {len(products)}")
        print(f"  用时: {elapsed:.1f} 秒")
        print(f"  速度: {len(products)/elapsed:.1f} 个/秒")
        
        # 评估
        if len(products) >= 400:
            print(f"\n✅ 性能良好！")
        else:
            print(f"\n⚠️  获取产品数较少")
            
        # 预估全部5099个产品的时间
        if len(products) > 0:
            estimated_time = (5099 / len(products)) * elapsed
            print(f"\n💡 预估获取全部5099个产品需要: {estimated_time:.1f} 秒 ({estimated_time/60:.1f} 分钟)")
            
    finally:
        # 恢复原始方法
        crawler._load_all_results = original_load_all
        browser_manager.shutdown()
        print("\n✅ 测试完成")


if __name__ == '__main__':
    test_large_page() 