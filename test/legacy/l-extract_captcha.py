#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 L —— TraceParts完整CAD模型下载器 (验证码识别 + STL下载)
"""

import os
import sys
import time
from pathlib import Path
import importlib.util
from playwright.sync_api import sync_playwright, Route, Request, Response

# 导入验证码识别模块
sys.path.append(str(Path(__file__).parent.parent))
from utils.captcha_solver import solve_captcha_from_playwright

# ---------- 动态导入模块 ----------
def load_stealth_module():
    """延迟加载stealth模块，避免测试时的依赖问题"""
    BASE_DIR = Path(__file__).parent
    MOD11 = importlib.util.spec_from_file_location("stealth11j", BASE_DIR / "11j-stealth_cad_downloader_captcha.py")
    stealth11j = importlib.util.module_from_spec(MOD11)  # type: ignore
    MOD11.loader.exec_module(stealth11j)  # type: ignore
    return stealth11j

# ---------- 常量 ----------
CAP_DIR = Path("results/captcha_samples")
CAP_DIR.mkdir(parents=True, exist_ok=True)
DOWNLOAD_DIR = Path("results/downloads")
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
PRODUCT_URL = os.getenv("TRACEPARTS_PRODUCT_URL", "https://www.traceparts.cn/en/product/rs-pro-abs-plastic-sheet-stock1220x610x15mm?CatalogPath=TRACEPARTS%3ATP05009&Product=90-03062024-057087")

def main():
    """简化的主函数"""
    # 检查是否只是测试图片检测器
    if "--test-detector" in sys.argv:
        print("🧪 图片检测器功能已移除，请使用完整版本")
        return
    
    email = os.getenv("TRACEPARTS_EMAIL", "demo@example.com")
    pwd = os.getenv("TRACEPARTS_PASSWORD", "pass")
    print("===== 测试 L: TraceParts STL下载器 =====")
    
    # 加载stealth模块
    print("📦 加载隐身浏览器模块...")
    try:
        stealth11j = load_stealth_module()
    except Exception as e:
        print(f"❌ 无法加载stealth模块: {e}")
        return
    
    with sync_playwright() as p:
        browser, ctx, page = stealth11j.create_stealth_browser(p, headless=False)
        
        if not stealth11j.fast_stealth_login(page, email, pwd):
            return
        
        print(f"🎯 导航到产品页面: {PRODUCT_URL[:80]}...")
        page.goto(PRODUCT_URL, wait_until="domcontentloaded")
        
        # 更宽松的等待策略
        try:
            page.wait_for_load_state("networkidle", timeout=60000)  # 增加到60秒
        except Exception as e:
            print(f"⚠️ 页面加载超时，但继续执行: {e}")
            # 即使超时也继续，可能页面已经加载了主要内容
        
        # --- 格式选择和验证码处理 ---
        try:
            print("\n📋 开始处理下载流程...")
            
            # 第一步：选择格式
            print("\n1️⃣ 查找格式选择下拉菜单...")
            
            # 先截个图看看当前页面状态
            debug_screenshot = CAP_DIR / f"page_before_format_select_{int(time.time())}.png"
            page.screenshot(path=str(debug_screenshot))
            print(f"📷 页面截图: {debug_screenshot}")
            
            # 尝试多种方式定位下拉菜单
            format_selectors = [
                'select',  # 所有select元素
                'button:has-text("Please select")',
                'div:has-text("Please select")',
                '[placeholder*="select" i]',
                'select.form-control',
                'select.form-select'
            ]
            
            format_selector_found = False
            select_element = None
            
            for selector in format_selectors:
                try:
                    elements = page.query_selector_all(selector)
                    for element in elements:
                        try:
                            if element.is_visible():
                                # 检查元素文本
                                element_text = ""
                                try:
                                    element_text = element.text_content() or ""
                                    if "select" in element_text.lower():
                                        select_element = element
                                        print(f"✅ 找到格式选择器 (通过文本): {selector}")
                                        format_selector_found = True
                                        break
                                except:
                                    pass
                                
                                # 如果是select元素，检查其选项
                                if element.evaluate("el => el.tagName").lower() == "select":
                                    options = element.query_selector_all("option")
                                    if options and len(options) > 0:
                                        first_option_text = options[0].text_content() or ""
                                        if "select" in first_option_text.lower():
                                            select_element = element
                                            print(f"✅ 找到格式选择器 (select元素): {selector}")
                                            format_selector_found = True
                                            break
                        except:
                            pass
                    
                    if format_selector_found:
                        break
                except Exception as e:
                    print(f"检查选择器 {selector} 时出错: {e}")
            
            if format_selector_found and select_element:
                # 定义首选格式列表
                preferred_formats = ["STEP AP214", "STEP AP203", "STL", "IGES", "SOLIDWORKS", "Parasolid"]
                format_selected = False
                
                # 判断元素类型
                element_tag = select_element.evaluate("el => el.tagName").lower()
                
                if element_tag == "select":
                    # 处理原生select元素
                    print("🔧 处理原生select元素...")
                    
                    # 获取所有选项
                    options = select_element.query_selector_all("option")
                    print(f"📑 找到 {len(options)} 个选项")
                    
                    # 尝试选择首选格式
                    for format_name in preferred_formats:
                        for i, option in enumerate(options):
                            option_text = option.text_content() or ""
                            if format_name.lower() in option_text.lower():
                                try:
                                    select_element.select_option(index=i)
                                    print(f"✅ 选择了格式: {format_name} (索引: {i})")
                                    format_selected = True
                                    break
                                except Exception as e:
                                    print(f"选择选项时出错: {e}")
                        
                        if format_selected:
                            break
                    
                    # 如果没有找到首选格式，选择第一个非空选项
                    if not format_selected and len(options) > 1:
                        try:
                            select_element.select_option(index=1)
                            selected_text = options[1].text_content() if len(options) > 1 else "未知"
                            print(f"✅ 选择了第一个可用格式: {selected_text}")
                            format_selected = True
                        except:
                            print("⚠️ 无法选择默认格式")
                
                # 等待页面更新
                if format_selected:
                    page.wait_for_timeout(2000)
                    print("⏳ 等待页面更新...")
                    
                    # 再次截图查看选择后的状态
                    after_select_screenshot = CAP_DIR / f"page_after_format_select_{int(time.time())}.png"
                    page.screenshot(path=str(after_select_screenshot))
                    print(f"📷 格式选择后截图: {after_select_screenshot}")
            else:
                print("ℹ️ 未发现格式选择器")
            
            # 第二步：处理验证码
            print("\n2️⃣ 检查验证码...")
            
            # 先尝试识别验证码（即使还没找到输入框）
            print("🤖 尝试识别页面上的验证码...")
            captcha_text = None
            try:
                captcha_text = solve_captcha_from_playwright(page, icon_path="01.png", debug=True)
                if captcha_text:
                    print(f"✅ 验证码识别成功: '{captcha_text}'")
                else:
                    print("❌ 未能识别到验证码")
            except Exception as e:
                print(f"❌ 验证码识别出错: {e}")
            
            # 尝试定位验证码输入框
            captcha_input = None
            captcha_selectors = [
                'input[placeholder="captcha"]',
                'input[placeholder="captcha" i]',
                'input[name="captcha"]',
                'input[id*="captcha"]',
                'input[type="text"][placeholder*="captcha" i]',
                'input[type="text"]',  # 更通用的文本输入框
                'input:not([type="hidden"]):not([type="submit"]):not([type="button"])'  # 所有可见的输入框
            ]
            
            print("🔍 查找验证码输入框...")
            for selector in captcha_selectors:
                try:
                    elements = page.query_selector_all(selector)
                    for element in elements:
                        if element.is_visible():
                            # 检查输入框附近是否有验证码相关的文本或图片
                            try:
                                # 获取输入框的位置信息
                                bbox = element.bounding_box()
                                if bbox:
                                    # 检查placeholder或其他属性
                                    placeholder = element.get_attribute("placeholder") or ""
                                    name = element.get_attribute("name") or ""
                                    id_attr = element.get_attribute("id") or ""
                                    
                                    # 检查是否可能是验证码输入框
                                    if ("captcha" in placeholder.lower() or 
                                        "captcha" in name.lower() or 
                                        "captcha" in id_attr.lower() or
                                        (captcha_text and len(elements) < 5)):  # 如果识别到验证码且输入框不多，可能就是验证码输入框
                                        
                                        captcha_input = element
                                        print(f"✅ 找到验证码输入框: {selector}")
                                        print(f"   placeholder: '{placeholder}'")
                                        print(f"   name: '{name}'")
                                        print(f"   id: '{id_attr}'")
                                        break
                            except:
                                pass
                    
                    if captcha_input:
                        break
                except Exception as e:
                    print(f"   检查选择器 {selector} 时出错: {e}")
            
            # 如果识别到验证码但没找到明确的输入框，尝试找到唯一的空文本框
            if captcha_text and not captcha_input:
                print("🔍 识别到验证码但未找到明确的输入框，尝试查找空的文本输入框...")
                try:
                    text_inputs = page.query_selector_all('input[type="text"]:visible, input:not([type]):visible')
                    empty_inputs = []
                    for inp in text_inputs:
                        if inp.is_visible():
                            value = inp.get_attribute("value") or ""
                            if not value.strip():
                                empty_inputs.append(inp)
                    
                    if len(empty_inputs) == 1:
                        captcha_input = empty_inputs[0]
                        print("✅ 找到唯一的空文本输入框，可能是验证码输入框")
                    elif len(empty_inputs) > 1:
                        print(f"⚠️ 找到 {len(empty_inputs)} 个空输入框，无法确定哪个是验证码输入框")
                except:
                    pass
            
            # 填写验证码
            if captcha_input and captcha_text:
                try:
                    print("📝 正在填写验证码...")
                    # 清空输入框
                    captcha_input.click()
                    page.wait_for_timeout(200)
                    captcha_input.fill("")
                    page.wait_for_timeout(200)
                    # 填入验证码
                    captcha_input.type(captcha_text, delay=100)  # 使用type方法模拟真实输入
                    print("✅ 验证码已填入")
                    
                    # 等待一下
                    page.wait_for_timeout(1000)
                except Exception as e:
                    print(f"❌ 填写验证码时出错: {e}")
            elif captcha_text and not captcha_input:
                print("⚠️ 识别到验证码但未找到输入框")
                # 截图保存当前状态
                no_input_screenshot = CAP_DIR / f"page_captcha_no_input_{int(time.time())}.png"
                page.screenshot(path=str(no_input_screenshot))
                print(f"📷 保存页面状态: {no_input_screenshot}")
            elif not captcha_text:
                print("ℹ️ 未识别到验证码（可能不需要）")
            
            # 等待一下确保页面稳定
            page.wait_for_timeout(1000)
            
            # 第三步：查找并点击下载按钮
            print("\n3️⃣ 查找下载按钮...")
            download_clicked = False
            
            # 尝试多种下载按钮选择器
            download_button_selectors = [
                # 下载图标按钮
                'a[href*="download"]',
                'button[onclick*="download" i]',
                'a[onclick*="download" i]',
                # 下载文字按钮
                'button:has-text("Download")',
                'a:has-text("Download")',
                'button:has-text("下载")',
                'a:has-text("下载")',
                # 通用按钮
                'button[type="submit"]',
                'input[type="submit"]',
                # 图标按钮
                'button.download-button',
                'a.download-link',
                'button.btn-download',
                'a.btn-download',
                # 可能的图标按钮
                'button[title*="download" i]',
                'a[title*="download" i]',
                'button[aria-label*="download" i]',
                'a[aria-label*="download" i]',
                # SVG图标按钮
                'button:has(svg)',
                'a:has(svg)',
                # 特定class的按钮
                'button.btn',
                'a.btn'
            ]
            
            # 先截个图看看当前页面
            download_debug_screenshot = CAP_DIR / f"page_before_download_{int(time.time())}.png"
            page.screenshot(path=str(download_debug_screenshot))
            print(f"📷 下载前页面截图: {download_debug_screenshot}")
            
            for selector in download_button_selectors:
                try:
                    buttons = page.query_selector_all(selector)
                    for button in buttons:
                        try:
                            if button.is_visible() and button.is_enabled():
                                # 获取按钮信息用于调试
                                button_text = ""
                                try:
                                    button_text = button.text_content() or ""
                                except:
                                    pass
                                
                                # 检查是否是下载相关的按钮
                                button_html = button.evaluate("el => el.outerHTML")
                                if ("download" in button_html.lower() or 
                                    "下载" in button_html or 
                                    "arrow-down" in button_html or
                                    "fa-download" in button_html or
                                    len(button_text.strip()) == 0):  # 空文本可能是图标按钮
                                    
                                    print(f"🎯 找到可能的下载按钮: {selector}")
                                    print(f"   按钮文本: '{button_text.strip()}'")
                                    
                                    # 滚动到按钮位置
                                    button.scroll_into_view_if_needed()
                                    page.wait_for_timeout(500)
                                    
                                    # 点击按钮
                                    button.click()
                                    print("✅ 已点击下载按钮")
                                    download_clicked = True
                                    
                                    # 等待下载开始
                                    page.wait_for_timeout(3000)
                                    
                                    # 截图查看点击后的效果
                                    after_click_screenshot = CAP_DIR / f"page_after_download_click_{int(time.time())}.png"
                                    page.screenshot(path=str(after_click_screenshot))
                                    print(f"📷 点击下载后截图: {after_click_screenshot}")
                                    
                                    break
                        except Exception as e:
                            print(f"   尝试点击按钮时出错: {e}")
                    
                    if download_clicked:
                        break
                        
                except Exception as e:
                    print(f"检查选择器 {selector} 时出错: {e}")
            
            if not download_clicked:
                print("⚠️ 未找到可点击的下载按钮")
                
                # 最后尝试：查找所有可点击的元素
                print("🔍 尝试查找所有可点击元素...")
                clickable_elements = page.query_selector_all('button, a, input[type="button"], input[type="submit"]')
                print(f"   找到 {len(clickable_elements)} 个可点击元素")
                
                # 如果验证码已填写，尝试按Enter键提交
                if captcha_input and captcha_text:
                    try:
                        print("⏎ 尝试在验证码输入框按Enter键提交...")
                        captcha_input.press("Enter")
                        page.wait_for_timeout(2000)
                    except:
                        pass
        except Exception as e:
            print(f"⚠️ 处理过程中出现错误: {e}")
            import traceback
            traceback.print_exc()
        
        # --- 原有的截图和分析流程 ---
        # 截图页面
        screenshot_path = CAP_DIR / f"page_screenshot_after_attempt_{int(time.time())}.png"
        page.screenshot(path=str(screenshot_path), full_page=True)
        print(f"📷 页面截图 (尝试处理验证码后): {screenshot_path}")
        
        user_choice = input("\n🔽 是否继续分析页面下载选项 (如果自动填充失败，请手动输入验证码后按y)? (y/n): ").lower().strip()
        
        if user_choice in ['y', 'yes', '是']:
            # 简单页面分析
            print("\n🔍 分析页面...")
            
            # 查找所有链接和按钮
            links = page.query_selector_all('a')
            buttons = page.query_selector_all('button')
            
            print(f"📊 页面元素统计:")
            print(f"  - 链接: {len(links)}个")
            print(f"  - 按钮: {len(buttons)}个")
            
            # 查找可能的下载元素
            download_keywords = ['download', 'cad', 'stl', '下载']
            found_elements = []
            
            for link in links[:20]:  # 只检查前20个链接
                try:
                    text = link.text_content().strip().lower()
                    href = link.get_attribute('href') or ''
                    if any(keyword in text or keyword in href.lower() for keyword in download_keywords):
                        found_elements.append(('link', text[:50], href[:50]))
                except:
                    pass
            
            for button in buttons[:10]:  # 只检查前10个按钮
                try:
                    text = button.text_content().strip().lower()
                    if any(keyword in text for keyword in download_keywords):
                        found_elements.append(('button', text[:50], ''))
                except:
                    pass
            
            if found_elements:
                print(f"\n✅ 找到 {len(found_elements)} 个可能的下载元素:")
                for i, (elem_type, text, href) in enumerate(found_elements):
                    print(f"  {i+1}. [{elem_type}] {text}")
                    if href:
                        print(f"     链接: {href}")
            else:
                print("\n❌ 未找到明显的下载元素")
                print("💡 这可能需要登录后的特殊权限或在其他页面区域")
        
        input("\n按回车退出...")
        browser.close()

if __name__ == "__main__":
    main() 