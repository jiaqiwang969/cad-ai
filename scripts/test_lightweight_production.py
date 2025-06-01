#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
轻量级生产环境测试
================
在保持基本功能的同时最大化性能
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

# 设置简化的日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
LOG = logging.getLogger("lightweight")


class LightweightProductCrawler:
    """轻量级产品爬取器 - 平衡性能和功能"""
    
    def __init__(self):
        self.max_retry = 3
    
    def _create_optimized_driver(self):
        """创建优化的驱动 (平衡性能和稳定性)"""
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        
        # 固定User-Agent (性能优化)
        options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # 保留少量反检测选项 (稳定性)
        options.add_argument('--disable-blink-features=AutomationControlled')
        
        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(60)  # 60秒超时
        driver.implicitly_wait(5)
        
        return driver
    
    def _click_show_more_simple(self, driver) -> bool:
        """简化的Show More按钮点击"""
        selectors = [
            "button.more-results",
            "button.tp-button.more-results", 
            "//button[contains(@class, 'more-results')]",
            "//button[contains(text(), 'Show more results')]"
        ]
        
        for sel in selectors:
            try:
                elem = driver.find_element(By.XPATH, sel) if sel.startswith('//') else driver.find_element(By.CSS_SELECTOR, sel)
                if elem.is_displayed() and elem.is_enabled():
                    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", elem)
                    time.sleep(0.3)
                    driver.execute_script("arguments[0].click();", elem)
                    return True
            except:
                continue
        return False
    
    def _load_all_results_optimized(self, driver, target_count=5099):
        """优化的产品加载 (简化版本)"""
        LOG.info("开始加载产品...")
        
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)
        
        last_count = len(driver.find_elements(By.CSS_SELECTOR, "a[href*='&Product=']"))
        no_change_count = 0
        click_count = 0
        max_no_change = 10
        
        while True:
            current_count = len(driver.find_elements(By.CSS_SELECTOR, "a[href*='&Product=']"))
            
            # 只在有显著变化时记录日志
            if current_count != last_count:
                LOG.info(f"当前产品数: {current_count}")
            
            if current_count >= target_count:
                LOG.info(f"✅ 达到目标！获取了 {current_count} 个产品")
                break
                
            if current_count == last_count:
                no_change_count += 1
                if no_change_count >= max_no_change:
                    LOG.info(f"停止加载，最终产品数: {current_count}")
                    break
            else:
                no_change_count = 0
                last_count = current_count
            
            # 尝试点击Show More
            if self._click_show_more_simple(driver):
                click_count += 1
                if click_count % 20 == 0:  # 每20次记录一次
                    LOG.info(f"已点击 Show More {click_count} 次")
                time.sleep(1.5)
            else:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1)
            
            # 简化的抖动滚动
            if no_change_count >= 2:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.95);")
                time.sleep(0.2)
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(0.2)
            
            if click_count > 200:
                LOG.warning(f"点击次数过多，停止加载")
                break
                
        return current_count
    
    def extract_product_links(self, url: str, target_count: int = 5099):
        """提取产品链接 (带简化重试)"""
        for attempt in range(1, self.max_retry + 1):
            driver = None
            try:
                LOG.info(f"尝试 {attempt}/{self.max_retry}: {url}")
                
                # 创建驱动
                driver = self._create_optimized_driver()
                
                # 直接访问目标页面
                driver.get(url)
                
                # 等待页面加载
                WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='&Product=']"))
                )
                
                # 加载所有产品
                final_count = self._load_all_results_optimized(driver, target_count)
                
                # 提取链接
                links = driver.execute_script("""
                    return Array.from(new Set(
                        Array.from(document.querySelectorAll('a[href*="&Product="]'))
                            .filter(a => a.href.includes('/product/'))
                            .map(a => a.href)
                    ));
                """)
                
                LOG.info(f"成功提取 {len(links)} 个产品链接")
                return links
                
            except Exception as e:
                LOG.warning(f"尝试 {attempt} 失败: {e}")
                if attempt < self.max_retry:
                    time.sleep(2)  # 简单的重试延迟
                else:
                    LOG.error("达到最大重试次数，提取失败")
                    return []
            finally:
                if driver:
                    driver.quit()
        
        return []


def run_lightweight_test():
    url = (
        "https://www.traceparts.cn/en/search/traceparts-classification-"
        "electrical-electrical-protection-devices-circuit-breakers-"
        "molded-case-circuit-breakers-mccb?CatalogPath=TRACEPARTS%3ATP09004001008"
    )
    expected = 5099

    print("🚀 TraceParts 轻量级生产环境测试")
    print("=" * 80)
    print(f"测试 URL : {url}")
    print(f"目标产品数 : {expected}")
    print(f"爬取器类型 : LightweightProductCrawler")
    print(f"特点       : 平衡性能和功能完整性")
    print()

    crawler = LightweightProductCrawler()

    start = time.time()
    links = crawler.extract_product_links(url, expected)
    elapsed = time.time() - start

    print("\n测试结果")
    print("-" * 80)
    print(f"获取产品数 : {len(links)}")
    print(f"用时       : {elapsed:.1f} 秒 ({elapsed/60:.1f} 分钟)")
    if elapsed > 0:
        print(f"平均速度   : {len(links)/elapsed:.1f} 个/秒")
    print(f"完成率     : {len(links)/expected*100:.2f}%")

    # 显示前 5 个链接示例
    sample_count = min(5, len(links))
    print(f"\n示例链接 (前 {sample_count} 个)")
    for i in range(sample_count):
        print(f"{i+1:2d}. {links[i]}")

    # 性能评估
    if len(links) >= expected * 0.98:
        print("\n🎉 优秀: 获取了几乎全部产品！")
    elif len(links) >= expected * 0.9:
        print("\n✅ 良好: 获取了大部分产品。")
    elif len(links) >= expected * 0.7:
        print("\n⚠️  一般: 获取产品较多，可进一步优化。")
    else:
        print("\n❌ 需要优化: 获取产品不足。")

    # 优化说明
    print(f"\n🚀 轻量级生产环境特点:")
    print(f"   - 保留重试机制 (3次)")
    print(f"   - 保留基本反检测 (稳定性)")
    print(f"   - 去除浏览器池 (性能)")
    print(f"   - 简化日志系统 (性能)")
    print(f"   - 固定超时和User-Agent (性能)")
    print(f"   - 直接页面访问 (性能)")

    print("\n✅ 测试完成")


if __name__ == "__main__":
    run_lightweight_test() 