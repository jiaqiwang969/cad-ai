#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TraceParts 全流程一键抓取脚本
========================================================
本脚本集成之前的所有步骤：
1. test/06-test_classification_tree_recursive.py  —— 抓取完整分类扁平树
2. test/07-test_classification_tree_nested.py    —— 生成嵌套树并输出叶节点列表
3. test/09-test_batch_leaf_product_links.py      —— 批量抓取每个叶节点的产品详情页链接
4. test/09-1-test_product_specifications_extractor.py —— 提取单个产品的所有规格

最终生成一个 JSON：results/traceparts_full_data_<timestamp>.json
结构示例：
{
  "generated": "2025-06-01T12:00:00",
  "root": {              # 嵌套分类树（含 children / is_leaf）
     ...
  },
  "leaves": [
     {
       "name": "Bearings",
       "code": "TP01002002006",
       "url": "...",
       "products": [
           {
              "product_url": "...&Product=90-31032023-039178",
              "product_id": "90-31032023-039178",
              "specifications": [
                  {"reference": "TXCE-H1-6-1515-L100", ...},
                  ...
              ]
           },
           ...
       ]
     },
     ...
  ]
}

运行：
$ python pipeline_traceparts_allinone.py --workers 12
"""

import os
import json
import time
import logging
import argparse
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlparse, parse_qs

# -------- 配置日志 -------- #
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
LOG = logging.getLogger("allinone")

# 目录常量
RESULTS_DIR = Path("results")
PRODUCTS_DIR = RESULTS_DIR / "products"
PRODUCTS_DIR.mkdir(parents=True, exist_ok=True)

# -------- 依赖脚本路径 -------- #
TEST06 = Path("test/06-test_classification_tree_recursive.py")
TEST07 = Path("test/07-test_classification_tree_nested.py")
TEST09 = Path("test/09-test_batch_leaf_product_links.py")
TEST09_1 = Path("test/09-1-test_product_specifications_extractor.py")

# -------- 辅助函数 -------- #

def run_subprocess(cmd: str):
    """运行子进程并实时输出"""
    LOG.info(f"⚙️ 运行命令: {cmd}")
    proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for line in proc.stdout:
        print(line.rstrip())
    proc.wait()
    if proc.returncode != 0:
        raise RuntimeError(f"命令失败: {cmd}")

# -------- 步骤 1 & 2: 分类树 & 叶节点 -------- #

def ensure_classification_tree():
    """确保已生成嵌套树和叶节点文件"""
    leaves_file = RESULTS_DIR / "traceparts_tree_leaves.jsonl"
    if leaves_file.exists():
        LOG.info("✅ 已存在叶节点文件，跳过树抓取")
        return leaves_file

    # 运行 test-06
    run_subprocess(f"python {TEST06}")
    # 运行 test-07
    run_subprocess(f"python {TEST07}")

    if not leaves_file.exists():
        raise FileNotFoundError("叶节点文件生成失败！")
    return leaves_file

# -------- 步骤 3: 叶节点 -> 产品链接 -------- #

def ensure_product_links(leaves_file: Path, workers: int):
    """批量抓取所有叶节点的产品链接"""
    run_subprocess(f"python {TEST09} --leaves {leaves_file} --workers {workers}")

# -------- 步骤 4: 产品 -> 规格 -------- #
# 复用 test-09-1 中的函数
import importlib.util
spec = importlib.util.spec_from_file_location("tp_spec", TEST09_1)
TP_SPEC = importlib.util.module_from_spec(spec)
spec.loader.exec_module(TP_SPEC)  # type: ignore


def extract_specs_for_product(product_url: str) -> dict:
    """使用已有函数提取产品规格，返回 dict {product_url, product_id, specifications}"""
    try:
        base_info = TP_SPEC.extract_base_product_info(product_url)
        driver = TP_SPEC.prepare_driver()
        try:
            driver.get(product_url)
            time.sleep(2)
            specs = TP_SPEC.extract_all_product_specifications(driver)
            if not specs:
                LOG.warning(f"⚠️ 规格为空: {product_url}")
            return {
                "product_url": product_url,
                "product_id": base_info.get("product_id", "UNKNOWN") if base_info else "UNKNOWN",
                "specifications": specs
            }
        finally:
            driver.quit()
    except Exception as e:
        LOG.error(f"❌ 提取规格失败: {e}")
        return {
            "product_url": product_url,
            "error": str(e),
            "specifications": []
        }

# -------- 主流程 -------- #

def main(workers: int = 8):
    LOG.info("🚀 TraceParts 全流程抓取开始")
    leaves_file = ensure_classification_tree()

    # 读取叶节点列表
    leaves = []
    with open(leaves_file, 'r', encoding='utf-8') as f:
        for line in f:
            leaves.append(json.loads(line))
    LOG.info(f"📄 叶节点数量: {len(leaves)}")

    # 抓取产品列表
    ensure_product_links(leaves_file, workers)

    # 聚合产品列表数据
    leaf_code_to_links = {}
    for file in PRODUCTS_DIR.glob("product_links_*.json"):
        try:
            data = json.loads(file.read_text())
            leaf_code_to_links[data.get('tp_code')] = data.get('links', [])
        except Exception:
            continue

    # 并发提取产品规格
    final_leaves = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_leaf = {}
        for leaf in leaves:
            code = leaf.get('code')
            prod_links = leaf_code_to_links.get(code, [])
            leaf_info = {
                "name": leaf.get('name'),
                "code": code,
                "url": leaf.get('url'),
                "products": []
            }
            if not prod_links:
                final_leaves.append(leaf_info)
                continue
            # 针对当前 leaf 中的所有 product 链接提交任务
            futures = [executor.submit(extract_specs_for_product, url) for url in prod_links]
            for fut in as_completed(futures):
                leaf_info['products'].append(fut.result())
            final_leaves.append(leaf_info)

    # 读取嵌套树根
    nested_file = RESULTS_DIR / "traceparts_tree_nested.json"
    with open(nested_file, 'r', encoding='utf-8') as f:
        nested_data = json.load(f)
    root = nested_data.get('root')

    # 输出最终 JSON
    timestamp = int(time.time())
    out_file = RESULTS_DIR / f"traceparts_full_data_{timestamp}.json"
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump({
            "generated": time.strftime('%Y-%m-%dT%H:%M:%S'),
            "root": root,
            "leaves": final_leaves
        }, f, ensure_ascii=False, indent=2)

    LOG.info(f"✅ 全部完成，输出文件: {out_file.resolve()}")
    print("✅ pipeline_allinone 成功")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="TraceParts 全流程抓取")
    parser.add_argument('--workers', type=int, default=8, help='并发线程数 (默认 8)')
    args = parser.parse_args()
    main(workers=args.workers) 