#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 08  —— 针对 TraceParts 某个最末层（leaf）分类页面，收集该分类下所有产品详情页链接。
使用 Playwright + stealth 登录，完全类似 test-10 的实现方式。

示例入口（leaf）URL：
https://www.traceparts.cn/en/search/traceparts-classification-mechanical-components-bearings-bearing-blocks-cartridge-blocks?CatalogPath=TRACEPARTS%3ATP01002002006

目标：获取所有形如
https://www.traceparts.cn/en/product/...?...&Product=90-31032023-039178
的链接，并保存到 results/product_links_<TP code>.json

使用方法：
$ python test/08-test_leaf_product_links.py <leaf_url>
若不提供参数，则脚本默认使用上面示例。
"""

import os
import re
import sys
import json
import time
import random
import logging
from urllib.parse import urlparse, parse_qs
from pathlib import Path
import importlib.util

# Playwright
from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
LOG = logging.getLogger("test-08")

# 调试开关
DEBUG_MODE = True
# 可通过环境变量 TRACEPARTS_SKIP_LOGIN=1 来跳过登录
SKIP_LOGIN = os.getenv("TRACEPARTS_SKIP_LOGIN", "0") == "1"  # True 跳过登录
HEADLESS_MODE = True  # 设置为False使用有头模式调试

# 登录账号
EMAIL = os.getenv("TRACEPARTS_EMAIL", "SearcherKerry36154@hotmail.com")
PASSWORD = os.getenv("TRACEPARTS_PASSWORD", "Vsn220mh@")

# --------- 动态加载 stealth11i 模块 ---------
BASE_DIR = Path(__file__).parent
path_to_11i = BASE_DIR / "legacy" / "11i-stealth_cad_downloader.py"
if not path_to_11i.exists():
    LOG.error(f"❌ Critical: 11i-stealth_cad_downloader.py not found at expected location: {path_to_11i}")
    sys.exit(1)

MOD11 = importlib.util.spec_from_file_location("stealth11i", path_to_11i)
stealth11i = importlib.util.module_from_spec(MOD11)  # type: ignore
MOD11.loader.exec_module(stealth11i)  # type: ignore


PRODUCT_LINK_PATTERN = re.compile(r"[?&]Product=([0-9\-]+)")

def human_like_delay(min_delay=0.5, max_delay=2.0):
    """人类行为延迟"""
    delay = random.uniform(min_delay, max_delay)
    time.sleep(delay)

def scroll_full(page, current_products: int = 0, target_count: int = 0):
    """逐步滚动到页面底部，带随机人类行为"""
    if DEBUG_MODE:
        LOG.info("📜 开始随机化滚动...")
    
    # 获取初始滚动高度
    last_height = page.evaluate("document.body.scrollHeight")
    
    # 随机选择滚动步数 (4-7步)
    scroll_steps = random.randint(4, 7)
    if DEBUG_MODE:
        LOG.info(f"  📜 随机选择 {scroll_steps} 步滚动")
    
    # 分步滚动，每次滚动一定比例
    for step in range(scroll_steps):
        # 滚动到当前的 (step+1)/scroll_steps 位置
        position = last_height * (step + 1) / scroll_steps
        page.evaluate(f"window.scrollTo(0, {position});")
        if DEBUG_MODE:
            LOG.info(f"  📜 滚动步骤 {step + 1}/{scroll_steps}")
        
        # 根据进度调整等待时间 - 前期更快
        current_progress = (current_products / target_count * 100) if target_count > 0 else 50
        if current_progress < 80:
            wait_time = random.uniform(0.3, 0.8)  # 80%前更快
        else:
            wait_time = random.uniform(0.5, 1.2)  # 80%后正常速度
        time.sleep(wait_time)
        
        # 随机添加人类行为：有30%概率稍微往回滚
        if random.random() < 0.3:
            back_scroll = random.randint(20, 100)
            page.evaluate(f"window.scrollBy(0, -{back_scroll});")
            if DEBUG_MODE:
                LOG.info(f"  🔙 随机回滚 {back_scroll}px")
            time.sleep(random.uniform(0.3, 0.8))
            page.evaluate(f"window.scrollBy(0, {back_scroll + 20});")
    
    # 最后确保滚动到绝对底部
    page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
    final_wait = random.uniform(0.8, 1.5)  # 减少最终等待
    time.sleep(final_wait)
    if DEBUG_MODE:
        LOG.info(f"📜 滚动完成，最终等待 {final_wait:.1f}s")


def detect_leaf_node_and_target_count(page) -> tuple:
    """检测是否为叶节点并获取目标产品总数"""
    try:
        # 获取页面文本内容
        page_text = page.text_content("body")
        
        # 使用正则表达式检测"数字+results"模式
        # 支持逗号分隔的数字和不间断空格(\u00a0)
        import re
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
    """从页面提取目标产品总数"""
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


def monitor_progress(current_count: int, target_count: int, round_name: str = ""):
    """监控抓取进度"""
    if target_count > 0:
        progress = (current_count / target_count) * 100
        remaining = target_count - current_count
        LOG.info(f"📈 {round_name}进度: {current_count}/{target_count} ({progress:.1f}%), 还需抓取: {remaining}")
    else:
        LOG.info(f"📊 {round_name}当前数量: {current_count}")


def extract_products_on_page(page, seen: set) -> list:
    """提取当前页面所有含 &Product= 的 a 标签链接，去重"""
    elements = page.query_selector_all("a[href*='&Product=']")
    links = []
    for el in elements:
        href = el.get_attribute('href') or ""
        if not href or href in seen:
            continue
        if '&Product=' not in href:
            continue
        parsed = urlparse(href)
        if '/product/' not in parsed.path:
            continue  # 过滤广告或其他链接
        seen.add(href)
        links.append(href)
    return links


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


def click_show_more_if_any(page, target_count: int = 0) -> bool:
    """若页面存在 'Show more results' 按钮，则点击并返回 True；否则 False。"""
    try:
        # 先检查页面上所有的按钮
        all_buttons = page.query_selector_all("button")
        if DEBUG_MODE:
            LOG.info(f"🔍 页面共有 {len(all_buttons)} 个按钮")
        
        # 查找包含show more的按钮
        show_more_buttons = []
        for i, btn in enumerate(all_buttons):
            try:
                btn_text = (btn.text_content() or "").lower()
                if DEBUG_MODE and btn_text:  # 只在调试模式显示所有按钮文本
                    pass  # Add pass to make the if statement syntactically correct
                if 'show' in btn_text and 'more' in btn_text:
                    show_more_buttons.append((i, btn, btn_text))
                    LOG.info(f"🎯 找到Show More按钮 {i}: '{btn_text}' (visible: {btn.is_visible()}, enabled: {btn.is_enabled()})")
            except Exception:
                continue
        
        LOG.info(f"🎯 总共找到 {len(show_more_buttons)} 个Show More按钮")
        
        # 尝试多种Show More按钮查找策略
        btn = None
        selectors = [
            "button:has-text('Show more')",
            "button:has-text('Show More')", 
            "button:has-text('Load more')",
            "button:has-text('More results')",
            "a:has-text('Show more')",
            ".show-more, .load-more",
            "button[class*='show-more'], button[class*='load-more']"
        ]
        
        for selector in selectors:
            try:
                btn = page.query_selector(selector)
                if btn and btn.is_visible() and btn.is_enabled():
                    LOG.info(f"✅ 使用选择器找到按钮: {selector}")
                    break
            except Exception:
                continue
        
        if not btn:
            LOG.info("❌ 所有选择器都未找到Show More按钮")
            return False
        if btn and btn.is_visible() and btn.is_enabled():
            LOG.info(f"👆 找到可点击的Show More按钮: '{btn.text_content()}'")
            btn.scroll_into_view_if_needed()
            time.sleep(1)
            
            try:
                # 先尝试普通点击
                btn.click()
                LOG.info("✅ 普通点击成功")
            except Exception:
                LOG.info("⚠️ 普通点击失败，尝试JavaScript点击")
                # 使用JavaScript点击
                page.evaluate("arguments[0].click();", btn)
                LOG.info("✅ JavaScript点击成功")
            
            # 根据进度调整点击后的等待时间
            current_after_click = len(page.query_selector_all("a[href*='&Product=']"))
            progress_after_click = (current_after_click / target_count * 100) if target_count > 0 else 50
            
            if progress_after_click < 80:
                post_click_wait = random.uniform(0.2, 0.5)  # 80%前更快
                up_scroll_prob = 0.3  # 降低概率
                final_wait = random.uniform(0.4, 0.8)
            else:
                post_click_wait = random.uniform(0.4, 0.8)  # 80%后正常
                up_scroll_prob = 0.5
                final_wait = random.uniform(0.8, 1.5)
                
            time.sleep(post_click_wait)
            
            # 点击后人类通常会随机查看新内容
            if random.random() < up_scroll_prob:
                up_scroll = random.randint(80, 150)
                page.evaluate(f"window.scrollBy(0, -{up_scroll});")
                if DEBUG_MODE:
                    LOG.info(f"  👀 随机上滚查看 {up_scroll}px")
                time.sleep(random.uniform(0.1, 0.3))
            
            # 再滚到底部，随机等待
            page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(final_wait)
            return True
        else:
            LOG.info("❌ Show More按钮不可点击")
    except Exception as e:
        LOG.warning(f"⚠️ 点击Show More按钮出错: {e}")
        time.sleep(1)
    return False


def load_all_results(page, target_count: int = 0):
    """持续滚动并点击 'Show more results'，直到全部产品都加载完。"""
    # click_count is the general iteration counter for the main loop
    click_count = 0 
    # max_clicks is the overall safety limit for iterations of the main loop
    max_clicks = 100 
    
    # Counts consecutive rounds where product numbers didn't change after a click, 
    # or when no click could be made.
    no_change_rounds = 0
    
    # Counts consecutive failed attempts to find/click the "Show More" button.
    consecutive_click_failures = 0
    MAX_CONSECUTIVE_CLICK_FAILURES = 3

    # 根据是否有目标数量调整无变化容忍度
    if target_count > 0:
        max_no_change = 5   # 有目标时更宽容，因为我们用进度控制
    else:
        max_no_change = 3   # 无目标时严格一些
    
    # Corrected while loop condition using parentheses for implicit line continuation
    while (click_count < max_clicks and
           no_change_rounds < max_no_change and
           consecutive_click_failures < MAX_CONSECUTIVE_CLICK_FAILURES):
        
        LOG.info(f"🚀 第 {click_count + 1}/{max_clicks} 轮加载更多结果 (无产品变化轮次: {no_change_rounds}/{max_no_change}, 连续点击失败: {consecutive_click_failures}/{MAX_CONSECUTIVE_CLICK_FAILURES})...")
        
        current_products = len(page.query_selector_all("a[href*='&Product=']"))
        monitor_progress(current_products, target_count, f"第{click_count + 1}轮开始前")
        
        # 智能停止逻辑 (based on target_count and progress)
        if target_count > 0:
            current_progress = (current_products / target_count) * 100
            if current_progress >= 100.0:
                LOG.info(f"🎯 进度已达 {current_progress:.1f}%，目标完成！(跳过最终确认)")
                return 
            elif current_progress >= 95.0 and no_change_rounds >= 2:
                LOG.info(f"🎯 进度已达 {current_progress:.1f}%，且连续 {no_change_rounds} 轮无变化，认为抓取完成 (主循环)")
                break 
            # Inner "fast retry" logic if progress < 95%
            elif current_progress < 95.0:
                LOG.info(f"🚀 当前进度 {current_progress:.1f}% < 95%，尝试快速点击/滚动...")
                time.sleep(random.uniform(1.0, 2.0))
                
                if click_show_more_if_any(page, target_count):
                    consecutive_click_failures = 0 # Reset on successful click attempt
                    click_count += 1 # Increment main loop/attempt counter
                    after_quick_click_products = len(page.query_selector_all("a[href*='&Product=']"))
                    if after_quick_click_products > current_products:
                        no_change_rounds = 0
                        LOG.info(f"⚡ 快速模式点击：产品数量增加 {current_products} → {after_quick_click_products}")
                    else:
                        no_change_rounds += 1
                        LOG.info(f"⚡ 快速模式点击：无增长，累计无产品变化轮次 {no_change_rounds}")
                    # Check target achievement immediately after a successful click
                    if target_count > 0 and after_quick_click_products >= target_count:
                        LOG.info(f"🎯 快速模式点击后已达目标产品数量: {after_quick_click_products}/{target_count} (跳过最终确认)")
                        return
                    continue # Continue to next iteration of the main while loop
                else: # click_show_more_if_any returned False in fast mode
                    consecutive_click_failures += 1
                    LOG.info(f"⚡ 快速模式：未找到Show More按钮 (连续点击失败: {consecutive_click_failures})，将滚动重试")
                    scroll_full(page, current_products, target_count)
                    # No click was made, so product count didn't change due to a click.
                    # This round effectively had no change in products due to a click.
                    no_change_rounds += 1 
                # If consecutive_click_failures reached limit here, the main while loop condition will catch it.
                click_count += 1 # Increment main loop/attempt counter even if click failed, as an attempt was made
                continue

        # Default behavior (not in <95% progress fast retry, or if target_count is 0)
        scroll_full(page, current_products, target_count)
        
        if click_show_more_if_any(page, target_count):
            consecutive_click_failures = 0 # Reset on successful click attempt
            # click_count is incremented at the end of the loop iteration
            
            after_click_products = len(page.query_selector_all("a[href*='&Product=']"))
            monitor_progress(after_click_products, target_count, f"第{click_count + 1}次(尝试)点击后")
            
            if after_click_products == current_products:
                no_change_rounds += 1
                LOG.warning(f"⚠️ 点击Show More后产品数量没有增加 (无产品变化轮次: {no_change_rounds}/{max_no_change})")
            else:
                no_change_rounds = 0  # Reset no_change_rounds for product count
                
            if target_count > 0 and after_click_products >= target_count:
                LOG.info(f"🎯 已达到目标产品数量: {after_click_products}/{target_count} (跳过最终确认)")
                return
        else: # click_show_more_if_any returned False
            consecutive_click_failures += 1
            no_change_rounds += 1 # No click, so no change in products from a click
            LOG.warning(f"⚠️ 未找到或未能点击Show More按钮 (连续点击失败: {consecutive_click_failures}/{MAX_CONSECUTIVE_CLICK_FAILURES}, 无产品变化轮次: {no_change_rounds})")

        click_count += 1 # Increment main loop iteration counter

    # Logging reasons for exiting the main while loop
    if click_count >= max_clicks:
        LOG.warning(f"⚠️ 主加载阶段因达到最大尝试次数 ({max_clicks}) 而停止")
    elif no_change_rounds >= max_no_change:
        LOG.info(f"✅ 主加载阶段因连续 {max_no_change} 轮无产品数量变化而停止")
    elif consecutive_click_failures >= MAX_CONSECUTIVE_CLICK_FAILURES:
        LOG.warning(f"⚠️ 主加载阶段因连续 {MAX_CONSECUTIVE_CLICK_FAILURES} 次未能点击Show More按钮而停止")
        
    # 最后的彻底确认滚动
    LOG.info("🔄 开始最终彻底确认阶段...")
    final_scroll_rounds = 5 
    consecutive_no_change_final = 0 # Renamed to avoid clash if this script was part of a class
    consecutive_no_button_final = 0 # Renamed

    for final_scroll_iter in range(final_scroll_rounds): # Renamed loop variable
        before_final = len(page.query_selector_all("a[href*='&Product=']"))
        LOG.info(f"📊 第 {final_scroll_iter + 1}/{final_scroll_rounds} 轮最终确认开始，当前产品数: {before_final}")
        
        scroll_full(page, before_final, target_count)
        time.sleep(2) 
        page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        
        LOG.info(f"  🔍 第 {final_scroll_iter + 1} 轮：检查是否还有Show More按钮...")
        button_was_clicked_this_round = click_show_more_if_any(page, target_count)
        
        if button_was_clicked_this_round:
            LOG.info(f"  🎯 第 {final_scroll_iter + 1} 轮：发现并点击了Show More按钮！继续检查...")
            time.sleep(3) 
            consecutive_no_change_final = 0 
            consecutive_no_button_final = 0 
        else:
            consecutive_no_button_final += 1
            LOG.info(f"  ❌ 第 {final_scroll_iter + 1} 轮：未找到/点击Show More按钮 (连续未找到: {consecutive_no_button_final})")
            if consecutive_no_button_final >= 3: # Threshold for consecutive no button
                LOG.info(f"🎯 连续 {consecutive_no_button_final} 轮未找到/点击Show More按钮，确认已到页面底部！")
                break
        
        after_final = len(page.query_selector_all("a[href*='&Product=']"))
        LOG.info(f"📊 第 {final_scroll_iter + 1} 轮最终确认结果: {before_final} → {after_final}")
        
        if after_final == before_final:
            consecutive_no_change_final += 1
            LOG.info(f"  ✅ 第 {final_scroll_iter + 1} 轮无新增产品 (连续无变化: {consecutive_no_change_final})")
            if consecutive_no_change_final >= 3: # Threshold for consecutive no new products
                LOG.info(f"🎯 连续 {consecutive_no_change_final} 轮最终确认无变化，确认抓取完成！")
                break
        else:
            consecutive_no_change_final = 0 
            LOG.info(f"  🆕 第 {final_scroll_iter + 1} 轮发现新产品: +{after_final - before_final}")
    
    final_count = len(page.query_selector_all("a[href*='&Product=']"))
    LOG.info(f"🏁 load_all_results完成，最终产品链接数: {final_count}")
    if target_count > 0:
        final_progress = (final_count / target_count) * 100
        LOG.info(f"📊 最终进度: {final_progress:.1f}% ({final_count}/{target_count})")


def collect_all_product_links(page, leaf_url: str) -> list:
    """主抓取函数：访问 leaf 页面，滚动+点击加载全部产品，并收集链接"""
    
    # 修改URL以支持更大的PageSize
    enhanced_url = append_page_size(leaf_url, 500)
    LOG.info(f"🌐 访问增强URL: {enhanced_url}")
    
    page.goto(enhanced_url)
    page.wait_for_load_state("networkidle")
    time.sleep(5)  # 等待页面加载
    
    # 检测是否为叶节点并获取目标数量
    is_leaf, target_count = detect_leaf_node_and_target_count(page)
    
    # 记录初始产品数量
    initial_elements = page.query_selector_all("a[href*='&Product=']")
    LOG.info(f"📊 页面初始加载的产品链接数: {len(initial_elements)}")
    
    # 如果不是叶节点且没有产品链接，直接退出
    if not is_leaf and len(initial_elements) == 0:
        LOG.error("❌ 检测到非叶节点页面且无产品链接，停止抓取")
        return [], {
            "extracted_count": 0,
            "target_count": 0,
            "progress_percentage": 0.0,
            "completion_status": "non_leaf_page",
            "error": "Page is not a leaf node with products"
        }
    
    if not is_leaf:
        LOG.warning("⚠️ 页面似乎不是叶节点，但发现产品链接，继续尝试抓取...")
    
    if target_count > 0:
        LOG.info(f"🎯 目标产品总数: {target_count}")
        expected_progress = (len(initial_elements) / target_count) * 100
        LOG.info(f"📈 初始进度: {expected_progress:.1f}%")
    
    # 加载所有结果
    load_all_results(page, target_count)
    
    # 收集所有链接
    seen = set()
    all_links = extract_products_on_page(page, seen)
    
    # 显示最终统计
    final_count = len(all_links)
    LOG.info(f"🎯 最终抓取结果: {final_count} 个产品链接")
    
    # 计算进度信息
    progress_info = {
        "extracted_count": final_count,
        "target_count": target_count,
        "progress_percentage": 0.0,
        "completion_status": "unknown"
    }
    
    if target_count > 0:
        final_progress = (final_count / target_count) * 100
        missing_count = target_count - final_count
        progress_info["progress_percentage"] = round(final_progress, 1)
        
        LOG.info(f"📊 完成度: {final_progress:.1f}% ({final_count}/{target_count})")
        if missing_count > 0:
            LOG.warning(f"⚠️ 可能遗漏: {missing_count} 个产品")
            progress_info["completion_status"] = "partial"
        else:
            LOG.info("✅ 已达到目标数量！")
            progress_info["completion_status"] = "complete"
    else:
        LOG.info("📊 未检测到目标数量，按实际抓取结果统计")
        progress_info["completion_status"] = "no_target"
    
    return all_links, progress_info


def tp_code_from_url(url: str) -> str:
    """从 leaf URL 提取 TP 编码，例 TP01002002006"""
    qs_part = urlparse(url).query
    params = parse_qs(qs_part)
    cp = params.get('CatalogPath', [''])[0]
    if cp.startswith('TRACEPARTS:'):
        cp = cp.split(':',1)[1]
    return cp


def main():
    # 读取命令行参数
    #leaf_url = sys.argv[1] if len(sys.argv) > 1 else "https://www.traceparts.cn/en/search/traceparts-classification-mechanical-components-bearings-bearing-blocks-flanged-block-bearings?CatalogPath=TRACEPARTS%3ATP01002002002"
    # 测试用例：使用带PageSize参数的bearing大类页面
    # 示例入口（leaf）URL：
    # https://www.traceparts.cn/en/search/traceparts-classification-mechanical-components-bearings-bearing-blocks-pillow-block-bearings-pillow-block-bearings-plain-bearings?CatalogPath=TRACEPARTS%3ATP01002002003003
    # 默认leaf_url为电机控制类目，如需测试其他类目可替换URL或通过命令行参数传入
    # 默认leaf_url为“Letters”类目，如需测试其他类目可替换URL或通过命令行参数传入
    leaf_url = sys.argv[1] if len(sys.argv) > 1 else "https://www.traceparts.cn/en/search/traceparts-classification-manufacturing-engineering-information-technology-software-and-general-drawings-for-software-symbols-computer-dummies-general-drawings-symbols-computer-dummies-graphical-symbols-letters?CatalogPath=TRACEPARTS%3ATP02003002001002002"

    tp_code = tp_code_from_url(leaf_url) or "UNKNOWN"

    with sync_playwright() as p:
        # 创建stealth浏览器
        headless_status = "无头模式" if HEADLESS_MODE else "有头模式"
        LOG.info(f"🖥️ 启动浏览器 ({headless_status})")
        browser, ctx, page = stealth11i.create_stealth_browser(p, headless=HEADLESS_MODE)
        
        try:
            # 首先进行登录（可选）
            if not SKIP_LOGIN:
                LOG.info("🔐 开始stealth登录流程...")
                if EMAIL == "SearcherKerry36154@hotmail.com" or PASSWORD == "Vsn220mh@":
                    LOG.info("✅ 使用预设凭据进行登录")
                
                if stealth11i.stealth_login(page, EMAIL, PASSWORD):
                    LOG.info("✅ 登录成功！")
                else:
                    LOG.warning("⚠️ 登录失败，但继续尝试抓取...")
            else:
                LOG.info("⏭️ 跳过登录流程")
            
            all_links, progress_info = collect_all_product_links(page, leaf_url)
            
            # 检查是否因为非叶节点页面而退出
            if progress_info.get("completion_status") == "non_leaf_page":
                LOG.error("❌ 因检测到非叶节点页面，程序终止")
                return False
            
            if not all_links:
                LOG.warning("未抓取到任何产品链接！")
            
            # 输出到文件，包含进度信息
            os.makedirs("results", exist_ok=True)
            out_file = f"results/product_links_{tp_code}.json"
            
            # 准备完整的数据结构
            output_data = {
                "leaf_url": leaf_url,
                "tp_code": tp_code,
                "total": len(all_links),
                "progress": progress_info,
                "extraction_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "links": all_links
            }
            
            with open(out_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
            
            # 更详细的完成日志
            completion_msg = f"✅ 共抓取 {len(all_links)} 条产品链接"
            if progress_info["target_count"] > 0:
                completion_msg += f" (完成度: {progress_info['progress_percentage']}%)"
            completion_msg += f"，已保存到 {out_file}"
            LOG.info(completion_msg)
            
            return True
        finally:
            browser.close()


if __name__ == "__main__":
    ok = main()
    print("✅ test-08 成功" if ok else "❌ test-08 失败")