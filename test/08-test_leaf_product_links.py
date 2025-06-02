#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 08  —— 针对 TraceParts 某个最末层（leaf）分类页面，收集该分类下所有产品详情页链接。

示例入口（leaf）URL：
https://www.traceparts.cn/en/search/traceparts-classification-mechanical-components-bearings-bearing-blocks-cartridge-blocks?CatalogPath=TRACEPARTS%3ATP01002002006

目标：获取所有形如
https://www.traceparts.cn/en/product/...?...&Product=90-31032023-039178
的链接，并保存到 results/product_links_<TP code>.json

使用方法：
$ python test/08-test_leaf_product_links.py <leaf_url>
若不提供参数，则脚本默认使用上面示例。
"""

import os
import re
import sys
import json
import time
import logging
from urllib.parse import urlparse, parse_qs

# Selenium
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException, ElementClickInterceptedException, StaleElementReferenceException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
LOG = logging.getLogger("test-08")

def prepare_driver() -> "webdriver.Chrome":
    """配置一个无头 Chrome 驱动"""
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


PRODUCT_LINK_PATTERN = re.compile(r"[?&]Product=([0-9\-]+)")


def scroll_full(driver: "webdriver.Chrome"):
    """持续滚动到页面底部，以触发惰性加载"""
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1.2)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            # 再次等待一下，确认没有新增内容
            time.sleep(0.8)
            new_height_final = driver.execute_script("return document.body.scrollHeight")
            if new_height_final == last_height:
                break
            else:
                last_height = new_height_final
        else:
            last_height = new_height


def extract_products_on_page(driver: "webdriver.Chrome", seen: set) -> list:
    """提取当前页面所有含 &Product= 的 a 标签链接，去重"""
    elements = driver.find_elements(By.CSS_SELECTOR, "a[href*='&Product=']")
    links = []
    for el in elements:
        href = el.get_attribute('href') or ""
        if not href or href in seen:
            continue
        if '&Product=' not in href:
            continue
        parsed = urlparse(href)
        if '/product/' not in parsed.path:
            continue  # 过滤广告或其他链接
        seen.add(href)
        links.append(href)
    return links


def append_page_size(url: str, size: int = 500) -> str:
    """若 URL 中未包含 PageSize 参数，则补充一个较大的值，减少分页次数。"""
    if 'PageSize=' in url:
        return url
    if '?' in url:
        return f"{url}&PageSize={size}"
    else:
        return f"{url}?PageSize={size}"


def click_show_more_if_any(driver: "webdriver.Chrome") -> bool:
    """若页面存在 'Show more results' 按钮，则点击并返回 True；否则 False。"""
    try:
        # TraceParts 使用 button 及 span 文本
        btn = driver.find_element(By.XPATH, "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'show more')]" )
        if btn and btn.is_displayed() and btn.is_enabled():
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
            btn.click()
            time.sleep(2)
            return True
    except NoSuchElementException:
        pass
    except (ElementClickInterceptedException, StaleElementReferenceException):
        time.sleep(1)
    return False


def load_all_results(driver: "webdriver.Chrome"):
    """持续滚动并点击 'Show more results'，直到全部产品都加载完。"""
    while True:
        scroll_full(driver)
        if not click_show_more_if_any(driver):
            # 没有更多按钮，退出
            break


def collect_all_product_links(driver: "webdriver.Chrome", leaf_url: str) -> list:
    LOG.info(f"🌐 打开叶节点页面: {leaf_url}")
    driver.get(leaf_url)
    try:
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
        )
    except TimeoutException:
        LOG.error("页面加载超时！")
        return []

    # 先加载全部结果
    load_all_results(driver)

    # 再一次性提取链接
    links = extract_products_on_page(driver, set())
    LOG.info(f"🔗 共提取产品链接 {len(links)} 条")
    return links


def tp_code_from_url(url: str) -> str:
    """从 leaf URL 提取 TP 编码，例 TP01002002006"""
    qs_part = urlparse(url).query
    params = parse_qs(qs_part)
    cp = params.get('CatalogPath', [''])[0]
    if cp.startswith('TRACEPARTS:'):
        cp = cp.split(':',1)[1]
    return cp


def main():
    if not SELENIUM_AVAILABLE:
        LOG.error("Selenium 未安装，无法运行 test-08！")
        return False

    # 读取命令行参数
    leaf_url = sys.argv[1] if len(sys.argv) > 1 else "https://www.traceparts.cn/en/search/traceparts-classification-mechanical-components-bearings-bearing-blocks-flanged-block-bearings-flanged-block-bearings-ball-bearings?CatalogPath=TRACEPARTS%3ATP01002002002001"

    tp_code = tp_code_from_url(leaf_url) or "UNKNOWN"

    driver = prepare_driver()
    try:
        all_links = collect_all_product_links(driver, leaf_url)
        if not all_links:
            LOG.warning("未抓取到任何产品链接！")
        # 输出到文件
        os.makedirs("results", exist_ok=True)
        out_file = f"results/product_links_{tp_code}.json"
        with open(out_file, 'w', encoding='utf-8') as f:
            json.dump({"leaf_url": leaf_url, "tp_code": tp_code, "total": len(all_links), "links": all_links}, f, ensure_ascii=False, indent=2)
        LOG.info(f"✅ 共抓取 {len(all_links)} 条产品链接，已保存到 {out_file}")
        return True
    finally:
        driver.quit()


if __name__ == "__main__":
    ok = main()
    print("✅ test-08 成功" if ok else "❌ test-08 失败") 