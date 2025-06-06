#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用 Playwright 的叶节点检测器，保持与 test-08 一致的方法
下载完整的 HTML 并进行分析
"""

import os
import sys
import re
import json
import time
import logging
from pathlib import Path
import importlib.util
from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
LOG = logging.getLogger("playwright-leaf-checker")

# 环境变量控制
SKIP_LOGIN = os.getenv("TRACEPARTS_SKIP_LOGIN", "1") == "1"  # 默认跳过登录
HEADLESS_MODE = True
DEBUG_MODE = True

# 登录账号
EMAIL = os.getenv("TRACEPARTS_EMAIL", "SearcherKerry36154@hotmail.com")
PASSWORD = os.getenv("TRACEPARTS_PASSWORD", "Vsn220mh@")

# 动态加载 stealth11i 模块
BASE_DIR = Path(__file__).parent.parent
path_to_11i = BASE_DIR / "test" / "legacy" / "11i-stealth_cad_downloader.py"
if not path_to_11i.exists():
    LOG.error(f"❌ Critical: 11i-stealth_cad_downloader.py not found at expected location: {path_to_11i}")
    sys.exit(1)

MOD11 = importlib.util.spec_from_file_location("stealth11i", path_to_11i)
stealth11i = importlib.util.module_from_spec(MOD11)
MOD11.loader.exec_module(stealth11i)


def append_page_size(url: str, size: int = 500) -> str:
    """若 URL 中未包含 PageSize 参数，则补充一个较大的值，减少分页次数。"""
    if 'PageSize=' in url:
        return url
    # 尝试更大的PageSize和其他可能的参数
    params = f"PageSize={size}&ShowAll=true&IncludeVariants=true"
    if '?' in url:
        return f"{url}&{params}"
    else:
        return f"{url}?{params}"


def detect_leaf_node_and_target_count(page) -> tuple:
    """检测是否为叶节点并获取目标产品总数 - 与 test-08 相同的逻辑（简化为数字+results模式）"""
    try:
        # 获取页面文本内容
        page_text = page.text_content("body")
        
        # 使用正则表达式检测"数字+results"模式
        # 支持逗号分隔的数字和不间断空格(\u00a0)
        results_pattern = r'\b[\d,]+(?:\s|\u00a0)+results?\b'
        has_number_results = bool(re.search(results_pattern, page_text, re.IGNORECASE))
        
        LOG.info(f"🔍 叶节点检测: 数字+results模式={'✅' if has_number_results else '❌'}")
        
        if has_number_results:
            LOG.info("✅ 确认这是一个叶节点页面（基于数字+results模式）")
            
            # 尝试提取目标产品总数
            target_count = extract_target_product_count(page)
            return True, target_count
        else:
            LOG.warning("⚠️ 这可能不是叶节点页面（未检测到数字+results模式）")
            return False, 0
            
    except Exception as e:
        LOG.warning(f"⚠️ 叶节点检测失败: {e}")
        return False, 0


def extract_target_product_count(page) -> int:
    """从页面提取目标产品总数 - 与 test-08 相同的逻辑"""
    try:
        # 常见的产品数量显示模式，支持逗号分隔符
        count_patterns = [
            r"([\d,]+)\s*results?",
            r"([\d,]+)\s*products?", 
            r"([\d,]+)\s*items?",
            r"showing\s*[\d,]+\s*[-–]\s*[\d,]+\s*of\s*([\d,]+)",
            r"([\d,]+)\s*total",
            r"found\s*([\d,]+)"
        ]
        
        # 获取页面全部文本内容
        page_text = page.text_content("body").lower()
        
        LOG.info(f"🔍 搜索产品数量模式...")
        
        # 尝试匹配各种模式
        for pattern in count_patterns:
            if DEBUG_MODE:
                LOG.info(f"  📄 尝试模式: {pattern}")
            matches = re.findall(pattern, page_text, re.IGNORECASE)
            if matches:
                if DEBUG_MODE:
                    LOG.info(f"    🎉 模式 {pattern} 匹配到: {matches}")
                for match_item in matches:
                    try:
                        # re.findall 返回的是元组列表，即使只有一个捕获组
                        # 如果是元组，取第一个元素；否则，直接使用
                        actual_match_str = match_item if isinstance(match_item, str) else match_item[0]
                        
                        # 移除逗号后转换为整数
                        count_str = actual_match_str.replace(',', '')
                        if not count_str.isdigit(): # 确保是纯数字
                            LOG.warning(f"      ⚠️ 非数字内容: '{count_str}' (来自: '{actual_match_str}')")
                            continue
                        count = int(count_str)
                        
                        # 更新产品数量范围的下限为1，因为我们关心的是>0
                        if 1 <= count <= 50000:  # 合理的产品数量范围
                            LOG.info(f"🎯 发现目标产品总数: {count} (来自模式: '{pattern}', 原文: '{actual_match_str}')")
                            return count
                        else:
                            if DEBUG_MODE:
                                LOG.info(f"      🔶 数量 {count} 不在有效范围 [1, 50000] (来自: '{actual_match_str}')")
                    except (ValueError, IndexError) as e_inner:
                        LOG.warning(f"      ⚠️ 处理匹配项 '{match_item}' 时出错: {e_inner}")
                        continue
            else:
                if DEBUG_MODE:
                    LOG.info(f"    ❌ 模式 {pattern} 未匹配到任何内容")
        
        LOG.info("⚠️ 未能提取到目标产品总数")
        return 0
        
    except Exception as e:
        LOG.warning(f"⚠️ 提取目标产品总数失败: {e}")
        return 0


def check_page_with_playwright(url: str, save_html: bool = True):
    """使用 Playwright 检查页面，与 test-08 保持一致的方法"""
    
    with sync_playwright() as p:
        # 创建stealth浏览器
        headless_status = "无头模式" if HEADLESS_MODE else "有头模式"
        LOG.info(f"🖥️ 启动浏览器 ({headless_status})")
        browser, ctx, page = stealth11i.create_stealth_browser(p, headless=HEADLESS_MODE)
        
        try:
            # 登录流程（可选）
            if not SKIP_LOGIN:
                LOG.info("🔐 开始stealth登录流程...")
                if stealth11i.stealth_login(page, EMAIL, PASSWORD):
                    LOG.info("✅ 登录成功！")
                else:
                    LOG.warning("⚠️ 登录失败，但继续尝试抓取...")
            else:
                LOG.info("⏭️ 跳过登录流程")
            
            # 增强URL - 与 test-08 相同
            enhanced_url = append_page_size(url, 500)
            LOG.info(f"🌐 访问增强URL: {enhanced_url}")
            
            # 访问页面并等待网络空闲 - 与 test-08 相同
            page.goto(enhanced_url)
            page.wait_for_load_state("networkidle")
            time.sleep(5)  # 等待页面加载
            
            # 检测叶节点 - 与 test-08 相同的逻辑
            is_leaf, target_count = detect_leaf_node_and_target_count(page)
            
            # 统计产品链接数量 - 与 test-08 相同
            product_elements = page.query_selector_all("a[href*='&Product=']")
            product_count = len(product_elements)
            
            LOG.info(f"📊 产品链接数量: {product_count}")
            
            # 保存HTML用于分析
            if save_html:
                html_content = page.content()
                body_text = page.text_content("body")
                
                # 创建输出目录
                os.makedirs("debug_html", exist_ok=True)
                
                # 生成文件名
                from urllib.parse import urlparse
                parsed = urlparse(url)
                catalog_path = ""
                if 'CatalogPath=' in url:
                    catalog_path = url.split('CatalogPath=')[1].split('&')[0]
                    catalog_path = catalog_path.replace('TRACEPARTS%3A', '').replace('%3A', '_')
                
                filename_base = f"debug_html/page_{catalog_path}" if catalog_path else "debug_html/page_unknown"
                
                # 保存完整HTML
                with open(f"{filename_base}_full.html", 'w', encoding='utf-8') as f:
                    f.write(html_content)
                
                # 保存纯文本
                with open(f"{filename_base}_text.txt", 'w', encoding='utf-8') as f:
                    f.write(body_text)
                
                # 保存分析结果
                results_pattern = r'\b[\d,]+(?:\s|\u00a0)+results?\b'
                has_number_results = bool(re.search(results_pattern, body_text, re.IGNORECASE))
                
                analysis = {
                    "url": url,
                    "enhanced_url": enhanced_url,
                    "is_leaf": is_leaf,
                    "target_count": target_count,
                    "product_count": product_count,
                    "has_number_results_pattern": has_number_results,
                    "body_text_length": len(body_text),
                    "html_length": len(html_content)
                }
                
                with open(f"{filename_base}_analysis.json", 'w', encoding='utf-8') as f:
                    json.dump(analysis, f, ensure_ascii=False, indent=2)
                
                LOG.info(f"📁 HTML已保存到: {filename_base}_full.html")
                LOG.info(f"📁 文本已保存到: {filename_base}_text.txt")
                LOG.info(f"📁 分析已保存到: {filename_base}_analysis.json")
            
            # 输出结果
            result_status = "✅" if is_leaf else "❌"
            LOG.info(f"{result_status} 叶节点: {is_leaf} | 目标数量: {target_count} | 产品链接: {product_count}")
            
            return {
                "is_leaf": is_leaf,
                "target_count": target_count,
                "product_count": product_count,
                "url": url,
                "enhanced_url": enhanced_url
            }
            
        finally:
            browser.close()


def main():
    if len(sys.argv) < 2:
        print("用法: python scripts/playwright_leaf_checker.py <URL>")
        print("示例: python scripts/playwright_leaf_checker.py 'https://www.traceparts.cn/en/search/...'")
        sys.exit(1)
    
    url = sys.argv[1]
    result = check_page_with_playwright(url, save_html=True)
    
    # 输出总结
    print(f"\n{'='*60}")
    print(f"📊 检测结果总结:")
    print(f"🌐 URL: {result['url']}")
    print(f"{'✅' if result['is_leaf'] else '❌'} 叶节点: {result['is_leaf']}")
    print(f"🎯 目标数量: {result['target_count']}")
    print(f"🔗 产品链接: {result['product_count']}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main() 