#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
超高性能测试
===========
完全模拟 test_5099_improved.py 的简单流程
去除所有生产环境的额外开销
"""

import sys
import os
import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
LOG = logging.getLogger("ultra-fast")


def create_ultra_fast_driver():
    """创建超高性能驱动 (完全模仿test_5099_improved.py)"""
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(60)
    return driver


def smart_load_all_products_ultra(driver, target_count=5099):
    """超高性能智能加载 (完全复刻test_5099_improved.py)"""
    LOG.info("开始智能加载产品...")
    
    # 1. 初始滚动触发第一次加载
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(1)
    
    # 2. 记录产品数变化
    last_count = len(driver.find_elements(By.CSS_SELECTOR, "a[href*='&Product=']"))
    no_change_count = 0
    click_count = 0
    max_no_change = 10
    
    while True:
        current_count = len(driver.find_elements(By.CSS_SELECTOR, "a[href*='&Product=']"))
        LOG.info(f"当前产品数: {current_count}/{target_count} ({current_count/target_count*100:.1f}%)")
        
        # 检查是否达到目标
        if current_count >= target_count:
            LOG.info(f"✅ 达到目标！获取了全部 {current_count} 个产品")
            break
            
        # 检查是否有变化
        if current_count == last_count:
            no_change_count += 1
            current_max_no_change = max_no_change * 2 if current_count >= target_count * 0.95 else max_no_change
            if no_change_count >= current_max_no_change:
                LOG.warning(f"连续 {current_max_no_change} 次没有新产品，可能已达到限制（当前: {current_count}/{target_count}）")
                break
        else:
            no_change_count = 0
            last_count = current_count
            
        # 策略1：尝试点击"Show More"按钮 (完全复刻原版逻辑)
        try:
            button_selectors = [
                "button.more-results",
                "button.tp-button.more-results",
                "//button[contains(@class, 'more-results')]",
                "//button[contains(text(), 'Show more results')]",
                "//button[contains(text(), 'SHOW MORE RESULTS')]",
                "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'show more')]"
            ]
            
            button_found = False
            for selector in button_selectors:
                try:
                    if selector.startswith('//'):
                        button = driver.find_element(By.XPATH, selector)
                    else:
                        button = driver.find_element(By.CSS_SELECTOR, selector)
                        
                    if button.is_displayed() and button.is_enabled():
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                        time.sleep(0.5)
                        driver.execute_script("arguments[0].click();", button)
                        click_count += 1
                        LOG.info(f"✓ 第 {click_count} 次点击 Show More")
                        button_found = True
                        time.sleep(1.5)
                        break
                except:
                    continue
                    
            if not button_found:
                LOG.debug("未找到Show More按钮，尝试滚动...")
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1)
                
        except Exception as e:
            LOG.error(f"点击按钮时出错: {e}")
            
        # 策略2：抖动滚动
        if no_change_count >= 2:
            positions = [0.9, 1.0]
            for pos in positions:
                driver.execute_script(f"window.scrollTo(0, document.body.scrollHeight * {pos});")
                time.sleep(0.3)
                
        # 避免无限循环
        if click_count > 200:
            LOG.warning(f"已点击 {click_count} 次，停止加载")
            break
            
    return current_count


def extract_all_product_links_ultra(driver):
    """超高性能链接提取 (完全复刻test_5099_improved.py)"""
    links = driver.execute_script("""
        return Array.from(new Set(
            Array.from(document.querySelectorAll('a[href*="&Product="]'))
                .filter(a => a.href.includes('/product/'))
                .map(a => a.href)
        ));
    """)
    return links


def run_ultra_fast_test():
    url = (
        "https://www.traceparts.cn/en/search/traceparts-classification-"
        "electrical-electrical-protection-devices-circuit-breakers-"
        "molded-case-circuit-breakers-mccb?CatalogPath=TRACEPARTS%3ATP09004001008"
    )
    expected = 5099

    print("⚡ TraceParts 超高性能测试")
    print("=" * 80)
    print(f"测试 URL : {url}")
    print(f"目标产品数 : {expected}")
    print(f"算法来源 : 完全复刻 test_5099_improved.py")
    print(f"优化策略 : 去除所有生产环境开销")
    print()

    driver = create_ultra_fast_driver()
    start_time = time.time()
    
    try:
        # 直接访问目标页面 (不像生产环境先访问base页面)
        LOG.info("🌐 打开页面...")
        driver.get(url)
        
        # 等待初始加载
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='&Product=']"))
        )
        
        # 智能加载所有产品
        final_count = smart_load_all_products_ultra(driver, 5099)
        
        # 提取所有链接
        LOG.info("📦 提取产品链接...")
        all_links = extract_all_product_links_ultra(driver)
        
        elapsed = time.time() - start_time
        
        print("\n测试结果")
        print("-" * 80)
        print(f"页面显示产品数 : {final_count}")
        print(f"实际提取链接数 : {len(all_links)}")
        print(f"用时           : {elapsed:.1f} 秒 ({elapsed/60:.1f} 分钟)")
        if elapsed > 0:
            print(f"平均速度       : {len(all_links)/elapsed:.1f} 个/秒")
        print(f"完成率         : {len(all_links)/expected*100:.2f}%")

        # 显示前 5 个链接示例
        sample_count = min(5, len(all_links))
        print(f"\n示例链接 (前 {sample_count} 个)")
        for i in range(sample_count):
            print(f"{i+1:2d}. {all_links[i]}")

        # 性能评估
        if len(all_links) >= expected * 0.98:
            print("\n🎉 优秀: 获取了几乎全部产品！")
        elif len(all_links) >= expected * 0.9:
            print("\n✅ 良好: 获取了大部分产品。")
        elif len(all_links) >= expected * 0.7:
            print("\n⚠️  一般: 获取产品较多，可进一步优化。")
        else:
            print("\n❌ 需要优化: 获取产品不足。")

        # 性能分析
        print(f"\n⚡ 超高性能优化说明:")
        print(f"   - 直接访问目标页面 (vs 生产环境先访问base页面)")
        print(f"   - 跳过Cookie注入和Banner处理")
        print(f"   - 跳过网络状态监控")
        print(f"   - 简化日志系统")
        print(f"   - 完全复刻 test_5099_improved.py 算法")

    except Exception as e:
        LOG.error(f"发生错误: {e}")
        elapsed = time.time() - start_time
        print(f"失败用时: {elapsed:.1f} 秒")
        
    finally:
        driver.quit()
        print("\n✅ 测试完成")


if __name__ == "__main__":
    run_ultra_fast_test() 