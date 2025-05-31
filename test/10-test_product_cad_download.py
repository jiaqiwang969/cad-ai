#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 10  —— 单产品页规格 + CAD 下载示例

说明：
1. 入口 URL 为某个具体产品（含 &Product=…）。默认示例：
   https://www.traceparts.cn/en/product/vuototecnica-caps-with-orings?Product=70-01102019-118491&PartNumber=00%2015%20273
2. 针对 Product selection 表格：支持分页；抓取 PartNumber、描述等参数。
3. 若行内存在 CAD 下载按钮，则点击 → 弹出格式列表 → 选择指定格式（默认 STEP）下载。
4. 下载文件保存到 results/cads/<PartNumber>/，并生成元数据 JSON。
5. 仅作 PoC：遇到复杂的『选择栏目』或多级过滤暂未递归。

运行：
$ python test/10-test_product_cad_download.py <product_url> [--format STEP]
$ make test-10
"""

import os
import re
import sys
import json
import csv
import time
import argparse
import logging
from urllib.parse import urlparse, parse_qs
from typing import List, Dict

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
LOG = logging.getLogger("test-10")

DOWNLOAD_DIR = os.path.abspath(os.path.join('results', 'cads_tmp'))

# ---------- Selenium helpers ---------- #

def prepare_driver() -> "webdriver.Chrome":
    opts = Options()
    opts.add_argument('--headless')
    opts.add_argument('--no-sandbox')
    opts.add_argument('--disable-dev-shm-usage')
    opts.add_argument('--disable-gpu')
    opts.add_argument('--window-size=1920,1080')
    prefs = {
        "download.default_directory": DOWNLOAD_DIR,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    }
    opts.add_experimental_option("prefs", prefs)
    driver = webdriver.Chrome(options=opts)
    driver.set_page_load_timeout(40)
    return driver

# ---------- Core ---------- #

CAD_BTN_SEL = "a[title*='CAD'], a[href*='CADDownload'], button.download-cad"


def wait_table_ready(driver):
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "table tbody tr"))
    )


def extract_rows(driver, headers: List[str]) -> List[Dict]:
    rows = []
    for tr in driver.find_elements(By.CSS_SELECTOR, "table tbody tr"):
        tds = tr.find_elements(By.TAG_NAME, 'td')
        if len(tds) < len(headers):
            continue  # 可能是空行或说明行
        cell_texts = [td.text.strip() for td in tds[:len(headers)]]
        row_map = dict(zip(headers, cell_texts))
        cad_btn = tr.find_elements(By.CSS_SELECTOR, CAD_BTN_SEL)
        # 取 PartNumber 列或首列作为部件号
        pn = row_map.get('Part Number') or row_map.get('PartNumber') or row_map.get('Part number') or cell_texts[0]
        rows.append({
            'data': row_map,
            'part_number': pn,
            'cad_btn': cad_btn[0] if cad_btn else None,
            'tr': tr
        })
    return rows


def click_and_choose_format(driver, btn, fmt_keyword="STEP AP203") -> str:
    """点击 CAD 按钮，选择指定格式并返回下载文件名（若成功）。"""
    try:
        btn.click()
    except (ElementClickInterceptedException, StaleElementReferenceException):
        driver.execute_script("arguments[0].click();", btn)
    # 等待格式弹窗出现
    try:
        WebDriverWait(driver, 15).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "div.modal-content, div#downloadModal"))
        )
    except TimeoutException:
        LOG.warning("格式弹窗未出现")
        return ""

    # 格式列表链接
    lower_kw = fmt_keyword.lower()
    links = driver.find_elements(By.CSS_SELECTOR, f"a[downloadfileformat*='{lower_kw}'], a[title*='{fmt_keyword}'], a:contains('{fmt_keyword}')")
    if not links:
        # 若未找到指定格式，则尝试任何可用格式
        links = driver.find_elements(By.CSS_SELECTOR, "a[downloadfileformat]")
    if not links:
        LOG.info("无可下载格式")
        driver.find_element(By.CSS_SELECTOR, "button.close, button[data-dismiss='modal']").click()
        return ""

    target = links[0]
    file_fmt = target.get_attribute('downloadfileformat') or target.text.strip()

    driver.execute_script("arguments[0].click();", target)
    time.sleep(2)
    driver.find_element(By.CSS_SELECTOR, "button.close, button[data-dismiss='modal']").click()
    LOG.debug(f"触发下载格式: {file_fmt}")
    return file_fmt


def wait_download_complete(before_files: set, timeout=60) -> str:
    start = time.time()
    while time.time() - start < timeout:
        files = set(os.listdir(DOWNLOAD_DIR))
        new_files = files - before_files
        if new_files:
            return new_files.pop()
        time.sleep(1)
    return ""


def get_headers(driver) -> List[str]:
    # 优先 thead
    heads = driver.find_elements(By.CSS_SELECTOR, "table thead th")
    if heads:
        return [h.text.strip() or f"Col{idx+1}" for idx, h in enumerate(heads)]
    # Fallback: 第一行 td 作为 header
    first_row_tds = driver.find_elements(By.CSS_SELECTOR, "table tbody tr:first-child td")
    return [td.text.strip() or f"Col{idx+1}" for idx, td in enumerate(first_row_tds)]


def process_product(url: str, fmt: str = "STEP"):
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    driver = prepare_driver()
    meta_out = {
        'product_url': url,
        'download_format': fmt,
        'specifications': []
    }
    csv_rows = []
    csv_header = []
    try:
        LOG.info(f"打开产品页: {url}")
        driver.get(url)
        wait_table_ready(driver)

        page_idx = 1
        while True:
            headers = csv_header or get_headers(driver)
            if not csv_header:
                csv_header = headers
            rows = extract_rows(driver, headers)
            LOG.info(f"- 第 {page_idx} 页规格数: {len(rows)}")

            for r in rows:
                spec = r['data'].copy()
                spec['cad_available'] = bool(r['cad_btn'])
                spec['cad_file'] = ''
                spec['part_number'] = r['part_number']
                if r['cad_btn']:
                    before = set(os.listdir(DOWNLOAD_DIR))
                    chosen_fmt = click_and_choose_format(driver, r['cad_btn'], fmt_keyword=fmt)
                    if chosen_fmt:
                        fname = wait_download_complete(before)
                        if fname:
                            dest_dir = os.path.join('results', 'cads', r['part_number'])
                            os.makedirs(dest_dir, exist_ok=True)
                            os.rename(os.path.join(DOWNLOAD_DIR, fname), os.path.join(dest_dir, fname))
                            spec['cad_file'] = os.path.join(dest_dir, fname)
                meta_out['specifications'].append(spec)
                # CSV 行：使用当前行所有 td 文本
                row_texts = [td.text.strip() for td in r['tr'].find_elements(By.TAG_NAME, 'td')]
                csv_rows.append([spec.get(h, '') for h in csv_header])

            # 翻页判定
            try:
                next_btn = driver.find_element(By.CSS_SELECTOR, "ul.pagination li:not(.disabled) a[aria-label='Next']")
                if next_btn and next_btn.is_enabled():
                    driver.execute_script("arguments[0].click();", next_btn)
                    time.sleep(2)
                    wait_table_ready(driver)
                    page_idx += 1
                    continue
            except NoSuchElementException:
                pass
            break  # 无下一页

        # 保存 meta json
        os.makedirs('results/products_meta', exist_ok=True)
        code = parse_qs(urlparse(url).query).get('Product', ['UNKNOWN'])[0]
        meta_path_json = f'results/products_meta/meta_{code}.json'
        with open(meta_path_json, 'w', encoding='utf-8') as f:
            json.dump(meta_out, f, ensure_ascii=False, indent=2)
        # 保存 CSV
        csv_path = f'results/products_meta/meta_{code}.csv'
        with open(csv_path, 'w', newline='', encoding='utf-8') as f_csv:
            writer = csv.writer(f_csv)
            if csv_header:
                writer.writerow(csv_header)
            writer.writerows(csv_rows)
        LOG.info(f"元数据保存完成 (JSON & CSV)")
    finally:
        driver.quit()

# ---------- CLI ---------- #

def main():
    if not SELENIUM_AVAILABLE:
        LOG.error("Selenium 未安装！")
        return False

    parser = argparse.ArgumentParser(description="单产品页规格 + CAD 下载示例")
    parser.add_argument('url', nargs='?', default="https://www.traceparts.cn/en/product/vuototecnica-caps-with-orings?Product=70-01102019-118491&PartNumber=00%2015%20273", help='产品页面 URL')
    parser.add_argument('--format', default='STEP AP203', help='首选下载格式，如 "STEP AP203"')
    args = parser.parse_args()

    process_product(args.url, args.format.upper())
    return True


if __name__ == '__main__':
    ok = main()
    print("✅ test-10 完成" if ok else "❌ test-10 失败") 