#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 08 对比版 —— 测试不同配置的效果
==========================================
对比：.com vs .cn，登录 vs 无登录，不同PageSize等
"""

import os
import re
import sys
import json
import time
import logging
from urllib.parse import urlparse, parse_qs
from pathlib import Path

# 添加项目根目录到路径
sys.path.append(str(Path(__file__).parent.parent))

# Selenium
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException

# 导入配置
from config.settings import Settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
LOG = logging.getLogger("test-08-comparison")


def prepare_driver(headless=True) -> "webdriver.Chrome":
    """配置Chrome驱动"""
    chrome_options = Options()
    if headless:
        chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    driver = webdriver.Chrome(options=chrome_options)
    driver.set_page_load_timeout(40)
    return driver


def simple_login(driver, email, password):
    """简单登录"""
    try:
        LOG.info("🔐 尝试登录...")
        driver.get("https://www.traceparts.cn/en/sign-in")
        time.sleep(3)
        
        # 输入邮箱
        email_input = driver.find_element(By.CSS_SELECTOR, "input[type='email']")
        email_input.clear()
        email_input.send_keys(email)
        
        # 输入密码
        password_input = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
        password_input.clear()
        password_input.send_keys(password)
        
        # 点击登录
        login_btn = driver.find_element(By.CSS_SELECTOR, "button:has-text('Sign in'), button[type='submit']")
        login_btn.click()
        time.sleep(5)
        
        # 检查是否成功
        current_url = driver.current_url
        if "sign-in" not in current_url.lower():
            LOG.info("✅ 登录成功！")
            return True
        else:
            LOG.warning("⚠️ 登录可能失败")
            return False
    except Exception as e:
        LOG.error(f"❌ 登录失败: {e}")
        return False


def test_configuration(config_name, url, use_login=False, page_size=None):
    """测试特定配置"""
    LOG.info(f"\n{'='*60}")
    LOG.info(f"🧪 测试配置: {config_name}")
    LOG.info(f"   URL: {url}")
    LOG.info(f"   登录: {'是' if use_login else '否'}")
    LOG.info(f"   PageSize: {page_size or '默认'}")
    LOG.info(f"{'='*60}")
    
    driver = prepare_driver(headless=False)  # 有头模式便于调试
    
    try:
        # 登录（如果需要）
        if use_login:
            auth_config = Settings.AUTH['accounts'][0]
            simple_login(driver, auth_config['email'], auth_config['password'])
        
        # 添加PageSize参数
        test_url = url
        if page_size:
            separator = '&' if '?' in url else '?'
            test_url = f"{url}{separator}PageSize={page_size}"
        
        LOG.info(f"🌐 访问: {test_url}")
        driver.get(test_url)
        
        # 等待页面加载
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
        )
        time.sleep(5)
        
        # 检查初始产品数量
        initial_products = len(driver.find_elements(By.CSS_SELECTOR, "a[href*='&Product=']"))
        LOG.info(f"📊 初始产品数量: {initial_products}")
        
        # 快速测试：滚动一次
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)
        
        after_scroll = len(driver.find_elements(By.CSS_SELECTOR, "a[href*='&Product=']"))
        LOG.info(f"📊 滚动后产品数量: {after_scroll}")
        
        # 检查Show More按钮
        try:
            show_more_btn = driver.find_element(By.XPATH, "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'show more')]")
            if show_more_btn.is_displayed() and show_more_btn.is_enabled():
                LOG.info("✅ 找到Show More按钮")
                
                # 尝试点击一次
                try:
                    driver.execute_script("arguments[0].click();", show_more_btn)
                    time.sleep(5)
                    after_click = len(driver.find_elements(By.CSS_SELECTOR, "a[href*='&Product=']"))
                    LOG.info(f"📊 点击Show More后: {after_click}")
                except Exception as e:
                    LOG.warning(f"⚠️ 点击Show More失败: {e}")
            else:
                LOG.info("❌ Show More按钮不可用")
        except NoSuchElementException:
            LOG.info("❌ 未找到Show More按钮")
        
        # 最终统计
        final_products = len(driver.find_elements(By.CSS_SELECTOR, "a[href*='&Product=']"))
        LOG.info(f"🔗 最终产品数量: {final_products}")
        
        return {
            'config': config_name,
            'initial': initial_products,
            'after_scroll': after_scroll,
            'final': final_products,
            'url': test_url
        }
        
    except Exception as e:
        LOG.error(f"❌ 测试失败: {e}")
        return {
            'config': config_name,
            'error': str(e),
            'url': test_url
        }
    finally:
        driver.quit()


def main():
    """主函数 - 对比测试不同配置"""
    
    # 测试URL
    base_url_com = "https://www.traceparts.com/en/search/traceparts-classification-mechanical-components-bearings-bearing-blocks-flanged-block-bearings?CatalogPath=TRACEPARTS%3ATP01002002002"
    base_url_cn = "https://www.traceparts.cn/en/search/traceparts-classification-mechanical-components-bearings-bearing-blocks-flanged-block-bearings?CatalogPath=TRACEPARTS%3ATP01002002002"
    
    # 测试配置
    test_configs = [
        ("原始(.com, 无登录)", base_url_com, False, None),
        ("CN域名(无登录)", base_url_cn, False, None),
        ("CN域名+登录", base_url_cn, True, None),
        ("CN域名+登录+大PageSize", base_url_cn, True, 200),
    ]
    
    results = []
    
    for config_name, url, use_login, page_size in test_configs:
        result = test_configuration(config_name, url, use_login, page_size)
        results.append(result)
        
        # 等待一下再进行下一个测试
        time.sleep(3)
    
    # 输出对比结果
    LOG.info(f"\n{'='*80}")
    LOG.info("📊 对比测试结果汇总")
    LOG.info(f"{'='*80}")
    
    for result in results:
        if 'error' in result:
            LOG.info(f"❌ {result['config']}: 失败 - {result['error']}")
        else:
            LOG.info(f"✅ {result['config']}: 初始={result['initial']}, 滚动后={result['after_scroll']}, 最终={result['final']}")
    
    # 保存结果
    os.makedirs("results", exist_ok=True)
    with open("results/test_08_comparison.json", 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    LOG.info(f"\n✅ 对比测试完成，结果已保存到 results/test_08_comparison.json")


if __name__ == "__main__":
    main()