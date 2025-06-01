#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
单页面产品提取测试
==================
测试特定页面的产品链接提取，诊断为什么只能获取部分产品
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from src.utils.browser_manager import create_browser_manager
from config.settings import Settings


def test_single_page_products():
    """测试单个页面的产品提取"""
    # 目标URL
    url = "https://www.traceparts.cn/en/search/traceparts-classification-electrical-electrical-protection-devices-circuit-breakers-transfer-switching-equipment-tse?CatalogPath=TRACEPARTS%3ATP09004001017"
    
    print(f"🎯 测试URL: {url}")
    print("=" * 80)
    
    # 创建浏览器管理器
    manager = create_browser_manager(pool_size=1)
    
    try:
        with manager.get_browser() as driver:
            print("📋 第一步：打开页面")
            driver.get(url)
            
            # 等待页面加载
            wait = WebDriverWait(driver, Settings.CRAWLER['timeout'])
            wait.until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
            time.sleep(3)  # 确保初始内容加载完成
            
            # 获取页面信息
            print("\n📊 页面信息：")
            
            # 尝试获取结果计数
            try:
                result_count_elements = driver.find_elements(By.CSS_SELECTOR, "[class*='result'], [class*='Result'], .search-results-count, .results-count")
                for elem in result_count_elements:
                    text = elem.text.strip()
                    if text and ('result' in text.lower() or '结果' in text):
                        print(f"  - 结果计数: {text}")
            except:
                pass
            
            # 第一次提取产品链接
            print("\n📋 第二步：初始产品链接提取")
            initial_links = extract_product_links(driver)
            print(f"  - 初始提取: {len(initial_links)} 个产品")
            
            # 尝试加载更多
            print("\n📋 第三步：尝试加载更多产品")
            
            # 方法1：查找并点击"Show More"按钮
            more_loaded = try_load_more_products(driver)
            
            # 方法2：滚动到底部触发加载
            if not more_loaded:
                print("  - 尝试滚动加载...")
                scroll_and_load(driver)
            
            # 再次提取
            print("\n📋 第四步：最终产品链接提取")
            final_links = extract_product_links(driver)
            print(f"  - 最终提取: {len(final_links)} 个产品")
            
            # 分析结果
            print("\n📊 分析结果：")
            print(f"  - 新增产品: {len(final_links) - len(initial_links)} 个")
            
            # 打印前5个和后5个链接
            if final_links:
                print("\n  前5个产品链接:")
                for i, link in enumerate(final_links[:5], 1):
                    print(f"    {i}. {link}")
                
                if len(final_links) > 10:
                    print("\n  后5个产品链接:")
                    for i, link in enumerate(final_links[-5:], len(final_links)-4):
                        print(f"    {i}. {link}")
            
            # 检查是否还有更多内容
            check_for_more_content(driver)
            
            # 保存页面源码用于分析
            save_page_source(driver)
            
    finally:
        manager.shutdown()
        print("\n✅ 测试完成")


def extract_product_links(driver):
    """提取产品链接"""
    links = []
    seen_urls = set()
    
    # 查找产品链接
    elements = driver.find_elements(By.CSS_SELECTOR, "a[href*='&Product=']")
    
    for element in elements:
        try:
            href = element.get_attribute('href') or ''
            if '&Product=' in href and href not in seen_urls:
                seen_urls.add(href)
                links.append(href)
        except:
            pass
    
    return links


def try_load_more_products(driver):
    """尝试点击"显示更多"按钮"""
    print("  - 查找'显示更多'按钮...")
    
    # 各种可能的按钮选择器
    button_selectors = [
        "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'show more')]",
        "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'load more')]",
        "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'view more')]",
        "//a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'show more')]",
        "//a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'load more')]",
        "//div[@class='show-more' or @class='load-more' or contains(@class, 'more-button')]",
        "//button[@class='btn-show-more' or contains(@class, 'load-more')]"
    ]
    
    clicked = False
    click_count = 0
    max_clicks = 10
    
    while click_count < max_clicks:
        button_found = False
        
        for selector in button_selectors:
            try:
                buttons = driver.find_elements(By.XPATH, selector)
                for button in buttons:
                    if button.is_displayed() and button.is_enabled():
                        # 滚动到按钮
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                        time.sleep(1)
                        
                        # 记录点击前的产品数
                        before_count = len(extract_product_links(driver))
                        
                        # 点击按钮
                        button.click()
                        print(f"    ✓ 点击了按钮 (第 {click_count + 1} 次)")
                        time.sleep(3)  # 等待加载
                        
                        # 检查是否加载了新产品
                        after_count = len(extract_product_links(driver))
                        if after_count > before_count:
                            print(f"    ✓ 加载了 {after_count - before_count} 个新产品")
                        
                        clicked = True
                        click_count += 1
                        button_found = True
                        break
            except Exception as e:
                continue
        
        if not button_found:
            break
    
    if clicked:
        print(f"  - 总共点击了 {click_count} 次'显示更多'按钮")
    else:
        print("  - 未找到'显示更多'按钮")
    
    return clicked


def scroll_and_load(driver):
    """滚动页面触发懒加载"""
    print("  - 开始滚动加载...")
    
    last_height = driver.execute_script("return document.body.scrollHeight")
    scroll_count = 0
    max_scrolls = 10
    
    while scroll_count < max_scrolls:
        # 记录滚动前的产品数
        before_count = len(extract_product_links(driver))
        
        # 滚动到底部
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        
        # 检查是否有新内容
        new_height = driver.execute_script("return document.body.scrollHeight")
        after_count = len(extract_product_links(driver))
        
        if new_height > last_height:
            print(f"    ✓ 页面高度增加: {last_height} -> {new_height}")
            last_height = new_height
        
        if after_count > before_count:
            print(f"    ✓ 新增 {after_count - before_count} 个产品")
        
        if new_height == last_height and after_count == before_count:
            # 没有新内容，尝试向上滚动一点再向下
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight - 500);")
            time.sleep(1)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
            
            # 再次检查
            final_height = driver.execute_script("return document.body.scrollHeight")
            if final_height == new_height:
                break
        
        scroll_count += 1
    
    print(f"  - 滚动了 {scroll_count} 次")


def check_for_more_content(driver):
    """检查是否还有更多内容的迹象"""
    print("\n📋 检查页面状态：")
    
    # 检查分页
    try:
        pagination = driver.find_elements(By.CSS_SELECTOR, "[class*='pagination'], [class*='Pagination'], .page-link, .page-item")
        if pagination:
            print("  - 发现分页元素")
            for elem in pagination[:5]:  # 只打印前5个
                print(f"    • {elem.tag_name}: {elem.text.strip()}")
    except:
        pass
    
    # 检查加载指示器
    try:
        loaders = driver.find_elements(By.CSS_SELECTOR, "[class*='loader'], [class*='loading'], [class*='spinner']")
        visible_loaders = [l for l in loaders if l.is_displayed()]
        if visible_loaders:
            print(f"  - 发现 {len(visible_loaders)} 个可见的加载指示器")
    except:
        pass
    
    # 检查是否有禁用的按钮
    try:
        disabled_buttons = driver.find_elements(By.CSS_SELECTOR, "button[disabled], a.disabled")
        if disabled_buttons:
            print(f"  - 发现 {len(disabled_buttons)} 个禁用的按钮")
    except:
        pass


def save_page_source(driver):
    """保存页面源码供分析"""
    try:
        import os
        from datetime import datetime
        
        # 创建调试目录
        debug_dir = Settings.RESULTS_DIR / 'debug'
        debug_dir.mkdir(exist_ok=True)
        
        # 保存HTML
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        html_file = debug_dir / f'page_source_{timestamp}.html'
        
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(driver.page_source)
        
        print(f"\n💾 页面源码已保存到: {html_file}")
        
        # 同时保存截图
        screenshot_file = debug_dir / f'page_screenshot_{timestamp}.png'
        driver.save_screenshot(str(screenshot_file))
        print(f"📸 页面截图已保存到: {screenshot_file}")
        
    except Exception as e:
        print(f"保存页面源码失败: {e}")


if __name__ == '__main__':
    test_single_page_products() 