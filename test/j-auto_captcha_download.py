#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 J —— 使用改进算法自动选择格式、填写验证码并点击下载按钮
运行: make test-j
"""
import os, sys, time
from pathlib import Path
from playwright.sync_api import sync_playwright
import importlib.util

# 导入工具
sys.path.append(str(Path(__file__).parent.parent))
from utils.captcha_solver import CaptchaSolver

CAP_DIR = Path("results/captcha_samples")
CAP_DIR.mkdir(parents=True, exist_ok=True)

PRODUCT_URL = os.getenv("TRACEPARTS_PRODUCT_URL", "https://www.traceparts.cn/en/product/rs-pro-abs-plastic-sheet-stock1220x610x15mm?CatalogPath=TRACEPARTS%3ATP05009&Product=90-03062024-057087")
preferred_formats = ["STEP AP214", "STEP AP203", "STL", "IGES", "SOLIDWORKS", "Parasolid"]

# --------- 动态加载 stealth11j 模块 ---------
BASE_DIR = Path(__file__).parent
MOD11 = importlib.util.spec_from_file_location(
    "stealth11j", BASE_DIR / "11j-stealth_cad_downloader_captcha.py")
stealth11j = importlib.util.module_from_spec(MOD11)  # type: ignore
MOD11.loader.exec_module(stealth11j)  # type: ignore

# 登录账号
EMAIL = os.getenv("TRACEPARTS_EMAIL", "demo@example.com")
PASSWORD = os.getenv("TRACEPARTS_PASSWORD", "pass")

def select_format(page):
    for sel in ['select', 'button:has-text("Please select")']:
        el = page.query_selector(sel)
        if el:
            if el.evaluate("el => el.tagName").lower()=="select":
                options = el.query_selector_all('option')
                for fmt in preferred_formats:
                    for idx,opt in enumerate(options):
                        if fmt.lower() in (opt.text_content() or "").lower():
                            el.select_option(index=idx)
                            print("选择格式:",fmt)
                            return
            else:
                el.click()
                page.wait_for_timeout(500)
                for fmt in preferred_formats:
                    opt=page.query_selector(f'li:has-text("{fmt}")')
                    if opt:
                        opt.click();print("选择格式:",fmt);return

def main():
    with sync_playwright() as p:
        # 创建隐身浏览器并登录
        browser, ctx, page = stealth11j.create_stealth_browser(p, headless=False)
        if not stealth11j.fast_stealth_login(page, EMAIL, PASSWORD):
            print("❌ 登录失败，退出测试")
            return
        page.goto(PRODUCT_URL)
        page.wait_for_load_state('networkidle',timeout=60000)
        select_format(page)
        
        # 使用TrOCR多模型进行验证码识别
        print("🤖 初始化TrOCR验证码识别器...")
        solver = CaptchaSolver(
            debug=True, 
            ocr_method="auto",  # 自动选择：优先TrOCR，失败则回退pytesseract
            trocr_model="microsoft-large"  # 使用大型模型获得更好的识别效果
        )
        
        res = solver.solve_from_playwright_page(page, return_bbox=True)
        text = res['text']
        bbox = res['icon_bbox']
        
        if text:
            print(f'✅ 验证码识别成功: {text}')
            # 找输入框
            input_box = None
            for sel in ['input[placeholder*="captcha" i]','input[name*="captcha" i]','input[id*="captcha" i]','input[type="text"]']:
                for el in page.query_selector_all(sel):
                    if el.is_visible() and not (el.input_value() or "").strip():
                        input_box = el
                        break
                if input_box:
                    break
            
            if not input_box and bbox:
                print("📍 未找到输入框，尝试点击验证码区域并输入")
                page.mouse.click(bbox['x']-20, bbox['y']+bbox['height']/2)
                page.keyboard.type(text)
            elif input_box:
                print("📝 找到验证码输入框，填入识别结果")
                input_box.fill('')
                input_box.type(text)
        else:
            print("❌ 验证码识别失败")
            
        # 点击下载
        print("🔽 尝试点击下载按钮...")
        for sel in ['a[href*="download"]','button:has-text("Download")']:
            btn = page.query_selector(sel)
            if btn:
                print(f"✅ 找到下载按钮: {sel}")
                btn.click()
                break
        else:
            print("❌ 未找到下载按钮")
            
        time.sleep(5)
        browser.close()

if __name__=='__main__':
    main() 