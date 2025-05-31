#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 09  —— 批量抓取所有叶节点分类的产品详情链接

步骤概述：
1. 读取 results/traceparts_tree_leaves.jsonl，每行一个叶节点（含 name / url / code）。
2. 针对每个叶节点 url，复用 **测试 08** 的逻辑，加载全部结果 → 提取 &Product= 链接。
3. 结果保存到 results/products/product_links_<TPcode>.json，如果文件已存在则跳过。
4. 支持线程池并发（默认 20），可通过 CLI --workers 指定。

运行：
$ python test/09-test_batch_leaf_product_links.py [--leaves path] [--workers 6]
或使用 Makefile：
$ make test-09
"""

import os
import re
import sys
import json
import time
import argparse
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Set
from urllib.parse import urlparse, parse_qs

# Selenium (与 test-08 相同)
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException, StaleElementReferenceException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
LOG = logging.getLogger("test-09")

PRODUCT_LINK_PATTERN = re.compile(r"[?&]Product=([0-9\-]+)")

# ---------- Selenium helpers ---------- #

def prepare_driver() -> "webdriver.Chrome":
    opt = Options()
    opt.add_argument('--headless')
    opt.add_argument('--no-sandbox')
    opt.add_argument('--disable-dev-shm-usage')
    opt.add_argument('--disable-gpu')
    opt.add_argument('--window-size=1920,1080')
    opt.add_argument('--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    drv = webdriver.Chrome(options=opt)
    drv.set_page_load_timeout(40)
    return drv


def scroll_full(driver: "webdriver.Chrome"):
    last_h = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1.1)
        new_h = driver.execute_script("return document.body.scrollHeight")
        if new_h == last_h:
            time.sleep(0.6)
            if driver.execute_script("return document.body.scrollHeight") == last_h:
                break
        last_h = new_h


def click_show_more_if_any(driver: "webdriver.Chrome") -> bool:
    try:
        btn = driver.find_element(By.XPATH, "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'show more')]")
        if btn and btn.is_displayed() and btn.is_enabled():
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
            btn.click()
            time.sleep(1.8)
            return True
    except NoSuchElementException:
        pass
    except (ElementClickInterceptedException, StaleElementReferenceException):
        time.sleep(0.8)
    return False


def load_all_results(driver: "webdriver.Chrome"):
    while True:
        scroll_full(driver)
        if not click_show_more_if_any(driver):
            break


def extract_products_on_page(driver: "webdriver.Chrome", seen: Set[str]) -> List[str]:
    links = []
    nodes = driver.find_elements(By.CSS_SELECTOR, "a[href*='&Product=']")
    for el in nodes:
        href = el.get_attribute('href') or ""
        if not href or href in seen:
            continue
        if '&Product=' not in href:
            continue
        if '/product/' not in urlparse(href).path:
            continue
        seen.add(href)
        links.append(href)
    return links

# ---------- Core logic per leaf ---------- #

def scrape_leaf(leaf: Dict, out_dir: str) -> Dict:
    """返回 {'code': code, 'total': n, 'ok': bool}"""
    code = leaf.get('code') or 'UNKNOWN'
    out_file = os.path.join(out_dir, f"product_links_{code}.json")
    if os.path.exists(out_file):
        LOG.info(f"🔹 已存在 {code}, 跳过")
        with open(out_file, 'r') as f:
            data = json.load(f)
        return {'code': code, 'total': data.get('total', 0), 'ok': True, 'skipped': True}

    driver = prepare_driver()
    try:
        url = leaf['url']
        driver.get(url)
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.CSS_SELECTOR, "body")))
        load_all_results(driver)
        links = extract_products_on_page(driver, set())
        os.makedirs(out_dir, exist_ok=True)
        with open(out_file, 'w', encoding='utf-8') as f:
            json.dump({
                'leaf_name': leaf.get('name'),
                'leaf_url': url,
                'tp_code': code,
                'total': len(links),
                'links': links
            }, f, ensure_ascii=False, indent=2)
        LOG.info(f"✅ [{code}] 抓取 {len(links)} 条")
        return {'code': code, 'total': len(links), 'ok': True}
    except Exception as e:
        LOG.error(f"❌ [{code}] 失败: {e}")
        return {'code': code, 'total': 0, 'ok': False, 'error': str(e)}
    finally:
        driver.quit()

# ---------- Main ---------- #

def main():
    if not SELENIUM_AVAILABLE:
        LOG.error("Selenium 未安装，无法运行 test-09！")
        return False

    parser = argparse.ArgumentParser(description="批量抓取 TraceParts 叶节点产品链接")
    parser.add_argument('--leaves', default='results/traceparts_tree_leaves.jsonl', help='叶节点 jsonl 文件')
    parser.add_argument('--workers', type=int, default=16, help='并发线程数 (默认 20)')
    args = parser.parse_args()

    leaves_path = args.leaves
    if not os.path.isfile(leaves_path):
        LOG.error(f"叶节点文件不存在: {leaves_path}")
        return False

    out_dir = os.path.join('results', 'products')
    os.makedirs(out_dir, exist_ok=True)

    # 读取所有叶节点
    leaves = []
    with open(leaves_path, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                leaves.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    LOG.info(f"📄 叶节点总数: {len(leaves)}")

    ok_count = 0
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        future_to_code = {executor.submit(scrape_leaf, leaf, out_dir): leaf.get('code') for leaf in leaves}
        for future in as_completed(future_to_code):
            res = future.result()
            if res.get('ok'):
                ok_count += 1
    LOG.info(f"🌟 完成 {ok_count}/{len(leaves)} 个叶节点抓取")
    return True


if __name__ == '__main__':
    success = main()
    print("✅ test-09 成功" if success else "❌ test-09 失败") 