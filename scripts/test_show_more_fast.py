#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速测试Show More Results
========================
优化版本，更快速地获取所有产品
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from src.utils.browser_manager import create_browser_manager


def test_show_more_fast():
    """快速测试Show More功能"""
    url = "https://www.traceparts.cn/en/search/traceparts-classification-electrical-electrical-protection-devices-circuit-breakers-transfer-switching-equipment-tse?CatalogPath=TRACEPARTS%3ATP09004001017"
    
    print("🚀 快速测试 Show More Results")
    print("=" * 80)
    
    manager = create_browser_manager(pool_size=1)
    
    try:
        with manager.get_browser() as driver:
            print("📋 加载页面...")
            driver.get(url)
            
            # 等待初始产品加载
            wait = WebDriverWait(driver, 10)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='&Product=']")))
            time.sleep(1)
            
            # 快速收集产品的JavaScript
            js_collect = """
            return document.querySelectorAll('a[href*="&Product="]').length;
            """
            
            # 记录初始产品数
            initial_count = driver.execute_script(js_collect)
            print(f"✅ 初始产品数: {initial_count}")
            
            # 专门针对这个网站的按钮选择器
            button_clicked = 0
            max_clicks = 5  # 最多点击5次
            
            for i in range(max_clicks):
                # 滚动到底部，让按钮出现
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(0.5)
                
                # 尝试找到并点击按钮
                try:
                    # 使用更精确的选择器
                    button = driver.find_element(
                        By.XPATH, 
                        "//button[contains(text(), 'Show more results')] | "
                        "//button[contains(text(), 'SHOW MORE RESULTS')] | "
                        "//a[contains(text(), 'Show more results')]"
                    )
                    
                    if button.is_displayed():
                        # JavaScript点击更可靠
                        driver.execute_script("arguments[0].click();", button)
                        button_clicked += 1
                        print(f"  ✓ 第 {button_clicked} 次点击 Show More")
                        
                        # 等待新产品加载
                        time.sleep(1.5)
                        
                        # 检查产品数量
                        current_count = driver.execute_script(js_collect)
                        print(f"    当前产品数: {current_count}")
                        
                        if current_count >= 145:
                            print(f"\n🎉 成功！已加载所有 {current_count} 个产品")
                            break
                    else:
                        print("  按钮不可见")
                        break
                        
                except Exception as e:
                    print(f"  未找到 Show More 按钮: {type(e).__name__}")
                    
                    # 再滚动一下试试
                    driver.execute_script("window.scrollTo(0, 0);")
                    time.sleep(0.3)
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(0.5)
            
            # 最终统计
            final_count = driver.execute_script(js_collect)
            print(f"\n📊 最终结果:")
            print(f"  - 初始产品: {initial_count}")
            print(f"  - 最终产品: {final_count}")
            print(f"  - 增加产品: {final_count - initial_count}")
            print(f"  - 点击次数: {button_clicked}")
            
            # 获取所有产品链接
            if final_count > 0:
                links = driver.execute_script("""
                    return Array.from(new Set(
                        Array.from(document.querySelectorAll('a[href*="&Product="]'))
                            .map(a => a.href)
                    ));
                """)
                
                print(f"\n提取到 {len(links)} 个唯一产品链接")
                print("前3个:")
                for i, link in enumerate(links[:3], 1):
                    print(f"  {i}. {link}")
                    
    finally:
        manager.shutdown()
        print("\n✅ 测试完成")


if __name__ == '__main__':
    test_show_more_fast() 