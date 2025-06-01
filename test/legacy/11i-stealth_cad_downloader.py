#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 11i —— 彻底隐身的CAD下载器
基于发现的检测差异，实现完全隐身的自动化CAD下载
"""

from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync
import time
import os
import random
import json
from pathlib import Path

def create_stealth_browser(playwright_instance, headless=False):
    """创建完全隐身的浏览器"""
    # 使用真实的Chrome路径（如果可用）
    browser = playwright_instance.chromium.launch(
        headless=headless,
        slow_mo=random.randint(100, 300),  # 随机延迟
        args=[
            '--disable-blink-features=AutomationControlled',
            '--disable-features=VizDisplayCompositor',
            '--disable-web-security',
            '--disable-features=TranslateUI',
            '--disable-ipc-flooding-protection',
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--no-first-run',
            '--no-zygote',
            '--disable-background-timer-throttling',
            '--disable-backgrounding-occluded-windows',
            '--disable-renderer-backgrounding',
            '--disable-features=TranslateUI',
            '--disable-default-apps',
            '--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            '--enable-webgl',
            '--ignore-gpu-blocklist',
        ]
    )
    
    # 创建上下文时设置真实的用户代理
    downloads_dir = Path("results/downloads")
    downloads_dir.mkdir(parents=True, exist_ok=True)
    context = browser.new_context(
        viewport={'width': 1366, 'height': 768},
        user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        locale='en-US',
        timezone_id='America/New_York',
        accept_downloads=True
    )
    
    page = context.new_page()
    
    # 应用stealth
    stealth_sync(page)
    
    # 修复playwright_stealth中的UA getter错误 (opts未定义)
    page.add_init_script("""
        try {
            const uaStr = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36';
            Object.defineProperty(navigator, 'userAgent', {
                get: () => uaStr,
                configurable: true
            });
        } catch (e) {
            console.warn('UA patch error', e);
        }
    """)
    
    # 额外的反检测脚本
    page.add_init_script("""
        // 完全删除webdriver属性
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined,
        });
        
        // 由于已在context级别设置真实UA，这里不再覆盖，避免潜在脚本冲突
        
        // 完善Chrome对象
        window.chrome = {
            runtime: {
                onConnect: undefined,
                onMessage: undefined
            },
            loadTimes: function() {
                return {
                    commitLoadTime: Date.now() - Math.random() * 1000,
                    connectionInfo: 'h2',
                    finishDocumentLoadTime: Date.now() - Math.random() * 500,
                    finishLoadTime: Date.now() - Math.random() * 200,
                    firstPaintAfterLoadTime: 0,
                    firstPaintTime: Date.now() - Math.random() * 300,
                    navigationType: 'Navigation',
                    npnNegotiatedProtocol: 'h2',
                    requestTime: Date.now() - Math.random() * 2000,
                    startLoadTime: Date.now() - Math.random() * 1500,
                    wasAlternateProtocolAvailable: false,
                    wasFetchedViaSpdy: true,
                    wasNpnNegotiated: true
                };
            },
            csi: function() {
                return {
                    pageT: Date.now() - Math.random() * 1000,
                    tran: Math.floor(Math.random() * 20)
                };
            },
            app: {
                isInstalled: false,
                InstallState: {
                    DISABLED: 'disabled',
                    INSTALLED: 'installed',
                    NOT_INSTALLED: 'not_installed'
                },
                RunningState: {
                    CANNOT_RUN: 'cannot_run',
                    READY_TO_RUN: 'ready_to_run',
                    RUNNING: 'running'
                }
            }
        };
        
        // 完善插件信息
        Object.defineProperty(navigator, 'plugins', {
            get: () => [
                {
                    0: {type: "application/x-google-chrome-pdf", suffixes: "pdf", description: "Portable Document Format", enabledPlugin: {}},
                    description: "Portable Document Format",
                    filename: "internal-pdf-viewer",
                    length: 1,
                    name: "Chrome PDF Plugin"
                },
                {
                    0: {type: "application/pdf", suffixes: "pdf", description: "", enabledPlugin: {}},
                    description: "",
                    filename: "mhjfbmdgcfjbbpaeojofohoefgiehjai",
                    length: 1,
                    name: "Chrome PDF Viewer"
                },
                {
                    0: {type: "application/x-nacl", suffixes: "", description: "Native Client Executable", enabledPlugin: {}},
                    1: {type: "application/x-pnacl", suffixes: "", description: "Portable Native Client Executable", enabledPlugin: {}},
                    description: "",
                    filename: "internal-nacl-plugin",
                    length: 2,
                    name: "Native Client"
                }
            ],
        });
        
        // 删除所有自动化特征
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_JSON;
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Object;
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Proxy;
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Reflect;
        
        // 修复权限查询
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
        );
        
        // 添加真实的languages
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en', 'zh-CN', 'zh'],
        });
        
        // 伪造真实的内存信息
        Object.defineProperty(navigator, 'deviceMemory', {
            get: () => 8,
        });
        
        // 伪造硬件并发
        Object.defineProperty(navigator, 'hardwareConcurrency', {
            get: () => 8,
        });
    """)
    
    return browser, context, page

def human_like_delay(min_delay=0.5, max_delay=2.0):
    """人类行为延迟"""
    delay = random.uniform(min_delay, max_delay)
    time.sleep(delay)

def human_like_typing(page, selector, text, delay_range=(50, 150)):
    """模拟人类打字"""
    element = page.locator(selector)
    element.click()
    human_like_delay(0.3, 0.8)
    
    # 清空字段
    element.fill("")
    human_like_delay(0.2, 0.5)
    
    # 逐字符输入
    for char in text:
        element.type(char, delay=random.randint(*delay_range))

def stealth_login(page, email, password):
    """隐身登录"""
    print("🔐 开始隐身登录...")
    
    # 访问登录页面
    page.goto("https://www.traceparts.cn/en/sign-in", wait_until="networkidle")
    human_like_delay(2, 4)
    
    # 模拟真实用户行为 - 滚动页面
    page.evaluate("window.scrollTo(0, 100)")
    human_like_delay(0.5, 1.0)
    page.evaluate("window.scrollTo(0, 0)")
    human_like_delay(0.5, 1.0)
    
    # 输入邮箱
    print("📧 输入邮箱...")
    human_like_typing(page, "input[type='email']", email)
    human_like_delay(0.8, 1.5)
    
    # 输入密码  
    print("🔑 输入密码...")
    human_like_typing(page, "input[type='password']", password)
    human_like_delay(1.0, 2.0)
    
    # 模拟检查输入
    page.evaluate("""
        document.querySelector('input[type="email"]').focus();
        setTimeout(() => document.querySelector('input[type="password"]').focus(), 200);
    """)
    human_like_delay(0.5, 1.0)
    
    # 点击登录按钮
    print("🚀 点击登录...")
    submit_btn = page.locator("button:has-text('Sign in')").first
    submit_btn.hover()
    human_like_delay(0.3, 0.8)
    submit_btn.click()
    
    # 等待登录响应
    print("⏳ 等待登录响应...")
    human_like_delay(3, 6)
    
    # 检查是否成功
    current_url = page.url
    # 保存调试信息
    debug_dir = Path("results/stealth_debug")
    debug_dir.mkdir(parents=True, exist_ok=True)
    timestamp = int(time.time())
    
    if "sign-in" not in current_url.lower():
        print("✅ 登录成功！")
        page.screenshot(path=f"results/stealth_debug/login_success_{timestamp}.png")
        print(f"📸 登录成功截图: results/stealth_debug/login_success_{timestamp}.png")
        print(f"🌐 当前URL: {current_url}")
        return True
    else:
        print("❌ 登录失败")
        page.screenshot(path=f"results/stealth_debug/login_fail_{timestamp}.png")
        print(f"📸 登录失败截图: results/stealth_debug/login_fail_{timestamp}.png")
        return False

def navigate_to_product_with_stealth(page):
    """隐身导航到产品页面"""
    print("📦 隐身导航到产品页面...")
    
    # 先访问首页，模拟正常浏览行为
    page.goto("https://www.traceparts.cn/en", wait_until="networkidle")
    human_like_delay(2, 4)
    
    # 模拟浏览行为
    page.evaluate("window.scrollTo(0, 300)")
    human_like_delay(1, 2)
    page.evaluate("window.scrollTo(0, 600)")
    human_like_delay(1, 2)
    page.evaluate("window.scrollTo(0, 0)")
    human_like_delay(1, 2)
    
    # 访问产品页面，使用更简化的方式
    product_url = "https://www.traceparts.cn/en/product/rs-pro-abs-plastic-sheet-stock1220x610x15mm?CatalogPath=TRACEPARTS%3ATP05009&Product=90-03062024-057087"
    print(f"🎯 访问产品页面: {product_url}")
    
    try:
        page.goto(product_url, wait_until="domcontentloaded", timeout=60000)
        human_like_delay(3, 5)
        
        # 等待页面稳定
        page.wait_for_load_state("networkidle", timeout=30000)
    except Exception as e:
        print(f"⚠️ 页面加载超时，但继续分析: {e}")
        human_like_delay(2, 3)
    
    # 检查页面是否正确加载
    title = page.title()
    print(f"📄 页面标题: {title}")
    
    if "sign-in" in page.url.lower():
        print("❌ 被重定向到登录页")
        return False
    
    return True

def locate_and_download_cad(page):
    """定位并下载CAD文件"""
    print("🔍 寻找CAD下载区域...")
    
    # 模拟真实用户浏览页面
    page.evaluate("window.scrollTo(0, 200)")
    human_like_delay(1, 2)
    page.evaluate("window.scrollTo(0, 400)")  
    human_like_delay(1, 2)
    page.evaluate("window.scrollTo(0, 600)")
    human_like_delay(1, 2)
    
    # 截图当前状态
    debug_dir = Path("results/stealth_debug")
    debug_dir.mkdir(parents=True, exist_ok=True)
    timestamp = int(time.time())
    page.screenshot(path=f"results/stealth_debug/cad_search_{timestamp}.png", full_page=True)
    
    # 分析页面内容
    print("📋 分析页面内容...")
    body_text = page.text_content("body")
    print(f"   页面文本长度: {len(body_text)}")
    
    # 检查CAD相关内容
    cad_keywords = ["cad", "3d", "model", "download", "stl", "step", "iges", "format"]
    found_cad_keywords = []
    for keyword in cad_keywords:
        if keyword in body_text.lower():
            count = body_text.lower().count(keyword)
            found_cad_keywords.append(f"{keyword}({count})")
    
    print(f"   CAD关键词: {found_cad_keywords}")
    
    # 查找CAD Models选项卡
    cad_tab_selectors = [
        "a:has-text('CAD models')",
        "a:has-text('CAD')",
        "a:has-text('3D')",
        "[data-toggle='tab']:has-text('CAD')",
        "li:has-text('CAD models') a",
    ]
    
    cad_tab = None
    for selector in cad_tab_selectors:
        try:
            element = page.locator(selector)
            if element.is_visible():
                cad_tab = element
                print(f"✅ 找到CAD选项卡: {selector}")
                break
        except:
            continue
    
    if cad_tab:
        print("🖱️ 点击CAD Models选项卡...")
        cad_tab.hover()
        human_like_delay(0.5, 1.0)
        cad_tab.click()
        human_like_delay(2, 4)
    else:
        print("⚠️ 未找到CAD Models选项卡")
    
    # 查找CAD格式选择器
    print("🔽 寻找CAD格式选择器...")
    cad_format_selector = None
    
    # 多种选择器尝试
    format_selectors = [
        "#cad-format-select",
        "select[id*='format']",
        "select[name*='format']",
        "select:has(option:text('STEP'))",
        "select:has(option:text('STL'))",
    ]
    
    for selector in format_selectors:
        try:
            element = page.locator(selector)
            if element.is_visible():
                cad_format_selector = element
                print(f"✅ 找到CAD格式选择器: {selector}")
                break
        except:
            continue
    
    if cad_format_selector:
        # 获取所有格式选项
        options = cad_format_selector.locator("option").all()
        available_formats = []
        for opt in options:
            text = opt.text_content()
            value = opt.get_attribute("value")
            if text and text.strip() and text.strip() != "Please select":
                available_formats.append({"text": text.strip(), "value": value})
        
        print(f"📦 可用CAD格式 ({len(available_formats)}个):")
        for i, fmt in enumerate(available_formats[:10]):  # 只显示前10个
            print(f"   {i+1}. {fmt['text']}")
        if len(available_formats) > 10:
            print(f"   ... 还有 {len(available_formats)-10} 个格式")
        
        # 优先选择常用格式
        preferred_formats = ["STEP AP214", "STEP AP203", "STL", "IGES", "SOLIDWORKS", "Parasolid"]
        selected_format = None
        
        for pref in preferred_formats:
            for fmt in available_formats:
                if pref.lower() in fmt["text"].lower():
                    selected_format = fmt
                    break
            if selected_format:
                break
        
        # 如果没有找到优先格式，选择第一个非空的
        if not selected_format and available_formats:
            selected_format = available_formats[0]
        
        if selected_format:
            print(f"🎯 选择CAD格式: {selected_format['text']}")
            
            # 点击选择器
            cad_format_selector.click()
            human_like_delay(0.5, 1.0)
            
            # 选择格式
            if selected_format["value"]:
                cad_format_selector.select_option(selected_format["value"])
            else:
                # 如果没有value，通过文本选择
                cad_format_selector.select_option(label=selected_format["text"])
            
            human_like_delay(1.0, 2.0)
            print(f"✅ 已选择格式: {selected_format['text']}")
        else:
            print("❌ 未找到可用的CAD格式")
            return False
    else:
        print("❌ 未找到CAD格式选择器")
        return False
    
    # 选择格式后检查是否需要点击"Generate"
    generate_btn_selectors = [
        "button:has-text('Generate')",
        "button:has-text('Generate CAD model')",
        "#generate-cad-model",
        "button[id*='generate']"
    ]
    
    generate_btn = None
    for selector in generate_btn_selectors:
        try:
            elem = page.locator(selector)
            if elem.is_visible():
                generate_btn = elem
                print(f"🔧 找到生成按钮: {selector}")
                break
        except:
            continue
    
    if generate_btn:
        generate_btn.hover()
        human_like_delay(0.5, 1.0)
        generate_btn.click()
        print("⚙️ 已点击生成CAD模型，等待处理...")
    else:
        print("⚠️ 未找到生成按钮，可能不需要此步骤")
    
    # 等待下载按钮可用
    def download_button_enabled():
        btn = page.locator("#direct-cad-download")
        if btn.count() == 0:
            return False
        classes = btn.get_attribute("class") or ""
        return "disabled" not in classes.lower()
    
    for _ in range(30):  # 最长等待约30秒
        if download_button_enabled():
            print("✅ 下载按钮已激活！")
            break
        human_like_delay(1.0, 1.5)
    else:
        print("⚠️ 下载按钮始终未激活 (超时)")
    
    # 截图最终状态
    page.screenshot(path=f"results/stealth_debug/after_download_attempt_{timestamp}.png", full_page=True)
    print(f"📸 下载尝试截图: results/stealth_debug/after_download_attempt_{timestamp}.png")
    
    # 检查页面是否有错误信息
    error_selectors = [
        ".alert-danger",
        ".error",
        "[class*='error']",
        ".message.error"
    ]
    
    for selector in error_selectors:
        try:
            error_elements = page.locator(selector).all()
            for elem in error_elements:
                if elem.is_visible():
                    error_text = elem.text_content()
                    if error_text and error_text.strip():
                        print(f"⚠️ 发现错误信息: {error_text.strip()}")
        except:
            continue
    
    return False

def main():
    """主函数"""
    email = os.getenv("TRACEPARTS_EMAIL", "SearcherKerry36154@hotmail.com")
    password = os.getenv("TRACEPARTS_PASSWORD", "Vsn220mh@")
    
    print("🥷 TraceParts 隐身CAD下载器")
    print("=" * 60)
    print(f"账号: {email}")
    print(f"密码: {'*' * len(password)}")
    
    with sync_playwright() as p:
        try:
            browser, context, page = create_stealth_browser(p, headless=False)
            
            # 步骤1: 隐身登录
            if not stealth_login(page, email, password):
                print("❌ 登录失败，停止执行")
                browser.close()
                return
            
            # 步骤2: 导航到产品页面
            if not navigate_to_product_with_stealth(page):
                print("❌ 产品页面访问失败，停止执行")
                browser.close()
                return
            
            # 步骤3: 定位并分析CAD区域
            if locate_and_download_cad(page):
                print("✅ 发现CAD相关元素")
            else:
                print("❌ 未发现CAD相关元素")
            
            print("\n🎯 流程完成！浏览器将保持开启以供检查...")
            input("按回车键关闭浏览器...")
            
            browser.close()
            
        except Exception as e:
            print(f"❌ 执行过程出错: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main() 