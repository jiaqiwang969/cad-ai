#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 06  —— Selenium 递归/遍历方式抓取 TraceParts Classification 完整树状结构，
不依赖 AI，直接解析 DOM，输出全量 JSON。
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
LOG = logging.getLogger("test-06")

ROOT_URL = "https://www.traceparts.cn/en/search/traceparts-classification?CatalogPath=TRACEPARTS%3ATRACEPARTS"

EXCLUDE_PATTERNS = [
    "sign-in", "sign-up", "login", "register", "javascript:", "mailto:", "#"
]


def prepare_driver() -> webdriver.Chrome:
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


def scroll_full(driver: webdriver.Chrome):
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1.5)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height
    # 回到顶部
    driver.execute_script("window.scrollTo(0,0);")


def extract_links(driver: webdriver.Chrome) -> List[Dict]:
    elements = driver.find_elements(By.CSS_SELECTOR, "a[href*='traceparts-classification-']")
    LOG.info(f"🔗 共捕获 {len(elements)} 个包含 classification 的链接节点")
    records = []
    seen = set()

    def guess_name_from_href(href: str) -> str:
        try:
            if 'traceparts-classification-' in href:
                tail = href.split('traceparts-classification-')[1]
                path_part = tail.split('?')[0].strip('-')
                if path_part:
                    # 拿最后一个段落作为名称
                    last_seg = path_part.split('-')[-1]
                    return last_seg.replace('-', ' ').replace('_', ' ').title()
        except Exception:
            pass
        return "Unnamed"

    for el in elements:
        href = el.get_attribute('href') or ""
        # 可见文本
        raw_text = el.text.strip()
        if not href or any(pat in href.lower() for pat in EXCLUDE_PATTERNS):
            continue
        # 去重
        if href in seen:
            continue
        seen.add(href)

        name = raw_text
        # 如果可见文本为空，尝试其他属性
        if not name:
            alt_sources = [
                el.get_attribute('title'),
                el.get_attribute('aria-label'),
                el.get_attribute('data-original-title'),
                el.get_attribute('innerText'),
                el.get_attribute('textContent')
            ]
            for src in alt_sources:
                if src and src.strip():
                    name = src.strip()
                    break
        # 仍为空，解析 innerHTML 拿子元素文本
        if not name:
            inner_html = el.get_attribute('innerHTML') or ""
            soup = BeautifulSoup(inner_html, 'html.parser')
            txt = soup.get_text(" ", strip=True)
            if txt:
                name = txt
        # 仍为空，尝试从 href 推断
        if not name:
            name = guess_name_from_href(href)

        records.append({"name": name, "url": href})
    LOG.info(f"✅ 过滤后剩余 {len(records)} 条唯一分类链接，其中已填充名称")
    return records


def analyse_level(item_url: str) -> int:
    """根据 CatalogPath 的 TP 编码推断层级，高可靠：
    TP##                           -> L2 (主类目)
    TP##XXX                        -> L3 (1 组 3 位)
    TP##XXXYYY                     -> L4 (2 组)
    依此类推；若无符合规则，退回到基于 '-' 计数法。"""

    if "%3ATRACEPARTS" in item_url:
        return 1  # 根分类页面

    level_by_dash = None
    # 备用：'-' 计数
    try:
        tail = item_url.split('traceparts-classification-')[1]
        path_part = tail.split('?')[0].strip('-')
        if path_part:
            level_by_dash = len(path_part.split('-')) + 1  # L2 起
    except Exception:
        pass

    # CatalogPath 推断
    cat_path_part = None
    if "CatalogPath=TRACEPARTS%3A" in item_url:
        cat_path_part = item_url.split("CatalogPath=TRACEPARTS%3A")[1].split('&')[0]
    if cat_path_part and cat_path_part.startswith("TP"):
        code = cat_path_part[2:]
        if len(code) <= 2:  # TP01..TP14 等
            return 2
        # 剩余每 3 位一个深度
        depth_groups = len(code) // 3
        return 2 + depth_groups

    return level_by_dash if level_by_dash else 2


def build_tree(records: List[Dict]) -> List[Dict]:
    enriched = []
    for rec in records:
        level = analyse_level(rec['url'])
        rec['level'] = level
        enriched.append(rec)
    # sort by level then name
    enriched.sort(key=lambda x: (x['level'], x['name']))
    return enriched


def main():
    if not SELENIUM_AVAILABLE:
        LOG.error("Selenium 未安装，无法运行 test-06！")
        return False
    driver = prepare_driver()
    try:
        LOG.info(f"🌐 打开根分类页面: {ROOT_URL}")
        driver.get(ROOT_URL)
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
        time.sleep(4)
        scroll_full(driver)
        records = extract_links(driver)
        tree = build_tree(records)
        # 统计
        stats = defaultdict(int)
        for item in tree:
            stats[item['level']] += 1
        LOG.info("📊 层级统计:" + ", ".join([f"L{lv}:{cnt}" for lv,cnt in sorted(stats.items())]))
        # 保存
        result_file = "results/traceparts_classification_tree_full.json"
        os.makedirs("results", exist_ok=True)
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump({"total": len(tree), "records": tree, "stats": stats, "crawl_time": datetime.now().isoformat()}, f, ensure_ascii=False, indent=2)
        LOG.info(f"✅ 已保存完整分类树到 {result_file}")
        return True
    except Exception as e:
        LOG.error(f"❌ 抓取失败: {e}")
        return False
    finally:
        driver.quit()

if __name__ == "__main__":
    ok = main()
    print("✅ test-06 成功" if ok else "❌ test-06 失败") 