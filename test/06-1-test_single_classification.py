#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 06-1  —— 测试单个分类目录的链接提取
专门测试特定URL的分类链接抓取能力
"""

import os
import json
import time
import logging
from datetime import datetime
from collections import defaultdict
from typing import Dict, List
from bs4 import BeautifulSoup

# Selenium
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, WebDriverException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
LOG = logging.getLogger("test-06-1")

# 测试URL - 修正为.cn域名
TEST_URL = "https://www.traceparts.cn/en/search/traceparts-classification-mechanical-components-bearings-bearing-blocks-flanged-block-bearings?CatalogPath=TRACEPARTS%3ATP01002002002"

EXCLUDE_PATTERNS = [
    "sign-in", "sign-up", "login", "register", "javascript:", "mailto:", "#"
]


def prepare_driver() -> webdriver.Chrome:
    """准备Chrome驱动"""
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    driver = webdriver.Chrome(options=chrome_options)
    driver.set_page_load_timeout(40)
    return driver


def scroll_full(driver):
    """滚动页面到底部，确保所有内容加载"""
    LOG.info("🔄 开始滚动页面...")
    last_height = driver.execute_script("return document.body.scrollHeight")
    scroll_count = 0
    
    while True:
        # 滚动到底部
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        
        # 计算新的滚动高度并与之前的高度进行比较
        new_height = driver.execute_script("return document.body.scrollHeight")
        scroll_count += 1
        
        LOG.info(f"   滚动第 {scroll_count} 次: {last_height} -> {new_height}")
        
        if new_height == last_height:
            break
        last_height = new_height
        
        # 防止无限循环
        if scroll_count > 10:
            LOG.warning("   滚动次数过多，停止滚动")
            break
    
    # 滚动回顶部
    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(1)
    LOG.info("✅ 页面滚动完成")


def extract_all_links(driver) -> List[Dict]:
    """提取页面中的所有链接"""
    LOG.info("🔗 开始提取页面中的所有链接...")
    
    # 多种CSS选择器
    selectors = [
        "a[href*='traceparts-classification-']",  # test-06使用的选择器
        "a[href*='classification']",              # 更宽泛的分类链接
        "a[href*='CatalogPath']",                 # 包含CatalogPath的链接
        "a",                                      # 所有链接
    ]
    
    all_links = {}
    
    for selector in selectors:
        elements = driver.find_elements(By.CSS_SELECTOR, selector)
        LOG.info(f"   选择器 '{selector}' 找到 {len(elements)} 个元素")
        
        for el in elements:
            href = el.get_attribute('href') or ""
            text = el.text.strip()
            
            if not href or any(pat in href.lower() for pat in EXCLUDE_PATTERNS):
                continue
                
            # 存储链接信息
            if href not in all_links:
                all_links[href] = {
                    'url': href,
                    'text': text,
                    'selector': selector,
                    'is_classification': 'traceparts-classification-' in href,
                    'has_catalog_path': 'CatalogPath=' in href
                }
    
    LOG.info(f"✅ 总共找到 {len(all_links)} 个唯一链接")
    return list(all_links.values())


def analyze_url(url: str) -> Dict:
    """分析URL的结构"""
    analysis = {
        'url': url,
        'domain': '',
        'path': '',
        'catalog_path': '',
        'code': '',
        'level': 0,
        'is_classification': False
    }
    
    try:
        # 提取域名
        if '://' in url:
            analysis['domain'] = url.split('://')[1].split('/')[0]
        
        # 提取路径
        if '/search/' in url:
            analysis['path'] = url.split('/search/')[1].split('?')[0]
        
        # 提取CatalogPath
        if 'CatalogPath=TRACEPARTS%3A' in url:
            analysis['catalog_path'] = url.split('CatalogPath=TRACEPARTS%3A')[1].split('&')[0]
            analysis['code'] = analysis['catalog_path']
        
        # 判断是否为分类链接
        analysis['is_classification'] = 'traceparts-classification-' in url
        
        # 分析层级
        if analysis['code']:
            if analysis['code'] == 'TRACEPARTS':
                analysis['level'] = 1
            elif analysis['code'].startswith('TP'):
                code = analysis['code'][2:]  # 去掉'TP'
                if len(code) <= 2:
                    analysis['level'] = 2
                else:
                    # 每3位一个层级
                    analysis['level'] = 2 + len(code) // 3
        
    except Exception as e:
        LOG.warning(f"分析URL失败: {e}")
    
    return analysis


def test_specific_url():
    """测试特定URL"""
    if not SELENIUM_AVAILABLE:
        LOG.error("❌ Selenium 未安装，无法运行测试！")
        return False
    
    driver = None
    try:
        driver = prepare_driver()
        
        LOG.info(f"🌐 测试URL: {TEST_URL}")
        LOG.info("=" * 80)
        
        # 访问页面
        LOG.info("🔄 正在加载页面...")
        driver.get(TEST_URL)
        
        # 等待页面加载
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.TAG_NAME, 'body'))
        )
        time.sleep(3)
        
        # 检查页面基本信息
        title = driver.title
        current_url = driver.current_url
        LOG.info(f"📄 页面标题: {title}")
        LOG.info(f"🔗 当前URL: {current_url}")
        
        # 检查是否被重定向
        if current_url != TEST_URL:
            LOG.warning(f"⚠️  页面被重定向: {TEST_URL} -> {current_url}")
        
        # 滚动页面
        scroll_full(driver)
        
        # 提取所有链接
        links = extract_all_links(driver)
        
        # 分析链接
        LOG.info("\n📊 链接分析结果:")
        LOG.info("=" * 50)
        
        classification_links = []
        catalog_links = []
        other_links = []
        
        for link in links:
            analysis = analyze_url(link['url'])
            link.update(analysis)
            
            if link['is_classification']:
                classification_links.append(link)
            elif link['has_catalog_path']:
                catalog_links.append(link)
            else:
                other_links.append(link)
        
        LOG.info(f"📋 分类链接 (traceparts-classification-): {len(classification_links)}")
        LOG.info(f"📋 目录链接 (CatalogPath): {len(catalog_links)}")
        LOG.info(f"📋 其他链接: {len(other_links)}")
        
        # 详细显示分类链接
        if classification_links:
            LOG.info(f"\n🔍 分类链接详情 (前10个):")
            for i, link in enumerate(classification_links[:10]):
                LOG.info(f"  {i+1}. {link['text'][:50]}...")
                LOG.info(f"      Code: {link['code']}, Level: {link['level']}")
                LOG.info(f"      URL: {link['url']}")
        
        # 详细显示目录链接
        if catalog_links:
            LOG.info(f"\n🔍 目录链接详情 (前10个):")
            for i, link in enumerate(catalog_links[:10]):
                LOG.info(f"  {i+1}. {link['text'][:50]}...")
                LOG.info(f"      Code: {link['code']}, Level: {link['level']}")
                LOG.info(f"      URL: {link['url']}")
        
        # 按层级统计
        level_stats = defaultdict(int)
        for link in classification_links + catalog_links:
            if link['level'] > 0:
                level_stats[link['level']] += 1
        
        if level_stats:
            LOG.info(f"\n📊 层级统计:")
            for level in sorted(level_stats.keys()):
                LOG.info(f"   Level {level}: {level_stats[level]} 个链接")
        
        # 保存结果
        result = {
            'test_url': TEST_URL,
            'current_url': current_url,
            'title': title,
            'timestamp': datetime.now().isoformat(),
            'total_links': len(links),
            'classification_links': len(classification_links),
            'catalog_links': len(catalog_links),
            'level_stats': dict(level_stats),
            'links': links[:50]  # 只保存前50个链接避免文件过大
        }
        
        # 保存到文件
        result_file = "results/test_06_1_single_classification.json"
        os.makedirs("results", exist_ok=True)
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        LOG.info(f"\n💾 结果已保存到: {result_file}")
        
        # 总结
        LOG.info(f"\n✅ 测试完成!")
        LOG.info(f"   总链接数: {len(links)}")
        LOG.info(f"   分类链接: {len(classification_links)}")
        LOG.info(f"   目录链接: {len(catalog_links)}")
        
        return True
        
    except Exception as e:
        LOG.error(f"❌ 测试失败: {e}")
        return False
        
    finally:
        if driver:
            driver.quit()


def main():
    """主函数"""
    LOG.info("🚀 开始测试单个分类目录...")
    LOG.info("=" * 80)
    
    success = test_specific_url()
    
    if success:
        LOG.info("✅ 测试成功完成!")
    else:
        LOG.error("❌ 测试失败!")
    
    return success


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)