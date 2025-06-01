#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
速度优化测试
============
探索更快的方法获取所有产品
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from src.utils.browser_manager import create_browser_manager


def test_speed_optimization():
    """测试速度优化方案"""
    url = "https://www.traceparts.cn/en/search/traceparts-classification-electrical-electrical-protection-devices-circuit-breakers-transfer-switching-equipment-tse?CatalogPath=TRACEPARTS%3ATP09004001017"
    
    print("⚡ 速度优化测试")
    print("=" * 80)
    
    manager = create_browser_manager(pool_size=1)
    
    try:
        with manager.get_browser() as driver:
            start_time = time.time()
            driver.get(url)
            
            # 等待初始加载
            wait = WebDriverWait(driver, 10)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='&Product=']")))
            
            # 方法1：直接触发多次点击，不等待
            print("\n📋 方法1：快速连续点击")
            
            # 快速滚动到底部触发第一次加载
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)  # 最小等待
            
            # 尝试快速点击多次
            clicks = 0
            for i in range(3):  # 最多需要点击2-3次
                try:
                    # 使用CSS选择器更快
                    button = driver.find_element(By.CSS_SELECTOR, "button.more-results")
                    driver.execute_script("arguments[0].click();", button)
                    clicks += 1
                    print(f"  ✓ 第 {clicks} 次点击")
                    
                    # 使用更短的等待，只等待按钮状态改变
                    time.sleep(0.5)
                    
                except:
                    # 没有按钮了，尝试滚动
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.9);")
                    time.sleep(0.3)
            
            # 等待最后的产品加载
            time.sleep(1)
            
            # 统计结果
            count1 = driver.execute_script("return document.querySelectorAll('a[href*=\"&Product=\"]').length;")
            time1 = time.time() - start_time
            print(f"  结果: {count1} 个产品, 用时: {time1:.1f}秒")
            
            # 方法2：分析是否可以直接修改页面参数
            print("\n📋 方法2：尝试直接加载所有产品")
            driver.get(url)
            time.sleep(1)
            
            # 检查是否有分页参数
            js_check = """
            // 查找可能的分页控制
            const possibleVars = window;
            for (let key in possibleVars) {
                if (key.toLowerCase().includes('page') || 
                    key.toLowerCase().includes('limit') ||
                    key.toLowerCase().includes('size')) {
                    console.log(key + ':', possibleVars[key]);
                }
            }
            
            // 查找React/Vue组件数据
            const rootEl = document.querySelector('#root') || document.querySelector('[id*="app"]');
            if (rootEl && rootEl.__vue__) {
                console.log('Vue data:', rootEl.__vue__.$data);
            }
            if (rootEl && rootEl._reactRootContainer) {
                console.log('React detected');
            }
            """
            driver.execute_script(js_check)
            
            # 方法3：使用WebDriverWait优化等待
            print("\n📋 方法3：智能等待策略")
            driver.get(url)
            start_time = time.time()
            
            # 初始滚动
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            
            # 使用WebDriverWait等待产品数量变化
            initial_count = 40
            expected_counts = [80, 120, 145]  # 预期的产品数量阶段
            
            for expected in expected_counts:
                try:
                    # 等待产品数量达到预期
                    WebDriverWait(driver, 5).until(
                        lambda d: len(d.find_elements(By.CSS_SELECTOR, "a[href*='&Product=']")) >= expected
                    )
                    print(f"  ✓ 达到 {expected} 个产品")
                    
                    if expected < 145:
                        # 立即尝试点击按钮
                        try:
                            button = driver.find_element(By.CSS_SELECTOR, "button.more-results")
                            driver.execute_script("arguments[0].click();", button)
                            print(f"    点击 Show More")
                        except:
                            # 可能需要滚动
                            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                            
                except:
                    print(f"  ✗ 未能达到 {expected} 个产品")
                    break
            
            count3 = driver.execute_script("return document.querySelectorAll('a[href*=\"&Product=\"]').length;")
            time3 = time.time() - start_time
            print(f"  最终结果: {count3} 个产品, 用时: {time3:.1f}秒")
            
            # 方法4：预加载优化
            print("\n📋 方法4：并行操作优化")
            driver.get(url)
            start_time = time.time()
            
            # JavaScript代码：持续监控和点击
            js_auto_click = """
            let clickCount = 0;
            const interval = setInterval(() => {
                // 检查按钮
                const button = document.querySelector('button.more-results');
                if (button && button.offsetParent !== null) {
                    button.click();
                    clickCount++;
                    console.log('Auto clicked:', clickCount);
                }
                
                // 检查产品数
                const products = document.querySelectorAll('a[href*="&Product="]').length;
                if (products >= 145 || clickCount >= 3) {
                    clearInterval(interval);
                }
                
                // 保持页面在底部
                window.scrollTo(0, document.body.scrollHeight);
            }, 500);  // 每500毫秒检查一次
            
            // 10秒后自动停止
            setTimeout(() => clearInterval(interval), 10000);
            """
            
            driver.execute_script(js_auto_click)
            
            # 等待自动加载完成
            time.sleep(5)
            
            count4 = driver.execute_script("return document.querySelectorAll('a[href*=\"&Product=\"]').length;")
            time4 = time.time() - start_time
            print(f"  最终结果: {count4} 个产品, 用时: {time4:.1f}秒")
            
    finally:
        manager.shutdown()
        print("\n✅ 测试完成")


if __name__ == '__main__':
    test_speed_optimization() 