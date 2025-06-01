#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TraceParts 全链条抓取 (独立版)
================================
从根分类 → 叶节点 → 产品链接 → 规格，统一输出一个 JSON。
运行：
$ python traceparts_full_pipeline.py --workers 8
"""

import os, re, json, time, logging, argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse, parse_qs
import threading
from net_guard import register_fail, register_success

# -------- Selenium -------- #
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException, ElementClickInterceptedException, WebDriverException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    raise RuntimeError("需要 selenium，请先 pip install selenium")

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
LOG = logging.getLogger('pipeline')

RESULTS_DIR = Path('results')
PRODUCTS_DIR = RESULTS_DIR / 'products'
PRODUCTS_DIR.mkdir(parents=True, exist_ok=True)

ROOT_URL = "https://www.traceparts.cn/en/search/traceparts-classification?CatalogPath=TRACEPARTS%3ATRACEPARTS"

# 重试配置
MAX_RETRY_LEAF = 3      # 叶节点页面重试次数
MAX_RETRY_PRODUCT = 2   # 产品规格页重试次数

# ---------------- 工具函数 ---------------- #

def prepare_driver():
    opt = Options()
    opt.add_argument('--headless')
    opt.add_argument('--no-sandbox')
    opt.add_argument('--disable-dev-shm-usage')
    opt.add_argument('--disable-gpu')
    opt.add_argument('--window-size=1920,1080')
    opt.add_argument('--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    drv = webdriver.Chrome(options=opt)
    drv.set_page_load_timeout(90)  # 加长超时
    return drv

# --------- 分类树抓取 --------- #

def scroll_full(driver):
    last_h = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1.3)
        new_h = driver.execute_script("return document.body.scrollHeight")
        if new_h == last_h:
            break
        last_h = new_h

EXCLUDE_PATTERNS = ["sign-in","sign-up","login","register","javascript:","mailto:","#"]

def extract_classification_links() -> list:
    driver = prepare_driver()
    links = []
    try:
        LOG.info(f"🌐 打开分类根: {ROOT_URL}")
        driver.get(ROOT_URL)
        WebDriverWait(driver,30).until(EC.presence_of_element_located((By.TAG_NAME,'body')))
        scroll_full(driver)
        elements = driver.find_elements(By.CSS_SELECTOR,"a[href*='traceparts-classification-']")
        seen = set()
        for el in elements:
            href = el.get_attribute('href') or ''
            if not href or any(p in href.lower() for p in EXCLUDE_PATTERNS):
                continue
            if href in seen:
                continue
            seen.add(href)
            name = el.text.strip() or href.split('/')[-1]
            links.append({'name':name,'url':href})
        LOG.info(f"🔗 分类链接数: {len(links)}")
    finally:
        driver.quit()
    return links

def analyse_level(url:str)->int:
    if '%3ATRACEPARTS' in url:
        return 1
    if 'CatalogPath=TRACEPARTS%3A' in url:
        code = url.split('CatalogPath=TRACEPARTS%3A')[1].split('&')[0]
        if code.startswith('TP'):
            suffix = code[2:]
            if len(suffix)<=2:
                return 2
            return 2+len(suffix)//3
    # fallback
    return 2

def build_tree(records:list):
    # enrich level
    for r in records:
        r['level']=analyse_level(r['url'])
    records.sort(key=lambda x:(x['level'],x['name']))
    # root node
    root={'name':'TraceParts','level':1,'url':ROOT_URL,'code':'TRACE_ROOT','children':[]}
    code_map={'TRACE_ROOT':root}
    def code_of(url):
        if 'CatalogPath=TRACEPARTS%3A' in url:
            cp=url.split('CatalogPath=TRACEPARTS%3A')[1].split('&')[0]
            return cp
        return url.split('/')[-1][:30]
    leaves=[]
    for rec in records:
        rec['code']=code_of(rec['url'])
        node={'name':rec['name'],'url':rec['url'],'level':rec['level'],'code':rec['code'],'children':[]}
        code_map[node['code']]=node
        parent_code='TRACE_ROOT' if node['level']==2 else node['code'][:-3]
        parent=code_map.get(parent_code,root)
        parent.setdefault('children',[]).append(node)
    # mark leaves
    def mark(n):
        if n.get('children'):
            n['is_leaf']=False
            for c in n['children']:
                mark(c)
        else:
            n['is_leaf']=True
            leaves.append(n)
    mark(root)
    LOG.info(f"🌳 树构建完成，叶节点 {len(leaves)}")
    return root,leaves

# --------- 叶节点 -> 产品链接 --------- #

def load_all_results(driver):
    def click_show_more():
        try:
            btn=driver.find_element(By.XPATH,"//button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'show more')]")
            if btn.is_displayed() and btn.is_enabled():
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});",btn)
                btn.click();time.sleep(1.5);return True
        except NoSuchElementException:
            pass
        return False
    while True:
        scroll_full(driver)
        if not click_show_more():
            break

# -------- 带重试的叶节点抓取 -------- #

def _extract_products_once(leaf_url:str)->list:
    """单次尝试提取叶节点产品链接"""
    driver=prepare_driver();links=[];seen=set()
    try:
        driver.get(leaf_url)
        WebDriverWait(driver,60).until(EC.presence_of_element_located((By.TAG_NAME,'body')))
        load_all_results(driver)
        elements=driver.find_elements(By.CSS_SELECTOR,"a[href*='&Product=']")
        for el in elements:
            href=el.get_attribute('href') or ''
            if '&Product=' not in href or href in seen or '/product/' not in urlparse(href).path:
                continue
            seen.add(href);links.append(href)
        # 访问成功，记录 success（不论 links 是否为空，说明网络可用）
        register_success()
        return links
    except (TimeoutException, WebDriverException) as e:
        register_fail()
        raise
    except Exception:
        register_fail()
        raise
    finally:
        driver.quit()

def extract_products_for_leaf(leaf_url: str) -> list:
    """带重试包装，避免 renderer timeout"""
    for attempt in range(1, MAX_RETRY_LEAF + 1):
        try:
            res = _extract_products_once(leaf_url)
            return res
        except (TimeoutException, WebDriverException) as e:
            LOG.warning(f"⏳ 叶节点加载超时 ({attempt}/{MAX_RETRY_LEAF}) {leaf_url}: {e}")
            time.sleep(5)
        except Exception as e:
            LOG.warning(f"⚠️ 叶节点异常 ({attempt}/{MAX_RETRY_LEAF}) {leaf_url}: {e}")
            time.sleep(3)
    LOG.error(f"❌ 叶节点最终失败: {leaf_url}")
    return []

# --------- 产品 -> 规格 --------- #
# 复用之前的 is_valid_product_reference & helper

def is_valid_product_reference(text:str)->bool:
    if not text or len(text)<3:return False
    if any(k in text.lower() for k in ['aluminum','description','links','manufacturer','product page']):return False
    return bool(re.search(r'[A-Z].*\d',text)) and len(text)<=60

# -------- 带重试的规格抓取 -------- #

def _extract_specifications_once(product_url:str)->list:
    driver=prepare_driver()
    specs=[];seen=set()
    try:
        driver.get(product_url);WebDriverWait(driver,30).until(EC.presence_of_element_located((By.TAG_NAME,'body')));time.sleep(2)
        # 尝试选择 All
        try:
            btns=driver.find_elements(By.XPATH,"//*[text()='All' and (self::li or self::option or self::div or self::span)]")
            if btns:
                btns[0].click();time.sleep(2)
        except Exception:
            pass
        scroll_full(driver)
        rows=driver.find_elements(By.CSS_SELECTOR,'tr')
        for row in rows:
            cells=[c.text.strip() for c in row.find_elements(By.CSS_SELECTOR,'td,th')]
            for txt in cells[:5]:
                if is_valid_product_reference(txt) and txt not in seen:
                    specs.append({'reference':txt,'all_cells':cells});seen.add(txt)
                    break
        # 即使 specs 为空，也算成功访问
        register_success()
        return specs
    except (TimeoutException, WebDriverException) as e:
        register_fail()
        raise
    except Exception as e:
        register_fail()
        raise
    finally:
        driver.quit()

def safe_extract_specifications(product_url: str) -> dict:
    for attempt in range(1, MAX_RETRY_PRODUCT + 1):
        try:
            specs = _extract_specifications_once(product_url)
            return {"product_url": product_url, "specifications": specs}
        except (TimeoutException, WebDriverException) as e:
            LOG.warning(f"⏳ 规格页超时 ({attempt}/{MAX_RETRY_PRODUCT}) {product_url}: {e}")
            time.sleep(4)
        except Exception as e:
            LOG.warning(f"⚠️ 规格提取异常 ({attempt}/{MAX_RETRY_PRODUCT}) {product_url}: {e}")
            time.sleep(3)
    return {"product_url": product_url, "specifications": [], "error": "retry_failed"}

# --------------- 主流程 --------------- #

def main(workers:int):
    if not SELENIUM_AVAILABLE:
        LOG.error("缺少 selenium，无法运行");return
    LOG.info("🚀 开始全链条抓取…")
    # 1. 分类
    links=extract_classification_links()
    root,leaves=build_tree(links)

    # 2. 叶节点产品链接
    leaf_products={}
    with ThreadPoolExecutor(max_workers=workers) as exe:
        fut_map={exe.submit(extract_products_for_leaf,l['url']):l['code'] for l in leaves}
        for fut in as_completed(fut_map):
            code=fut_map[fut]
            try:
                leaf_products[code]=fut.result()
                LOG.info(f"📦 叶节点 {code} 产品数 {len(leaf_products[code])}")
            except Exception as e:
                LOG.error(f"叶节点 {code} 失败: {e}")
                leaf_products[code]=[]

    # 3. 产品规格
    final_leaves=[]
    with ThreadPoolExecutor(max_workers=workers) as exe:
        for leaf in leaves:
            code=leaf['code'];prods=leaf_products.get(code,[])
            leaf_info={'name':leaf['name'],'code':code,'url':leaf['url'],'products':[]}
            if prods:
                futs=[exe.submit(safe_extract_specifications, p) for p in prods]
                for fut in as_completed(futs):
                    try:
                        leaf_info['products'].append(fut.result())
                    except Exception as e:
                        register_fail()
                        leaf_info['products'].append({'product_url': 'unknown','specifications': [], 'error': str(e)})
            final_leaves.append(leaf_info)

    # 4. 输出
    RESULTS_DIR.mkdir(exist_ok=True)
    out=RESULTS_DIR / f"traceparts_full_data_{int(time.time())}.json"
    with open(out,'w',encoding='utf-8') as f:
        json.dump({'generated':time.strftime('%Y-%m-%dT%H:%M:%S'),'root':root,'leaves':final_leaves},f,ensure_ascii=False,indent=2)
    LOG.info(f"✅ 完成，文件: {out.resolve()}")

if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--workers',type=int,default=8)
    args=ap.parse_args()
    main(args.workers) 