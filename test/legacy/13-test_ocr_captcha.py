#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 13 —— 本地 OCR 识别验证码

用法：
$ python test/13-test_ocr_captcha.py <png_path>
若不提供，则自动读取 results/captcha_samples 目录下最新一张。
"""

import sys
import glob
from pathlib import Path

from utils.captcha_solver import solve_file

CAPTCHA_DIR = Path("results/captcha_samples")

def latest_png() -> Path:
    files = sorted(CAPTCHA_DIR.glob("*.png"), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None


def main():
    if len(sys.argv) > 1:
        img_path = Path(sys.argv[1])
    else:
        img_path = latest_png()
        if not img_path:
            print("❌ 未找到验证码样本，请先运行 test-12")
            return
    text = solve_file(str(img_path))
    print(f"图片: {img_path}\n识别结果 => '{text}'")

if __name__ == "__main__":
    main() 