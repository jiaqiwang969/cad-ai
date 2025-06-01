#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
改进版5099产品测试
==================
基于test-08的代码，结合优化策略获取所有产品
"""

import os
import sys
import json
import time
import logging
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
LOG = logging.getLogger("test-5099-improved")


def prepare_driver():
    """配置 Chrome 驱动（无头模式）"""
    chrome_options = Options()
    chrome_options.add_argument('--headless')  # 启用无头模式
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    driver = webdriver.Chrome(options=chrome_options)
    driver.set_page_load_timeout(60)
    return driver


def smart_load_all_products(driver, target_count=5099):
    """智能加载所有产品，结合多种策略"""
    LOG.info("开始智能加载产品...")
    
    # 1. 初始滚动触发第一次加载
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(1)
    
    # 2. 记录产品数变化
    last_count = len(driver.find_elements(By.CSS_SELECTOR, "a[href*='&Product=']"))
    no_change_count = 0
    click_count = 0
    max_no_change = 10  # 增加到10次，给更多机会
    
    while True:
        current_count = len(driver.find_elements(By.CSS_SELECTOR, "a[href*='&Product=']"))
        LOG.info(f"当前产品数: {current_count}/{target_count} ({current_count/target_count*100:.1f}%)")
        
        # 检查是否达到目标
        if current_count >= target_count:  # 达到100%才停止
            LOG.info(f"✅ 达到目标！获取了全部 {current_count} 个产品")
            break
            
        # 检查是否有变化
        if current_count == last_count:
            no_change_count += 1
            # 如果接近目标，给更多机会
            current_max_no_change = max_no_change * 2 if current_count >= target_count * 0.95 else max_no_change
            if no_change_count >= current_max_no_change:
                LOG.warning(f"连续 {current_max_no_change} 次没有新产品，可能已达到限制（当前: {current_count}/{target_count}）")
                break
        else:
            no_change_count = 0
            last_count = current_count
            
        # 策略1：尝试点击"Show More"按钮
        try:
            # 使用多种选择器查找按钮
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
                        # 滚动到按钮位置
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                        time.sleep(0.5)
                        
                        # 使用JavaScript点击（更可靠）
                        driver.execute_script("arguments[0].click();", button)
                        click_count += 1
                        LOG.info(f"✓ 第 {click_count} 次点击 Show More")
                        button_found = True
                        
                        # 等待新产品加载
                        time.sleep(1.5)
                        break
                except:
                    continue
                    
            if not button_found:
                # 没找到按钮，尝试滚动
                LOG.debug("未找到Show More按钮，尝试滚动...")
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1)
                
        except Exception as e:
            LOG.error(f"点击按钮时出错: {e}")
            
        # 策略2：如果长时间没有进展，尝试不同的滚动位置
        if no_change_count >= 2:
            positions = [0.9, 1.0]
            for pos in positions:
                driver.execute_script(f"window.scrollTo(0, document.body.scrollHeight * {pos});")
                time.sleep(0.3)
                
        # 避免无限循环
        if click_count > 200:  # 5099/40 ≈ 128，给予充足余量
            LOG.warning(f"已点击 {click_count} 次，停止加载")
            break
            
    return current_count


def extract_all_product_links(driver):
    """提取所有产品链接"""
    links = driver.execute_script("""
        return Array.from(new Set(
            Array.from(document.querySelectorAll('a[href*="&Product="]'))
                .filter(a => a.href.includes('/product/'))
                .map(a => a.href)
        ));
    """)
    return links


def tp_code_from_url(url):
    """从URL提取TP编码"""
    qs_part = urlparse(url).query
    params = parse_qs(qs_part)
    cp = params.get('CatalogPath', [''])[0]
    if cp.startswith('TRACEPARTS:'):
        cp = cp.split(':', 1)[1]
    return cp


def main():
    # 目标URL
    url = "https://www.traceparts.cn/en/search/traceparts-classification-electrical-electrical-protection-devices-circuit-breakers-molded-case-circuit-breakers-mccb?CatalogPath=TRACEPARTS%3ATP09004001008"
    tp_code = tp_code_from_url(url)
    
    LOG.info(f"🎯 测试URL: {url}")
    LOG.info(f"📌 TP编码: {tp_code}")
    LOG.info(f"🎯 目标: 5099个产品")
    
    driver = prepare_driver()
    start_time = time.time()
    
    try:
        # 打开页面
        LOG.info("🌐 打开页面...")
        driver.get(url)
        
        # 等待初始加载
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='&Product=']"))
        )
        
        # 智能加载所有产品
        final_count = smart_load_all_products(driver, 5099)
        
        # 提取所有链接
        LOG.info("📦 提取产品链接...")
        all_links = extract_all_product_links(driver)
        
        elapsed = time.time() - start_time
        
        # 输出结果
        LOG.info(f"\n{'='*60}")
        LOG.info(f"✅ 完成！")
        LOG.info(f"  - 页面显示产品数: {final_count}")
        LOG.info(f"  - 实际提取链接数: {len(all_links)}")
        LOG.info(f"  - 用时: {elapsed:.1f} 秒")
        LOG.info(f"  - 速度: {len(all_links)/elapsed:.1f} 个/秒")
        LOG.info(f"  - 完成率: {len(all_links)/5099*100:.1f}%")
        
        # 保存结果
        os.makedirs("results", exist_ok=True)
        out_file = f"results/product_links_{tp_code}_improved.json"
        with open(out_file, 'w', encoding='utf-8') as f:
            json.dump({
                "url": url,
                "tp_code": tp_code,
                "total": len(all_links),
                "elapsed": elapsed,
                "links": all_links
            }, f, ensure_ascii=False, indent=2)
        LOG.info(f"💾 结果已保存到: {out_file}")
        
        # 评估
        if len(all_links) >= 5000:
            LOG.info("🎉 完美！获取了几乎所有产品")
        elif len(all_links) >= 4000:
            LOG.info("✅ 优秀！获取了大部分产品")
        elif len(all_links) >= 2000:
            LOG.info("⚠️ 一般！可能需要进一步优化")
        else:
            LOG.info("❌ 需要改进！")
            
        return True
        
    except Exception as e:
        LOG.error(f"发生错误: {e}")
        return False
        
    finally:
        driver.quit()


if __name__ == "__main__":
    success = main()
    print("✅ 测试成功" if success else "❌ 测试失败") 