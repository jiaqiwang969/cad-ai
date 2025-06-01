#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试5099个产品的页面
====================
测试优化策略是否能处理大量产品
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from src.utils.browser_manager import create_browser_manager
from src.crawler.products import ProductLinksCrawler


def test_5099_products():
    """测试5099个产品的页面"""
    url = "https://www.traceparts.cn/en/search/traceparts-classification-electrical-electrical-protection-devices-circuit-breakers-molded-case-circuit-breakers-mccb?CatalogPath=TRACEPARTS%3ATP09004001008"
    
    print("🎯 测试5099个产品的页面")
    print("=" * 80)
    print(f"URL: {url}")
    print("目标: 5099个产品")
    print("=" * 80)
    
    # 先用手动方法测试，看看页面行为
    print("\n📋 第一步：分析页面行为")
    
    manager = create_browser_manager(pool_size=1)
    
    try:
        with manager.get_browser() as driver:
            start_time = time.time()
            driver.get(url)
            
            # 等待初始加载
            wait = WebDriverWait(driver, 10)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='&Product=']")))
            time.sleep(1)
            
            # 获取初始产品数
            initial_count = len(driver.find_elements(By.CSS_SELECTOR, "a[href*='&Product=']"))
            print(f"  初始产品数: {initial_count}")
            
            # 查看页面上显示的总数
            try:
                # 尝试找到显示总数的元素
                result_info = driver.execute_script("""
                    const elements = document.querySelectorAll('*');
                    for (let el of elements) {
                        if (el.textContent.includes('5099') || el.textContent.includes('results')) {
                            return el.textContent;
                        }
                    }
                    return null;
                """)
                if result_info:
                    print(f"  页面显示: {result_info}")
            except:
                pass
            
            # 滚动测试
            print("\n  测试滚动加载...")
            for i in range(3):
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1.5)
                count = len(driver.find_elements(By.CSS_SELECTOR, "a[href*='&Product=']"))
                print(f"    第{i+1}次滚动后: {count} 个产品")
                if count == initial_count:
                    break
            
            # 查找Show More按钮
            print("\n  查找Show More按钮...")
            show_more_count = 0
            max_clicks = 10  # 限制点击次数避免太长时间
            
            while show_more_count < max_clicks:
                try:
                    button = driver.find_element(By.CSS_SELECTOR, "button.more-results")
                    if button.is_displayed():
                        driver.execute_script("arguments[0].click();", button)
                        show_more_count += 1
                        print(f"    ✓ 第 {show_more_count} 次点击Show More")
                        time.sleep(1)  # 等待加载
                        
                        current_count = len(driver.find_elements(By.CSS_SELECTOR, "a[href*='&Product=']"))
                        print(f"      当前产品数: {current_count}")
                        
                        # 如果产品数增长缓慢，可能需要更多时间
                        if current_count > 1000:
                            print("      产品数较多，减少点击频率...")
                            break
                except:
                    # 没有找到按钮，可能需要滚动
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.9);")
                    time.sleep(0.5)
                    
                    # 再次检查产品数
                    current_count = len(driver.find_elements(By.CSS_SELECTOR, "a[href*='&Product=']"))
                    if current_count >= 500:  # 如果已经有很多产品，停止测试
                        print(f"    已加载 {current_count} 个产品，停止手动测试")
                        break
            
            manual_time = time.time() - start_time
            final_count = len(driver.find_elements(By.CSS_SELECTOR, "a[href*='&Product=']"))
            print(f"\n  手动测试结果: {final_count} 个产品, 用时 {manual_time:.1f} 秒")
            
        # 使用爬虫测试
        print("\n📋 第二步：使用优化后的爬虫")
        crawler = ProductLinksCrawler(manager)
        
        start_time = time.time()
        products = crawler.extract_product_links(url)
        crawler_time = time.time() - start_time
        
        print(f"\n✅ 爬虫结果:")
        print(f"  - 产品数: {len(products)}")
        print(f"  - 用时: {crawler_time:.1f} 秒")
        print(f"  - 速度: {len(products)/crawler_time:.1f} 个/秒")
        
        # 分析结果
        print(f"\n📊 分析:")
        completion_rate = len(products) / 5099 * 100
        print(f"  - 完成率: {completion_rate:.1f}%")
        
        if len(products) >= 5099:
            print("  🎉 完美！获取了所有产品")
        elif len(products) >= 4000:
            print("  ✅ 优秀！获取了大部分产品")
        elif len(products) >= 2000:
            print("  ⚠️ 一般！可能需要优化策略")
        else:
            print("  ❌ 需要改进！产品数太少")
            
        # 如果没有获取到所有产品，分析原因
        if len(products) < 5099:
            print("\n🔍 可能的原因:")
            print("  1. 网站可能限制了单次加载的最大产品数")
            print("  2. 可能需要登录才能查看所有产品")
            print("  3. 可能需要更多的点击次数或等待时间")
            print("  4. 网站可能使用了不同的分页机制")
        
        # 保存一些产品链接作为示例
        if products:
            print("\n📦 产品示例:")
            print("前3个:")
            for i, link in enumerate(products[:3], 1):
                print(f"  {i}. {link[:100]}...")
            
            if len(products) > 6:
                print("\n后3个:")
                for i, link in enumerate(products[-3:], len(products)-2):
                    print(f"  {i}. {link[:100]}...")
                    
    finally:
        manager.shutdown()
        print("\n✅ 测试完成")


if __name__ == '__main__':
    test_5099_products() 