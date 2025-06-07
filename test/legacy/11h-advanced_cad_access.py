#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 11h —— 高级CAD访问分析
专门分析为什么自动化访问失败而手动操作成功的技术原因
"""

from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync
import time
import os
import json
import re
from pathlib import Path

def capture_real_user_behavior():
    """捕获真实用户行为模式"""
    print("👤 启动真实用户行为捕获模式...")
    print("请手动完成以下操作，程序将记录所有网络请求和页面变化：")
    print("1. 登录TraceParts")
    print("2. 访问产品页面") 
    print("3. 找到CAD下载区域")
    print("4. 尝试下载CAD文件")
    
    email = os.getenv("TRACEPARTS_EMAIL", "SearcherKerry36154@hotmail.com")
    password = os.getenv("TRACEPARTS_PASSWORD", "Vsn220mh@")
    
    debug_dir = Path("results/behavior_analysis")
    debug_dir.mkdir(parents=True, exist_ok=True)
    
    # 记录所有网络活动
    network_log = []
    dom_changes = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            slow_mo=100,
            args=['--disable-blink-features=AutomationControlled']
        )
        
        context = browser.new_context(
            viewport={'width': 1366, 'height': 768},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
        )
        
        page = context.new_page()
        stealth_sync(page)
        
        # 网络请求监控
        def log_request(request):
            network_log.append({
                "timestamp": time.time(),
                "type": "request",
                "method": request.method,
                "url": request.url,
                "headers": dict(request.headers),
                "resource_type": request.resource_type
            })
        
        def log_response(response):
            network_log.append({
                "timestamp": time.time(),
                "type": "response", 
                "status": response.status,
                "url": response.url,
                "headers": dict(response.headers)
            })
        
        page.on("request", log_request)
        page.on("response", log_response)
        
        # DOM变化监控
        page.add_init_script("""
            const observer = new MutationObserver((mutations) => {
                mutations.forEach((mutation) => {
                    if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                        mutation.addedNodes.forEach((node) => {
                            if (node.nodeType === Node.ELEMENT_NODE) {
                                const tagName = node.tagName?.toLowerCase();
                                if (tagName && ['select', 'option', 'button', 'a', 'form'].includes(tagName)) {
                                    console.log('DOM_CHANGE:', {
                                        action: 'added',
                                        tag: tagName,
                                        id: node.id,
                                        class: node.className,
                                        text: node.textContent?.slice(0, 100)
                                    });
                                }
                            }
                        });
                    }
                });
            });
            observer.observe(document.body, { childList: true, subtree: true });
        """)
        
        # 监听控制台消息
        page.on("console", lambda msg: dom_changes.append({
            "timestamp": time.time(),
            "type": msg.type,
            "text": msg.text
        }))
        
        # 开始捕获
        print("\n🌐 打开登录页面...")
        page.goto("https://www.traceparts.cn/en/sign-in")
        
        print(f"\n📧 自动填写账号信息：{email}")
        print("⏳ 等待您手动完成登录和CAD访问操作...")
        print("完成后按回车键继续分析...")
        
        # 自动填写账号信息
        try:
            email_input = page.locator("input[type='email']")
            if email_input.is_visible():
                email_input.fill(email)
                
            pwd_input = page.locator("input[type='password']")  
            if pwd_input.is_visible():
                pwd_input.fill(password)
        except:
            pass
        
        # 等待用户完成手动操作
        input()
        
        print("\n📊 分析捕获的数据...")
        
        # 保存网络日志
        network_file = debug_dir / f"network_log_{int(time.time())}.json"
        with open(network_file, "w", encoding="utf-8") as f:
            json.dump(network_log, f, ensure_ascii=False, indent=2)
        
        # 保存DOM变化日志
        dom_file = debug_dir / f"dom_changes_{int(time.time())}.json"
        with open(dom_file, "w", encoding="utf-8") as f:
            json.dump(dom_changes, f, ensure_ascii=False, indent=2)
        
        print(f"📁 网络日志保存至: {network_file}")
        print(f"📁 DOM变化日志保存至: {dom_file}")
        
        # 分析关键请求
        analyze_network_patterns(network_log)
        
        browser.close()
        
        return network_log, dom_changes

def analyze_network_patterns(network_log):
    """分析网络请求模式"""
    print("\n🔍 分析网络请求模式...")
    
    # 按类型分组
    requests_by_type = {}
    for entry in network_log:
        if entry["type"] == "request":
            resource_type = entry.get("resource_type", "unknown")
            if resource_type not in requests_by_type:
                requests_by_type[resource_type] = []
            requests_by_type[resource_type].append(entry)
    
    print("请求类型分布:")
    for res_type, requests in requests_by_type.items():
        print(f"  {res_type}: {len(requests)} 个")
    
    # 查找CAD相关请求
    cad_requests = []
    cad_keywords = ["cad", "download", "model", "stl", "step", "iges", "3d"]
    
    for entry in network_log:
        if entry["type"] == "request":
            url = entry["url"].lower()
            if any(keyword in url for keyword in cad_keywords):
                cad_requests.append(entry)
    
    if cad_requests:
        print(f"\n🎯 发现 {len(cad_requests)} 个CAD相关请求:")
        for req in cad_requests:
            print(f"  {req['method']} {req['url']}")
    else:
        print("\n⚠️ 未发现CAD相关请求")
    
    # 查找登录相关请求
    auth_requests = []
    auth_keywords = ["sign-in", "login", "auth", "session", "cookie"]
    
    for entry in network_log:
        if entry["type"] == "request":
            url = entry["url"].lower()
            if any(keyword in url for keyword in auth_keywords):
                auth_requests.append(entry)
    
    if auth_requests:
        print(f"\n🔐 发现 {len(auth_requests)} 个认证相关请求:")
        for req in auth_requests[:5]:  # 只显示前5个
            print(f"  {req['method']} {req['url']}")

def simulate_captured_behavior(network_log):
    """模拟捕获的用户行为"""
    print("\n🤖 尝试模拟捕获的真实用户行为...")
    
    # 分析时间间隔
    timestamps = [entry["timestamp"] for entry in network_log if entry["type"] == "request"]
    if len(timestamps) > 1:
        intervals = [timestamps[i+1] - timestamps[i] for i in range(len(timestamps)-1)]
        avg_interval = sum(intervals) / len(intervals)
        print(f"平均请求间隔: {avg_interval:.2f} 秒")
    
    # 分析请求序列
    request_sequence = []
    for entry in network_log:
        if entry["type"] == "request":
            request_sequence.append({
                "url": entry["url"],
                "method": entry["method"],
                "delay": 0  # 计算延迟
            })
    
    # 用模拟的行为重新尝试访问
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=500)
        context = browser.new_context()
        page = context.new_page()
        stealth_sync(page)
        
        try:
            print("🎬 开始模拟行为序列...")
            
            # 复制重要的请求头
            important_headers = {}
            for entry in network_log:
                if entry["type"] == "request" and "traceparts" in entry["url"]:
                    headers = entry.get("headers", {})
                    if "authorization" in headers:
                        important_headers["authorization"] = headers["authorization"]
                    if "x-requested-with" in headers:
                        important_headers["x-requested-with"] = headers["x-requested-with"]
            
            if important_headers:
                print(f"发现重要请求头: {list(important_headers.keys())}")
                page.set_extra_http_headers(important_headers)
            
            # 按序列访问页面
            visited_urls = set()
            for req in request_sequence[:10]:  # 只模拟前10个请求
                url = req["url"]
                if url.startswith("https://www.traceparts") and url not in visited_urls:
                    print(f"访问: {url}")
                    try:
                        page.goto(url, wait_until="networkidle", timeout=30000)
                        visited_urls.add(url)
                        time.sleep(2)  # 模拟真实停留时间
                    except:
                        print(f"访问失败: {url}")
            
        except Exception as e:
            print(f"模拟失败: {e}")
        
        print("🎯 模拟完成，请检查浏览器中的结果...")
        input("按回车键关闭...")
        browser.close()

def compare_automation_vs_manual():
    """对比自动化和手动操作的差异"""
    print("\n⚖️ 对比自动化操作和手动操作的差异...")
    
    # 先运行标准自动化流程
    print("1️⃣ 运行标准自动化流程...")
    automation_log = run_standard_automation()
    
    print("\n2️⃣ 运行真实用户行为捕获...")
    manual_log, dom_log = capture_real_user_behavior()
    
    print("\n3️⃣ 对比分析...")
    
    # 对比请求头差异
    auto_headers = extract_common_headers(automation_log)
    manual_headers = extract_common_headers(manual_log)
    
    print("请求头差异分析:")
    for header in set(auto_headers.keys()) | set(manual_headers.keys()):
        auto_val = auto_headers.get(header, "缺失")
        manual_val = manual_headers.get(header, "缺失")
        if auto_val != manual_val:
            print(f"  {header}:")
            print(f"    自动化: {auto_val}")
            print(f"    手动: {manual_val}")
    
    # 对比请求时序
    auto_timing = analyze_request_timing(automation_log)
    manual_timing = analyze_request_timing(manual_log)
    
    print(f"\n请求时序差异:")
    print(f"  自动化平均间隔: {auto_timing:.2f}秒")
    print(f"  手动操作平均间隔: {manual_timing:.2f}秒")

def run_standard_automation():
    """运行标准的自动化流程"""
    network_log = []
    
    email = os.getenv("TRACEPARTS_EMAIL", "SearcherKerry36154@hotmail.com")
    password = os.getenv("TRACEPARTS_PASSWORD", "Vsn220mh@")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        stealth_sync(page)
        
        def log_request(request):
            network_log.append({
                "timestamp": time.time(),
                "type": "request",
                "method": request.method,
                "url": request.url,
                "headers": dict(request.headers),
                "resource_type": request.resource_type
            })
        
        page.on("request", log_request)
        
        try:
            # 标准登录流程
            page.goto("https://www.traceparts.cn/en/sign-in")
            page.fill("input[type='email']", email)
            page.fill("input[type='password']", password)
            page.click("button:has-text('Sign in')")
            page.wait_for_timeout(3000)
            
            # 访问产品页面
            product_url = "https://www.traceparts.cn/en/product/rs-pro-abs-plastic-sheet-stock1220x610x15mm?CatalogPath=TRACEPARTS%3ATP05009&Product=90-03062024-057087"
            page.goto(product_url)
            page.wait_for_timeout(5000)
            
        except Exception as e:
            print(f"自动化流程错误: {e}")
        
        browser.close()
    
    return network_log

def extract_common_headers(network_log):
    """提取常见请求头"""
    headers = {}
    for entry in network_log:
        if entry["type"] == "request" and "traceparts" in entry["url"]:
            req_headers = entry.get("headers", {})
            for key, value in req_headers.items():
                if key.lower() in ["user-agent", "accept", "accept-language", "referer", "cookie"]:
                    headers[key] = value
            break  # 只需要第一个TraceParts请求的头信息
    return headers

def analyze_request_timing(network_log):
    """分析请求时序"""
    timestamps = [entry["timestamp"] for entry in network_log if entry["type"] == "request"]
    if len(timestamps) > 1:
        intervals = [timestamps[i+1] - timestamps[i] for i in range(len(timestamps)-1)]
        return sum(intervals) / len(intervals)
    return 0

if __name__ == "__main__":
    print("🔬 TraceParts CAD访问高级分析")
    print("=" * 60)
    
    print("选择分析模式:")
    print("1. 捕获真实用户行为")
    print("2. 模拟捕获的行为")
    print("3. 对比自动化vs手动操作")
    
    choice = input("请选择 (1-3): ").strip()
    
    if choice == "1":
        capture_real_user_behavior()
    elif choice == "2":
        # 需要先有捕获的日志文件
        log_files = list(Path("results/behavior_analysis").glob("network_log_*.json"))
        if log_files:
            latest_log = max(log_files, key=lambda x: x.stat().st_mtime)
            with open(latest_log) as f:
                network_log = json.load(f)
            simulate_captured_behavior(network_log)
        else:
            print("❌ 未找到捕获的行为日志，请先运行模式1")
    elif choice == "3":
        compare_automation_vs_manual()
    else:
        print("❌ 无效选择") 