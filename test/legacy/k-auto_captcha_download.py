#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 K —— 使用 GPT-4o 自动选择格式、填写验证码并点击下载按钮
运行: make test-k
"""
import os, sys, time
from pathlib import Path
from playwright.sync_api import sync_playwright
import importlib.util

# 导入工具
sys.path.append(str(Path(__file__).parent.parent))
from utils.captcha_solver import CaptchaSolver

CAP_DIR = Path("results/captcha_samples") # 实际截图由 solver 的 debug 控制
CAP_DIR.mkdir(parents=True, exist_ok=True)

PRODUCT_URL = os.getenv("TRACEPARTS_PRODUCT_URL", "https://www.traceparts.cn/en/product/rs-pro-abs-plastic-sheet-stock1220x610x15mm?CatalogPath=TRACEPARTS%3ATP05009&Product=90-03062024-057087")
preferred_formats = ["STEP AP214", "STEP AP203", "STL", "IGES", "SOLIDWORKS", "Parasolid"]

# --------- 动态加载 stealth11j 模块 ---------
BASE_DIR = Path(__file__).parent
# Correcting the path to 11j-stealth_cad_downloader_captcha.py assuming it's in the same 'test' directory
# If it's in the root, it would be BASE_DIR.parent / "11j-stealth_cad_downloader_captcha.py"
# Assuming it's structured like 11j-stealth_cad_downloader_captcha.py is a sibling or in a known path
# For now, let's assume it's in the same directory as j-auto_captcha_download.py and thus k-auto_captcha_download.py
# This path might need adjustment based on your actual structure for 11j-stealth_cad_downloader_captcha.py
path_to_11j = BASE_DIR / "11j-stealth_cad_downloader_captcha.py"
if not path_to_11j.exists():
    # Try parent directory if not found, common for utility scripts
    path_to_11j = BASE_DIR.parent / "11j-stealth_cad_downloader_captcha.py"
    if not path_to_11j.exists():
        # Fallback or error if still not found
        print(f"❌ Critical: 11j-stealth_cad_downloader_captcha.py not found at expected locations.")
        print(f"Attempted: {BASE_DIR / '11j-stealth_cad_downloader_captcha.py'} and {path_to_11j}")
        sys.exit(1)

MOD11 = importlib.util.spec_from_file_location(
    "stealth11j", path_to_11j)
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
        browser, ctx, page = stealth11j.create_stealth_browser(p, headless=False) # Keep headless=False for debugging

        # ---- 下载文件保存设置 ----
        DOWNLOAD_DIR = Path("results/downloads")
        DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

        def _on_download(download):
            try:
                suggested = download.suggested_filename
                dest_path = DOWNLOAD_DIR / suggested
                download.save_as(str(dest_path))
                print(f"💾 下载完成，已保存到: {dest_path.resolve()}")
            except Exception as e_dl:
                print(f"❌ 保存下载文件失败: {e_dl}")

        ctx.on("download", _on_download)

        if not stealth11j.fast_stealth_login(page, EMAIL, PASSWORD):
            print("❌ 登录失败，退出测试")
            browser.close()
            return
        
        page.goto(PRODUCT_URL)
        try:
            page.wait_for_load_state('networkidle',timeout=60000)
        except Exception as e:
            print(f"⚠️ 页面加载可能超时或未完全空闲: {e}")
            page.screenshot(path=str(CAP_DIR / f"page_load_issue_{int(time.time())}.png"))

        # Frame listing moved to after solver initialization

        select_format(page)
        page.wait_for_timeout(1000) # Wait a bit after format selection
        
        print("🤖 初始化GPT-4o验证码识别器...")
        solver = CaptchaSolver(
            debug=True, 
            ocr_method="gpt4o"  # Explicitly use GPT-4o
        )

        if solver.debug: # Now solver is defined
            print("📄 Listing page frames after initial load and solver init:")
            for i, frame in enumerate(page.frames):
                frame_name = frame.name or "[no name]"
                frame_url = "[unavailable]"
                try:
                    frame_url = frame.url
                except Exception:
                    pass 
                print(f"  Frame {i}: Name='{frame_name}', URL='{frame_url}'")
                try:
                    if frame.parent_frame: 
                        owner = frame.frame_element()
                        if owner:
                             outer_html = owner.evaluate("el => el.outerHTML.substring(0, 250)")
                             print(f"    IFrame Element HTML: {outer_html.replace('\n', ' ')}")
                except Exception as e_frame_html:
                    print(f"    Could not get IFrame Element HTML: {e_frame_html}")
        
        # It's good to take a screenshot before trying to solve, for debugging
        pre_solve_screenshot_path = CAP_DIR / f"pre_solve_page_k_{int(time.time())}.png"
        page.screenshot(path=str(pre_solve_screenshot_path))
        print(f"📸 尝试解验证码前的截图已保存到: {pre_solve_screenshot_path}")

        if solver.debug:
            print("📄 Listing page frames before CAPTCHA solve attempt:")
            for i, frame in enumerate(page.frames):
                frame_name = frame.name or "[no name]"
                frame_url = "[unavailable]"
                try:
                    frame_url = frame.url
                except Exception:
                    pass
                print(f"  Frame {i}: Name='{frame_name}', URL='{frame_url}'")
                try:
                    if frame.parent_frame: 
                        owner = frame.frame_element()
                        if owner:
                             outer_html = owner.evaluate("el => el.outerHTML.substring(0, 250)")
                             print(f"    IFrame Element HTML: {outer_html.replace('\n', ' ')}")
                except Exception as e_frame_html:
                    print(f"    Could not get IFrame Element HTML: {e_frame_html}")

        text = solver.solve_from_playwright_page(page)  # 直接返回文本
        
        if text:
            print(f'✅ 验证码识别成功 (GPT-4o): {text}')
            input_box = None
            
            # ----- 仅保留一种方法：遍历所有 frame，基于 CSS 选择器查找 -----
            current_selectors = [
                'input[placeholder*="captcha" i]',
                'input[name*="captcha" i]',
                'input[id*="captcha" i]',
                'input[aria-label*="captcha" i]',
                'input[data-testid*="captcha" i]',
                'input[id*="mtcaptcha" i]',  # 针对 MTCaptcha
                'input[name*="mtcaptcha" i]',
                'input[type="text"][autocomplete*="off"]'
            ]

            frames_to_scan = page.frames
            for frame in frames_to_scan:
                frame_desc = frame.name or '[main]'
                for sel in current_selectors:
                    try:
                        elements = frame.query_selector_all(sel)
                    except Exception as e_sel:
                        if solver.debug:
                            print(f"⚠️ frame '{frame_desc}' 查询 '{sel}' 时报错: {e_sel}")
                        continue

                    for el in elements:
                        try:
                            if el.is_visible() and el.is_editable() and not (el.input_value() or "").strip():
                                input_box = el
                                print(f"📝 (方法1: CSS选择器) 在 frame '{frame_desc}' 找到验证码输入框 (selector: {sel}), 准备填入识别结果")
                                break
                        except Exception as e_chk:
                            if solver.debug:
                                print(f"⚠️ 检查元素时出错 frame '{frame_desc}' sel '{sel}': {e_chk}")
                    if input_box:
                        break
                if input_box:
                    break
            
            # 输入逻辑 (如果找到了 input_box)
            if input_box:
                try:
                    input_box.scroll_into_view_if_needed()
                    page.wait_for_timeout(50) 
                    input_box.focus()
                    page.wait_for_timeout(100) 
                    input_box.fill('') 
                    page.wait_for_timeout(100)
                    input_box.type(text, delay=150) # 增加一点延迟
                    print(f"✅ 已向定位到的输入框填入: {text}")
                except Exception as e:
                    print(f"❌ 尝试向定位的输入框 '{input_box.get_attribute('name') or input_box.get_attribute('id') or '[no id/name]'}' 填入文本时失败: {e}")
            else: 
                 print("❌ 未找到验证码输入框，无法输入验证码。")

        else:
            print("❌ 验证码识别失败 (GPT-4o)")
            # Save screenshot on failure
            failure_screenshot_path = CAP_DIR / f"captcha_failure_k_{int(time.time())}.png"
            page.screenshot(path=str(failure_screenshot_path))
            print(f"📸 验证码识别失败，截图已保存到: {failure_screenshot_path}")
            
        page.wait_for_timeout(1000) # Wait for text to be possibly processed by JS

        print("🔽 尝试点击下载按钮...")
        download_triggered = False
        # Enhanced download button selectors
        download_selectors = [
            'button:has-text("Download"):visible',
            'a[href*="download"]:visible',
            'button[id*="download"]:visible',
            'input[type="submit"][value*="Download" i]:visible',
            '[role="button"]:has-text("Download"):visible'
        ]
        for sel in download_selectors:
            btn = page.query_selector(sel)
            if btn:
                try:
                    print(f"✅ 找到下载按钮: {sel}")
                    btn.click()
                    download_triggered = True
                    break
                except Exception as e:
                    print(f"⚠️ 点击下载按钮 ({sel}) 失败: {e}")
        
        if not download_triggered:
            print("❌ 未找到或未能点击下载按钮")
            final_screenshot_path = CAP_DIR / f"no_download_trigger_k_{int(time.time())}.png"
            page.screenshot(path=str(final_screenshot_path))
            print(f"📸 未触发下载，截图: {final_screenshot_path}")

        print("⏳ 等待5秒观察下载情况或页面跳转...")
        time.sleep(5)

        # ----- 第二阶段：点击右侧活动面板中的下载图标 -----
        print("🔍 检测右侧活动面板中的下载图标...")

        second_download_selectors = [
            'button:has(svg[data-icon="download"])',
            '[class*="download"]:is(button, a)',
            'div[role="button"]:has(svg[data-icon="download"])',
            'button[aria-label*="Download" i]',
            'a[download]',
            '.fa-download',
            'svg[data-icon="download"]'
        ]

        second_clicked = False
        for attempt in range(10): # 尝试约5秒
            for sel in second_download_selectors:
                btn2 = page.query_selector(sel)
                if btn2 and btn2.is_visible():
                    try:
                        print(f"✅ 第二次下载按钮找到并点击: {sel}")
                        with page.expect_download(timeout=60000) as dl_info:
                            btn2.click()
                        download_obj = dl_info.value
                        suggested = download_obj.suggested_filename
                        dest_path = DOWNLOAD_DIR / suggested
                        try:
                            download_obj.save_as(str(dest_path))
                            print(f"💾 下载完成，已保存到: {dest_path.resolve()}")
                        except Exception as e_save:
                            print(f"❌ 保存下载文件失败: {e_save}")
                        second_clicked = True
                        break
                    except Exception as e2:
                        print(f"⚠️ 点击第二次下载按钮 ({sel}) 失败: {e2}")
            if second_clicked:
                break
            page.wait_for_timeout(500)

        if not second_clicked:
            print("❌ 可能验证码错误，尝试重新识别并提交...")

            max_retries = 2
            for attempt in range(1, max_retries+1):
                solver.extra_prompt = f"Previous OCR guess '{text}' was incorrect. Please re-extract the exact characters from the image only."
                new_text = solver.solve_from_playwright_page(page)
                if not new_text or new_text == text:
                    print(f"⚠️ 第{attempt}次重试未得到新结果: '{new_text}'. 终止重试。")
                    break

                print(f"🔄 第{attempt}次重试获得新验证码: {new_text}")

                # 重新填写验证码
                if input_box and input_box.is_visible():
                    try:
                        input_box.fill("")
                        page.wait_for_timeout(100)
                        input_box.type(new_text, delay=100)
                    except Exception as e_input:
                        print(f"❌ 重试时填写验证码失败: {e_input}")
                        break

                # 再次点击下载
                try:
                    with page.expect_download(timeout=60000) as dl_info:
                        for sel in download_selectors:
                            btn_retry = page.query_selector(sel)
                            if btn_retry and btn_retry.is_visible():
                                btn_retry.click()
                                break
                    download_obj = dl_info.value
                    suggested = download_obj.suggested_filename
                    dest_path = DOWNLOAD_DIR / suggested
                    try:
                        download_obj.save_as(str(dest_path))
                        print(f"💾 重试下载完成，已保存到: {dest_path.resolve()}")
                    except Exception as e_save2:
                        print(f"❌ 重试保存下载文件失败: {e_save2}")
                    second_clicked = True
                    break
                except Exception as e_retry:
                    print(f"⚠️ 重试点击下载失败或未捕获下载: {e_retry}")

            if not second_clicked:
                print("❌ 重试仍未成功，请人工检查。")

        # 再等待几秒
        time.sleep(3)

        # 保持浏览器与页面开启，方便手动检查；按 Ctrl+C 可终止脚本并关闭浏览器
        print("⚠️ 脚本已暂停，浏览器保持打开状态。按 Ctrl+C 结束并关闭浏览器。")
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            print("🛑 收到退出信号，正在关闭浏览器...")
            browser.close()

if __name__=='__main__':
    main() 