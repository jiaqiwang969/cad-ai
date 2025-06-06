#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""快速验证 OptimizedSpecificationsCrawler 的驱动启动与规格提取功能

用法示例：
  python scripts/test_driver_setup.py
  python scripts/test_driver_setup.py --url "<product_url>" --log DEBUG

脚本会：
1. 创建 OptimizedSpecificationsCrawler 实例；
2. 调用 extract_specifications 抓取单个产品的规格；
3. 打印抓取结果及前若干条规格详情。

若驱动无法正常启动，将在日志中看到 "创建 ChromeDriver 失败" 的明确报错。
"""

import argparse
import logging
import pprint
import sys
from pathlib import Path

# 确保项目根目录在 sys.path 中
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.crawler.specifications_optimized import OptimizedSpecificationsCrawler

DEFAULT_TEST_URL = (
    "https://www.traceparts.cn/en/product/"  # Timken 样例
    "the-timken-company-double-concentric-cartridge-block-qaamc10a050s?"
    "CatalogPath=TRACEPARTS%3ATP01002002006&Product=90-31032023-039175"
)


def main():
    parser = argparse.ArgumentParser(description="Test OptimizedSpecificationsCrawler driver setup")
    parser.add_argument("--url", type=str, default=DEFAULT_TEST_URL, help="Product URL to test")
    parser.add_argument("--log", type=str, default="INFO", help="Logging level (DEBUG, INFO, WARNING, ERROR)")
    args = parser.parse_args()

    # 设置日志
    logging.basicConfig(level=getattr(logging, args.log.upper(), logging.INFO),
                        format="%(asctime)s [%(levelname)s] %(message)s")

    crawler = OptimizedSpecificationsCrawler(log_level=getattr(logging, args.log.upper(), logging.INFO))

    print(f"\n🚀 Testing URL: {args.url}\n")
    result = crawler.extract_specifications(args.url)

    print("\n========== RESULT SUMMARY ==========")
    print(f"Success: {result.get('success')}")
    print(f"Specification count: {result.get('count')}")

    specs = result.get('specifications', [])
    if not specs:
        print("No specifications extracted.")
    else:
        print("\nFirst few specifications (truncated):")
        for i, spec in enumerate(specs[:10], 1):
            print(f"[{i}] {spec.get('reference', spec)}")  # 打印引用编号，如有维度重量也一起打印
            dims = spec.get('dimensions')
            weight = spec.get('weight')
            if dims:
                print(f"    dimensions: {dims}")
            if weight:
                print(f"    weight: {weight}")

    print("====================================\n")


if __name__ == "__main__":
    main() 