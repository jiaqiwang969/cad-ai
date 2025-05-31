#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 12 —— 触发 CAD 下载验证码并保存图片

流程：
1. 载入 results/session_cookies.json，复用已登录会话；
2. 打开指定产品 URL（默认使用 Vuototecnica 示例）；
3. 点击首条规格的 CAD Download 按钮；
4. 等待验证码图片出现，保存为 results/captcha_samples/<timestamp>.png，同时打印图片路径。

注意：
• 若验证码以 <img src="data:image/png;base64,..."> 嵌入，则转 base64 解码保存。
• 如以普通 <img src="/captcha/xxx.png"> 则直接请求该地址或用 selenium .screenshot。
"""

import os
import re
import time
import json
import base64
import argparse
from pathlib import Path
from datetime import datetime

# Session helper
from utils.traceparts_session import build_driver, ensure_login

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

CAPTCHA_DIR = Path("results/captcha_samples")
CAPTCHA_DIR.mkdir(parents=True, exist_ok=True)

PRODUCT_URL = "https://www.traceparts.cn/en/product/vuototecnica-caps-with-orings?Product=70-01102019-118491&PartNumber=00%2015%20273"
COOKIE_FILE = Path("results/session_cookies.json")


def trigger_captcha(driver, url: str):
    driver.get(url)
    # 先尝试关闭 cookie 许可弹窗，避免遮挡
    accept_cookie_consent(driver)
    # 等首条 CAD 按钮出现并点击
    try:
        btn = find_and_click_cad_button(driver)
        if not btn:
            raise Exception("未定位到 CAD 下载按钮")
    except Exception as e:
        print("❌ 未找到 CAD 按钮", e)
        # 调试：保存页面截图方便分析
        debug_path = CAPTCHA_DIR / "debug_no_cad.png"
        driver.save_screenshot(str(debug_path))
        print("📸 已保存调试截图 =>", debug_path)
        return None
    # 验证码弹窗：等待 img 出现
    try:
        img = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, "img[src*='captcha' i]")))
        src = img.get_attribute("src")
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = CAPTCHA_DIR / f"captcha_{ts}.png"
        if src.startswith("data:image"):
            # base64 格式
            header, b64data = src.split(",", 1)
            with open(out_path, "wb") as f:
                f.write(base64.b64decode(b64data))
        else:
            # 普通 URL，直接截图该元素
            img.screenshot(str(out_path))
        print("✅ 验证码已保存 =>", out_path)
        return out_path
    except Exception as e:
        print("❌ 未捕获到验证码", e)
        # 保存失败页面 HTML
        html_path = CAPTCHA_DIR / "debug_no_captcha.html"
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print("📝 已保存页面源码以供分析 =>", html_path)
        return None


# --------------------------------------------
# 工具函数
# --------------------------------------------

def accept_cookie_consent(driver):
    """尝试关闭常见的 cookie 许可横幅，以免遮挡按钮"""
    possible_selectors = [
        "button#onetrust-accept-btn-handler",            # OneTrust 默认 id
        "button[aria-label*='Accept'][id*='cookie']",    # aria-label 带 Accept cookie
        "button[title*='Accept'][title*='cookie']",
        "button[class*='accept'][class*='cookie']",
        "button[data-qa='accept-cookies']",
    ]
    for sel in possible_selectors:
        try:
            btns = driver.find_elements(By.CSS_SELECTOR, sel)
            if btns:
                for b in btns:
                    if b.is_displayed() and b.is_enabled():
                        b.click()
                        time.sleep(1)
                        return True
        except Exception:
            continue
    return False


def find_and_click_cad_button(driver):
    """搜索并点击触发 CAD 下载的按钮，返回按钮元素或 None"""
    selectors = [
        "button[title*='CAD Download' i]",   # title 属性
        "a[title*='CAD Download' i]",
        "button[aria-label*='CAD Download' i]",
        "a[aria-label*='CAD Download' i]",
        "button[data-original-title*='CAD Download' i]",
        "a[data-original-title*='CAD Download' i]",
        "button[class*='btn-download' i]",
        "a[class*='btn-download' i]",
        "button[id*='cad' i]",
        "a[id*='cad' i]",
    ]
    for sel in selectors:
        try:
            elem = WebDriverWait(driver, 8).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, sel))
            )
            if elem:
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", elem)
                time.sleep(0.5)
                elem.click()
                return elem
        except Exception:
            continue
    # 备用：根据可见文本含 CAD 查找按钮/链接
    try:
        elems = driver.find_elements(By.XPATH, "//*[contains(translate(text(),'CAD','cad'),'cad')]//ancestor::a[1] | //*[contains(translate(text(),'CAD','cad'),'cad')]//ancestor::button[1]")
        for e in elems:
            if e.is_displayed() and e.is_enabled():
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", e)
                time.sleep(0.5)
                e.click()
                return e
    except Exception:
        pass
    return None


# --------------------------------------------
# 主逻辑封装
# --------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=PRODUCT_URL, help="产品 URL")
    args = parser.parse_args()

    driver = build_driver(headless=True)
    # 自动登录或加载 cookie
    if not ensure_login(driver, email=os.getenv("TRACEPARTS_EMAIL"), password=os.getenv("TRACEPARTS_PASSWORD"), cookies_path=COOKIE_FILE):
        print("❌ 无法登录 TraceParts，请检查账号/密码或 Cookie 文件")
        driver.quit()
        exit(1)
    trigger_captcha(driver, args.url)
    driver.quit() 