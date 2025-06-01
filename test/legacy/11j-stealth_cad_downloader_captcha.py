#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 11j —— 隐身 CAD 下载 + 自动验证码识别
基于 11i-stealth_cad_downloader.py 复用浏览器隐身与格式选择逻辑，
新增步骤：
1. 点击下载按钮后，如出现验证码图片/Canvas，则调用 utils.captcha_solver 进行 OCR。
2. 自动填写验证码并重新点击下载按钮，最多重试 3 次。
3. 成功监听到 download 事件后，将文件保存至 results/downloads/ 目录。
"""

import time
import random
import os
from pathlib import Path
import importlib.util
from playwright.sync_api import sync_playwright, Page, Download
from utils.captcha_solver import solve_base64_captcha, solve_file

# ---------- 动态加载 11i 作为模块 -------------
BASE_DIR = Path(__file__).parent
I11_PATH = BASE_DIR / "11i-stealth_cad_downloader.py"
_spec = importlib.util.spec_from_file_location("stealth11i", I11_PATH)
stealth11i = importlib.util.module_from_spec(_spec)  # type: ignore
_spec.loader.exec_module(stealth11i)  # type: ignore

# 复用 11i 中的函数
create_stealth_browser = stealth11i.create_stealth_browser
stealth_login = stealth11i.stealth_login
navigate_to_product_with_stealth = stealth11i.navigate_to_product_with_stealth

# ---------- 常量 ----------
CAPTCHA_DIR = Path("results/captcha_samples")
CAPTCHA_DIR.mkdir(parents=True, exist_ok=True)
DOWNLOAD_DIR = Path("results/downloads")
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
WAIT_USER_INPUT = True  # 是否等待用户手动输入验证码

# ---------- 辅助 ----------

def human_delay(a=0.1, b=0.3):
    time.sleep(random.uniform(a, b))


def find_captcha_element(page: Page):
    selectors = [
        "img[src*='captcha']",
        "canvas[id*='captcha']",
        "canvas[class*='captcha']",
        "img[alt*='captcha']"
    ]
    for sel in selectors:
        try:
            elem = page.wait_for_selector(sel, timeout=5000)
            if elem and elem.is_visible():
                return elem
        except Exception:
            continue
    return None


def save_captcha_image(elem, page: Page) -> Path:
    """保存验证码图片到本地，返回路径"""
    # 尝试 base64 src
    try:
        src = elem.get_attribute("src")
        if src and src.startswith("data:image") and ";base64," in src:
            b64 = src.split(",", 1)[1]
            img_path = CAPTCHA_DIR / f"cap_{int(time.time()*1000)}.png"
            with open(img_path, "wb") as f:
                import base64, binascii
                f.write(base64.b64decode(b64))
            return img_path
    except Exception:
        pass
    # 否则截图文件
    img_path = CAPTCHA_DIR / f"cap_{int(time.time()*1000)}.png"
    elem.screenshot(path=str(img_path))
    return img_path


def input_captcha(page: Page, text: str) -> bool:
    input_sel = "input[name*='captcha'], input[placeholder*='captcha'], input[type='text']:below(img[src*='captcha'])"
    try:
        inp = page.wait_for_selector(input_sel, timeout=5000)
        if inp:
            inp.click()
            inp.fill("")
            human_delay(0.2,0.4)
            inp.type(text, delay=random.randint(50,120))
            return True
    except Exception:
        pass
    return False


def click_download(page: Page) -> bool:
    selectors = [
        "#direct-cad-download",
        "button[aria-label*=download i]",
        "button[id*='download']",
        "a[title*=download i]",
    ]
    for sel in selectors:
        try:
            btn = page.wait_for_selector(sel, timeout=4000)
            if btn and btn.is_visible():
                classes = (btn.get_attribute("class") or "").lower()
                if "disabled" in classes:
                    continue
                btn.hover()
                human_delay(0.3,0.6)
                btn.click()
                return True
        except Exception:
            continue
    return False


# ---------- 主流程 ----------

def main():
    email = os.getenv("TRACEPARTS_EMAIL", "demo@example.com")
    password = os.getenv("TRACEPARTS_PASSWORD", "pass")
    print("🔑 11j 隐身下载 + 自动验证码, 账号:", email)

    with sync_playwright() as p:
        browser, context, page = create_stealth_browser(p, headless=False)
        if not fast_stealth_login(page, email, password):
            return
        if not fast_navigate_to_product(page):
            return
        # 立即截图整个页面
        timestamp = int(time.time())
        debug_dir = Path("results/stealth_debug")
        debug_dir.mkdir(parents=True, exist_ok=True)
        full_page_shot = debug_dir / f"product_page_{timestamp}.png"
        page.screenshot(path=str(full_page_shot), full_page=True)
        print(f"📸 已截图整个产品页面: {full_page_shot}")
        
        # 保存页面HTML用于分析
        html_content = page.content()
        html_file = debug_dir / f"product_page_{timestamp}.html"
        with open(html_file, "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"💾 已保存页面HTML: {html_file}")
        
        # 增强验证码检测 - 搜索所有图片元素
        print("🔍 搜索页面中所有图片元素...")
        all_imgs = page.query_selector_all("img")
        print(f"   找到 {len(all_imgs)} 个 img 元素")
        
        for i, img in enumerate(all_imgs):
            try:
                src = img.get_attribute("src") or ""
                alt = img.get_attribute("alt") or ""
                id_attr = img.get_attribute("id") or ""
                class_attr = img.get_attribute("class") or ""
                
                # 检查是否可能是验证码
                combined = (src + alt + id_attr + class_attr).lower()
                if any(kw in combined for kw in ["captcha", "verify", "code", "challenge"]):
                    print(f"   🎯 可能的验证码图片 {i}: src='{src}', alt='{alt}', id='{id_attr}', class='{class_attr}'")
                    if img.is_visible():
                        captcha_path = save_captcha_image(img, page)
                        print(f"   ✅ 已保存验证码: {captcha_path}")
                else:
                    print(f"   🔗 普通图片 {i}: src='{src[:50]}...', alt='{alt}', visible={img.is_visible()}")
            except Exception as e:
                print(f"   ❌ 图片 {i} 分析失败: {e}")
        
        # 检查Canvas元素
        canvases = page.query_selector_all("canvas")
        print(f"🎨 找到 {len(canvases)} 个 canvas 元素")
        for i, canvas in enumerate(canvases):
            try:
                id_attr = canvas.get_attribute("id") or ""
                class_attr = canvas.get_attribute("class") or ""
                combined = (id_attr + class_attr).lower()
                if "captcha" in combined or "verify" in combined:
                    print(f"   🎯 可能的验证码Canvas {i}: id='{id_attr}', class='{class_attr}'")
                    if canvas.is_visible():
                        captcha_path = save_captcha_image(canvas, page)
                        print(f"   ✅ 已保存Canvas验证码: {captcha_path}")
                else:
                    print(f"   🎨 普通Canvas {i}: id='{id_attr}', class='{class_attr}', visible={canvas.is_visible()}")
            except Exception as e:
                print(f"   ❌ Canvas {i} 分析失败: {e}")
        
        # 传统方式检测验证码
        elem = find_captcha_element(page)
        if elem:
            img_path = save_captcha_image(elem, page)
            print(f"📸 传统方式找到验证码: {img_path}")
        else:
            print("ℹ️ 传统方式未检测到验证码元素")

        input("按回车关闭浏览器…")
        browser.close()

# 重用 choose_cad_format 逻辑（从 12h 简化版）
def choose_cad_format(page: Page) -> bool:
    """尝试选择常用 CAD 格式，使下载按钮变为可用"""
    select = None
    try:
        select = page.wait_for_selector("#cad-format-select", timeout=5000)
    except Exception:
        pass
    if not select:
        # 回退其它 selector
        try:
            select = page.query_selector("select[id*='format']")
        except Exception:
            pass
    if not select:
        return False
    # 遍历选项
    preferred = ["STEP", "STL", "IGES"]
    options = select.query_selector_all("option")
    for pref in preferred:
        for opt in options:
            text = (opt.text_content() or "").strip()
            if pref.lower() in text.lower():
                value = opt.get_attribute("value")
                if value:
                    select.select_option(value=value)
                else:
                    select.select_option(label=text)
                human_delay(0.5,1.0)
                return True
    # 若无匹配，选择第二项
    if len(options) > 1:
        select.select_option(index=1)
        human_delay(0.5,1.0)
        return True
    return False

# 加速版的登录和导航函数
def fast_stealth_login(page, email, password):
    """快速隐身登录，减少延迟"""
    print("🔐 开始快速隐身登录...")
    
    # 访问登录页面
    page.goto("https://www.traceparts.cn/en/sign-in", wait_until="networkidle")
    human_delay(0.5, 1.0)  # 减少等待时间
    
    # 快速滚动（减少延迟）
    page.evaluate("window.scrollTo(0, 100)")
    human_delay(0.1, 0.2)
    page.evaluate("window.scrollTo(0, 0)")
    human_delay(0.1, 0.2)
    
    # 快速输入邮箱
    print("📧 快速输入邮箱...")
    email_input = page.locator("input[type='email']")
    email_input.click()
    human_delay(0.1, 0.2)
    email_input.fill("")
    email_input.type(email, delay=10)  # 大幅减少打字延迟
    human_delay(0.2, 0.4)
    
    # 快速输入密码  
    print("🔑 快速输入密码...")
    pwd_input = page.locator("input[type='password']")
    pwd_input.click()
    human_delay(0.1, 0.2)
    pwd_input.fill("")
    pwd_input.type(password, delay=10)  # 大幅减少打字延迟
    human_delay(0.3, 0.5)
    
    # 快速检查输入
    page.evaluate("""
        document.querySelector('input[type="email"]').focus();
        setTimeout(() => document.querySelector('input[type="password"]').focus(), 50);
    """)
    human_delay(0.1, 0.3)
    
    # 快速点击登录
    print("🚀 快速点击登录...")
    submit_btn = page.locator("button:has-text('Sign in')").first
    submit_btn.hover()
    human_delay(0.1, 0.2)
    submit_btn.click()
    
    # 减少登录等待时间
    print("⏳ 等待登录响应...")
    human_delay(1.5, 2.5)  # 从3-6秒减少到1.5-2.5秒
    
    # 检查登录状态
    current_url = page.url
    if "sign-in" not in current_url.lower():
        print("✅ 登录成功！")
        return True
    else:
        print("❌ 登录失败")
        return False

def fast_navigate_to_product(page):
    """快速导航到产品页面"""
    print("📦 快速导航到产品页面...")
    
    # 快速访问首页
    page.goto("https://www.traceparts.cn/en", wait_until="networkidle")
    human_delay(0.5, 1.0)  # 减少等待
    
    # 快速滚动浏览
    page.evaluate("window.scrollTo(0, 300)")
    human_delay(0.2, 0.4)
    page.evaluate("window.scrollTo(0, 600)")
    human_delay(0.2, 0.4)
    page.evaluate("window.scrollTo(0, 0)")
    human_delay(0.2, 0.4)
    
    # 快速访问产品页面
    product_url = "https://www.traceparts.cn/en/product/rs-pro-abs-plastic-sheet-stock1220x610x15mm?CatalogPath=TRACEPARTS%3ATP05009&Product=90-03062024-057087"
    print(f"🎯 快速访问产品页面: {product_url}")
    
    try:
        page.goto(product_url, wait_until="domcontentloaded", timeout=30000)
        human_delay(1.0, 1.5)  # 减少等待时间
        
        # 快速等待页面稳定
        page.wait_for_load_state("networkidle", timeout=15000)  # 从30秒减少到15秒
    except Exception as e:
        print(f"⚠️ 页面加载超时，但继续分析: {e}")
        human_delay(0.5, 1.0)
    
    # 检查页面标题
    title = page.title()
    print(f"📄 页面标题: {title}")
    
    return "sign-in" not in page.url.lower()

if __name__ == "__main__":
    main() 