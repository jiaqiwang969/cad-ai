#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速算法可视化调试
==================
直接在脚本中实现优化算法
"""

import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 在导入其他模块之前修改配置
from config.settings import Settings
Settings.CRAWLER['headless'] = False  # 关闭无头模式

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def fast_load_products(driver):
    """快速加载产品（参考test_5099_improved.py）"""
    print("⚡ 使用快速加载算法...")
    
    # 初始快速滚动
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(0.5)
    
    last_count = len(driver.find_elements(By.CSS_SELECTOR, "a[href*='&Product=']"))
    no_change_count = 0
    click_count = 0
    
    while True:
        current_count = len(driver.find_elements(By.CSS_SELECTOR, "a[href*='&Product=']"))
        print(f"  当前产品数: {current_count}")
        
        if current_count == last_count:
            no_change_count += 1
            if no_change_count >= 3:  # 只等3次
                print("  ✓ 产品数不再变化，结束加载")
                break
        else:
            no_change_count = 0
            last_count = current_count
            
        # 尝试点击按钮（简化的选择器）
        try:
            button = driver.find_element(By.CSS_SELECTOR, "button.more-results")
            if button.is_displayed() and button.is_enabled():
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                time.sleep(0.3)
                driver.execute_script("arguments[0].click();", button)
                click_count += 1
                print(f"  ✓ 第 {click_count} 次点击 Show More")
                time.sleep(1)
                continue
        except:
            pass
            
        # 没找到按钮，滚动
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(0.3)
        
    return current_count


def debug_fast():
    """快速算法调试"""
    test_url = "https://www.traceparts.cn/en/search/traceparts-classification-electrical-electrical-protection-devices-circuit-breakers-transfer-switching-equipment-tse?CatalogPath=TRACEPARTS%3ATP09004001017"
    
    print("🚀 快速算法可视化调试")
    print("=" * 60)
    print("⚠️  已关闭无头模式")
    print(f"测试URL: {test_url}")
    print("目标: 145个产品\n")
    
    # 创建驱动
    options = Options()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    driver = webdriver.Chrome(options=options)
    
    try:
        print("🌐 打开页面...")
        driver.get(test_url)
        
        # 等待初始加载
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='&Product=']"))
        )
        
        start_time = time.time()
        final_count = fast_load_products(driver)
        
        # 提取产品链接
        products = driver.execute_script("""
            return Array.from(new Set(
                Array.from(document.querySelectorAll('a[href*="&Product="]'))
                    .filter(a => a.href.includes('/product/'))
                    .map(a => a.href)
            ));
        """)
        
        elapsed = time.time() - start_time
        
        print(f"\n✅ 完成!")
        print(f"  - 页面显示: {final_count} 个产品")
        print(f"  - 实际提取: {len(products)} 个链接")
        print(f"  - 用时: {elapsed:.1f} 秒")
        print(f"  - 速度: {len(products)/elapsed:.1f} 个/秒")
        
        if len(products) >= 145:
            print(f"\n🎉 成功！")
        else:
            print(f"\n⚠️  只获取了 {len(products)}/145 个产品")
            
    finally:
        print("\n等待3秒...")
        time.sleep(3)
        driver.quit()
        print("✅ 调试完成")


if __name__ == '__main__':
    debug_fast() 