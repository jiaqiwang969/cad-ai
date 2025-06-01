#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 11g —— TraceParts 检测机制诊断
深入分析为什么CAD内容不加载的原因和检测机制
"""

from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync
import time
import os
import random
import json
import re
from pathlib import Path

def analyze_page_detection_signals(page):
    """分析页面中的检测信号"""
    print("\n🔍 分析页面检测信号...")
    
    # 检查JavaScript检测
    js_checks = [
        "navigator.webdriver",
        "window.chrome",
        "window.callPhantom", 
        "window._phantom",
        "window.Buffer",
        "document.$cdc_asdjflasutopfhvcZLmcfl_",
        "navigator.plugins.length",
        "navigator.languages",
        "screen.width && screen.height"
    ]
    
    detection_results = {}
    for check in js_checks:
        try:
            result = page.evaluate(f"typeof {check}")
            detection_results[check] = result
            print(f"   {check}: {result}")
        except:
            detection_results[check] = "error"
    
    # 检查用户代理
    try:
        user_agent = page.evaluate("navigator.userAgent")
        print(f"   User Agent: {user_agent}")
    except Exception as e:
        print(f"   User Agent: error - {e}")
    
    # 检查插件
    try:
        plugins = page.evaluate("Array.from(navigator.plugins).map(p => p.name)")
        print(f"   Plugins: {plugins}")
    except Exception as e:
        print(f"   Plugins: error - {e}")
    
    # 检查权限
    try:
        permissions = page.evaluate("""
            navigator.permissions.query({name: 'notifications'}).then(result => result.state)
        """)
        print(f"   Permissions: {permissions}")
    except Exception as e:
        print(f"   Permissions: error - {e}")
    
    return detection_results

def check_network_fingerprinting(page):
    """检查网络指纹识别"""
    print("\n🌐 检查网络指纹...")
    
    # 检查TLS指纹
    try:
        # 检查请求头
        headers = {}
        page.on("request", lambda request: headers.update(dict(request.headers)))
        page.goto("https://httpbin.org/headers", wait_until="networkidle")
        print(f"   请求头数量: {len(headers)}")
        
        # 检查是否有自动化特征
        automation_headers = ["selenium", "webdriver", "playwright", "automation", "headless"]
        found_automation = []
        for key, value in headers.items():
            for auto_key in automation_headers:
                if auto_key.lower() in key.lower() or auto_key.lower() in str(value).lower():
                    found_automation.append(f"{key}: {value}")
        
        if found_automation:
            print(f"   ⚠️ 发现自动化特征: {found_automation}")
        else:
            print("   ✅ 未发现明显自动化特征")
            
    except Exception as e:
        print(f"   ❌ 网络检查失败: {e}")

def analyze_traceparts_login_flow(page):
    """分析TraceParts登录流程"""
    print("\n🔐 分析TraceParts登录流程...")
    
    # 检查登录页面特征
    page.goto("https://www.traceparts.cn/en/sign-in", wait_until="networkidle")
    
    # 检查页面加载的脚本
    scripts = page.query_selector_all("script[src]")
    external_scripts = []
    for script in scripts:
        src = script.get_attribute("src")
        if src:
            external_scripts.append(src)
    
    print(f"   外部脚本数量: {len(external_scripts)}")
    
    # 检查安全相关脚本
    security_scripts = []
    security_keywords = ["security", "captcha", "recaptcha", "hcaptcha", "cloudflare", "akamai", "bot", "detect"]
    for script in external_scripts:
        for keyword in security_keywords:
            if keyword in script.lower():
                security_scripts.append(script)
                break
    
    if security_scripts:
        print(f"   🚨 发现安全脚本: {security_scripts}")
    else:
        print("   ✅ 未发现明显安全脚本")
    
    # 检查表单特征
    form = page.query_selector("form")
    if form:
        form_html = form.inner_html()
        print(f"   表单HTML长度: {len(form_html)}")
        
        # 检查隐藏字段
        hidden_inputs = page.query_selector_all("input[type='hidden']")
        print(f"   隐藏字段数量: {len(hidden_inputs)}")
        
        for hidden in hidden_inputs:
            name = hidden.get_attribute("name") or "unnamed"
            value = hidden.get_attribute("value") or "empty"
            print(f"     {name}: {value[:50]}...")
    
    return external_scripts, security_scripts

def test_product_page_cad_loading(page, email, password):
    """测试产品页面CAD加载"""
    print("\n📦 测试产品页面CAD加载...")
    
    # 先登录
    email_input = page.locator("input[type='email']")
    email_input.fill(email)
    page.wait_for_timeout(1000)
    
    pwd_input = page.locator("input[type='password']")
    pwd_input.fill(password)
    page.wait_for_timeout(1000)
    
    submit_btn = page.locator("button:has-text('Sign in')").first
    submit_btn.click()
    page.wait_for_timeout(5000)
    
    # 检查登录状态
    if "sign-in" in page.url:
        print("   ❌ 登录失败")
        return False
    
    print("   ✅ 登录成功")
    
    # 访问产品页面
    product_url = "https://www.traceparts.cn/en/product/rs-pro-abs-plastic-sheet-stock1220x610x15mm?CatalogPath=TRACEPARTS%3ATP05009&Product=90-03062024-057087"
    page.goto(product_url, wait_until="networkidle")
    page.wait_for_timeout(5000)
    
    # 详细分析页面内容
    print("\n📋 详细分析产品页面...")
    
    # 检查页面标题和URL
    title = page.title()
    current_url = page.url
    print(f"   页面标题: {title}")
    print(f"   当前URL: {current_url}")
    
    # 检查是否被重定向
    if "sign-in" in current_url.lower():
        print("   ❌ 被重定向到登录页")
        return False
    
    # 分析页面结构
    body_text = page.text_content("body")
    page_html = page.content()
    
    print(f"   页面文本长度: {len(body_text)}")
    print(f"   页面HTML长度: {len(page_html)}")
    
    # 检查CAD相关内容
    cad_keywords = ["cad", "3d", "model", "download", "stl", "step", "iges", "format"]
    found_cad_keywords = []
    for keyword in cad_keywords:
        if keyword in body_text.lower():
            count = body_text.lower().count(keyword)
            found_cad_keywords.append(f"{keyword}({count})")
    
    print(f"   CAD关键词: {found_cad_keywords}")
    
    # 检查选择器和下拉框
    selects = page.query_selector_all("select")
    print(f"   下拉选择器数量: {len(selects)}")
    
    for i, select in enumerate(selects):
        try:
            select_id = select.get_attribute("id") or f"select-{i}"
            is_visible = select.is_visible()
            is_enabled = select.is_enabled()
            
            print(f"     选择器 {i}: id='{select_id}', 可见={is_visible}, 启用={is_enabled}")
            
            if is_visible:
                options = select.query_selector_all("option")
                option_texts = []
                for opt in options:
                    text = opt.text_content() or ""
                    if text.strip():
                        option_texts.append(text.strip())
                
                print(f"       选项: {option_texts}")
        except Exception as e:
            print(f"       分析选择器失败: {e}")
    
    # 检查按钮
    buttons = page.query_selector_all("button, input[type='button'], input[type='submit']")
    print(f"   按钮数量: {len(buttons)}")
    
    download_buttons = []
    for i, btn in enumerate(buttons):
        try:
            btn_text = btn.text_content() or ""
            btn_class = btn.get_attribute("class") or ""
            btn_id = btn.get_attribute("id") or ""
            
            combined = (btn_text + btn_class + btn_id).lower()
            if any(kw in combined for kw in ["download", "get", "export", "cad"]):
                is_visible = btn.is_visible()
                is_enabled = btn.is_enabled()
                download_buttons.append({
                    "index": i,
                    "text": btn_text,
                    "class": btn_class,
                    "id": btn_id,
                    "visible": is_visible,
                    "enabled": is_enabled
                })
        except:
            continue
    
    print(f"   下载相关按钮: {len(download_buttons)}")
    for btn in download_buttons:
        print(f"     {btn}")
    
    # 检查是否有特殊的登录验证
    auth_indicators = ["please sign in", "login required", "authentication", "session", "access denied"]
    auth_messages = []
    for indicator in auth_indicators:
        if indicator in body_text.lower():
            auth_messages.append(indicator)
    
    if auth_messages:
        print(f"   🚨 发现认证提示: {auth_messages}")
    
    # 检查页面错误
    error_indicators = ["error", "404", "not found", "access denied", "forbidden"]
    errors = []
    for error in error_indicators:
        if error in body_text.lower():
            count = body_text.lower().count(error)
            if count > 0:
                errors.append(f"{error}({count})")
    
    if errors:
        print(f"   ⚠️ 发现错误信息: {errors}")
    
    # 分析网络请求
    print("\n🌐 分析网络请求...")
    
    requests_log = []
    failures_log = []
    
    def log_request(request):
        requests_log.append({
            "url": request.url,
            "method": request.method,
            "resource_type": request.resource_type
        })
    
    def log_response(response):
        if response.status >= 400:
            failures_log.append({
                "url": response.url,
                "status": response.status,
                "status_text": response.status_text
            })
    
    page.on("request", log_request)
    page.on("response", log_response)
    
    # 重新加载页面以捕获请求
    page.reload(wait_until="networkidle")
    page.wait_for_timeout(3000)
    
    print(f"   总请求数: {len(requests_log)}")
    print(f"   失败请求数: {len(failures_log)}")
    
    if failures_log:
        print("   失败请求:")
        for failure in failures_log[:5]:  # 只显示前5个
            print(f"     {failure['status']} {failure['url']}")
    
    # 最后尝试查找CAD下载区域
    print("\n🎯 尝试定位CAD下载区域...")
    
    # 查找可能的CAD相关区域
    cad_sections = []
    
    # 方法1: 寻找包含CAD关键词的元素
    cad_elements = page.query_selector_all("*:has-text('CAD'), *:has-text('3D'), *:has-text('Download')")
    print(f"   CAD相关元素数量: {len(cad_elements)}")
    
    # 方法2: 寻找特定的类名或ID
    specific_selectors = [
        "[class*='cad']",
        "[class*='download']", 
        "[class*='model']",
        "[id*='cad']",
        "[id*='download']",
        "[id*='model']"
    ]
    
    for selector in specific_selectors:
        elements = page.query_selector_all(selector)
        if elements:
            print(f"   {selector}: {len(elements)} 个元素")
    
    return True

def diagnose_traceparts():
    """综合诊断TraceParts检测机制"""
    email = os.getenv("TRACEPARTS_EMAIL", "SearcherKerry36154@hotmail.com")
    password = os.getenv("TRACEPARTS_PASSWORD", "Vsn220mh@")
    
    print("🔬 TraceParts 检测机制综合诊断")
    print("=" * 60)
    print(f"账号: {email}")
    print(f"密码: {'*' * len(password)}")
    
    # 创建调试目录
    debug_dir = Path("results/detection_debug")
    debug_dir.mkdir(parents=True, exist_ok=True)
    
    with sync_playwright() as p:
        # 启动浏览器（非无头模式，便于观察）
        browser = p.chromium.launch(
            headless=False,
            slow_mo=500,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-features=VizDisplayCompositor',
                '--no-first-run',
                '--disable-default-apps',
                '--disable-popup-blocking',
                '--disable-translate',
                '--disable-background-timer-throttling',
                '--disable-renderer-backgrounding',
                '--disable-backgrounding-occluded-windows'
            ]
        )
        
        context = browser.new_context(
            viewport={'width': 1366, 'height': 768},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
        )
        
        page = context.new_page()
        
        # 应用stealth
        stealth_sync(page)
        
        # 应用额外的反检测脚本
        page.add_init_script("""
            // 删除webdriver属性
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
            
            // 伪造Chrome对象
            window.chrome = {
                runtime: {},
                loadTimes: function() {},
                csi: function() {},
                app: {}
            };
            
            // 伪造插件
            Object.defineProperty(navigator, 'plugins', {
                get: () => [
                    {name: "Chrome PDF Plugin", filename: "internal-pdf-viewer"},
                    {name: "Chrome PDF Viewer", filename: "mhjfbmdgcfjbbpaeojofohoefgiehjai"},
                    {name: "Native Client", filename: "internal-nacl-plugin"}
                ],
            });
            
            // 删除自动化特征
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise; 
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
        """)
        
        try:
            # 第一步：基础检测信号分析
            page.goto("https://httpbin.org/headers")
            detection_signals = analyze_page_detection_signals(page)
            
            # 第二步：网络指纹检查
            check_network_fingerprinting(page)
            
            # 第三步：TraceParts登录流程分析
            external_scripts, security_scripts = analyze_traceparts_login_flow(page)
            
            # 第四步：产品页面CAD加载测试
            success = test_product_page_cad_loading(page, email, password)
            
            # 生成诊断报告
            report = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "detection_signals": detection_signals,
                "external_scripts": external_scripts,
                "security_scripts": security_scripts,
                "login_success": success,
                "recommendations": []
            }
            
            # 生成建议
            if detection_signals.get("navigator.webdriver") != "undefined":
                report["recommendations"].append("webdriver属性未正确隐藏")
            
            if not detection_signals.get("window.chrome"):
                report["recommendations"].append("Chrome对象缺失")
            
            if len(security_scripts) > 0:
                report["recommendations"].append(f"检测到 {len(security_scripts)} 个安全脚本")
            
            if not success:
                report["recommendations"].append("产品页面访问失败，可能存在额外验证")
            
            # 保存报告
            report_file = debug_dir / f"diagnosis_report_{int(time.time())}.json"
            with open(report_file, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            print(f"\n📊 诊断报告已保存: {report_file}")
            
            # 输出建议
            if report["recommendations"]:
                print("\n💡 发现的问题:")
                for i, rec in enumerate(report["recommendations"], 1):
                    print(f"   {i}. {rec}")
            else:
                print("\n✅ 未发现明显检测问题")
            
            # 最终截图
            final_screenshot = debug_dir / f"final_state_{int(time.time())}.png"
            page.screenshot(path=str(final_screenshot), full_page=True)
            print(f"📸 最终状态截图: {final_screenshot}")
            
        except Exception as e:
            print(f"❌ 诊断过程出错: {e}")
        
        print("\n🎯 诊断完成！保持浏览器开启进行手动检查...")
        input("按回车键关闭...")
        
        browser.close()

if __name__ == "__main__":
    diagnose_traceparts() 