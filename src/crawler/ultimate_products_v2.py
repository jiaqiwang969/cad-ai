#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
终极产品链接爬取模块 v2
==================
集成test-08的所有优化策略：
- Playwright + stealth 登录
- 智能叶节点检测
- 进度监控和智能停止
- 人类化滚动行为
- 完善的Show More点击策略
"""

import re
import os
import sys
import time
import random
import logging
import importlib.util
import datetime
from typing import List, Dict, Any, Tuple, Optional
from urllib.parse import urlparse, parse_qs
from pathlib import Path

# Playwright
from playwright.sync_api import Playwright, sync_playwright, Page, BrowserContext, Browser


class UltimateProductLinksCrawlerV2:
    """终极产品链接爬取器 v2 - 集成test-08所有优化策略"""
    
    def __init__(self, log_level: int = logging.INFO, headless: bool = True, debug_mode: bool = False):
        """
        初始化终极产品链接爬取器 v2
        
        Args:
            log_level: 日志级别
            headless: 是否使用无头模式
            debug_mode: 是否启用调试模式日志
        """
        self.logger = logging.getLogger("ultimate-products-v2")
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
            self.logger.addHandler(handler)
        self.logger.setLevel(log_level)
        self.logger.propagate = False
        
        # 配置参数
        self.headless = headless
        self.debug_mode = debug_mode
        
        # 产品链接匹配模式
        self.PRODUCT_LINK_PATTERN = re.compile(r"[?&]Product=([0-9\-]+)")
        
        # 初始化stealth模块
        self.stealth11i = self._load_stealth_module()
        
        # Playwright instance management
        self.playwright_instance: Optional[Playwright] = None
        self._created_playwright_internally = False

    def _ensure_playwright_running(self) -> Playwright:
        if self.playwright_instance is None:
            self.playwright_instance = sync_playwright().start()
            self._created_playwright_internally = True
            self.logger.info("Playwright started internally by UltimateProductLinksCrawlerV2.")
        return self.playwright_instance

    def _load_stealth_module(self) -> Optional[Any]:
        """动态加载stealth11i模块"""
        try:
            BASE_DIR = Path(__file__).parent.parent.parent
            path_to_11i = BASE_DIR / "test" / "legacy" / "11i-stealth_cad_downloader.py"
            
            if not path_to_11i.exists():
                self.logger.warning(f"⚠️ Stealth module not found at: {path_to_11i}. Proceeding without stealth login capabilities.")
                return None
            
            MOD11 = importlib.util.spec_from_file_location("stealth11i", str(path_to_11i))
            if MOD11 is None or MOD11.loader is None:
                self.logger.error(f"❌ Failed to create module spec for stealth11i from {path_to_11i}")
                return None

            stealth_module = importlib.util.module_from_spec(MOD11)
            MOD11.loader.exec_module(stealth_module)
            self.logger.info("✅ stealth模块加载成功 (for optional login)")
            return stealth_module
            
        except Exception as e:
            self.logger.error(f"❌ 加载stealth模块失败: {e}", exc_info=self.debug_mode)
            return None

    def human_like_delay(self, min_delay=0.5, max_delay=2.0):
        """人类行为延迟"""
        delay = random.uniform(min_delay, max_delay)
        time.sleep(delay)

    def detect_leaf_node_and_target_count(self, page: Page) -> Tuple[bool, int]:
        """检测是否为叶节点并获取目标产品总数 - 使用简化的数字+results模式"""
        try:
            page_text = page.text_content("body")
            
            # 使用正则表达式检测"数字+results"模式
            # 支持逗号分隔的数字和不间断空格(\u00a0)
            import re
            results_pattern = r'\b[\d,]+(?:\s|\u00a0)+results?\b'
            has_number_results = bool(re.search(results_pattern, page_text, re.IGNORECASE))
            
            self.logger.info(f"🔍 叶节点检测 (来自test-08逻辑): 数字+results模式={'✅' if has_number_results else '❌'}")
            
            if has_number_results:
                self.logger.info("✅ 确认这是一个叶节点页面（基于数字+results模式）")
                target_count = self.extract_target_product_count(page)
                return True, target_count
            else:
                self.logger.warning("⚠️ 这可能不是叶节点页面（未检测到数字+results模式）")
                return False, 0
                
        except Exception as e:
            self.logger.warning(f"⚠️ 叶节点检测失败: {e}", exc_info=self.debug_mode)
            return False, 0

    def extract_target_product_count(self, page: Page) -> int:
        """从页面提取目标产品总数"""
        try:
            count_patterns = [
                r"([\d,]+)\s*results?",
                r"([\d,]+)\s*products?", 
                r"([\d,]+)\s*items?",
                r"showing\s*[\d,]+\s*[-–]\s*[\d,]+\s*of\s*([\d,]+)",
                r"([\d,]+)\s*total",
                r"found\s*([\d,]+)"
            ]
            page_text = page.text_content("body").lower()
            
            self.logger.info(f"🔍 搜索产品数量模式...")
            
            for pattern in count_patterns:
                if self.debug_mode:
                    self.logger.info(f"  📄 尝试模式: {pattern}")
                matches = re.findall(pattern, page_text, re.IGNORECASE)
                if matches:
                    if self.debug_mode:
                        self.logger.info(f"    🎉 模式 {pattern} 匹配到: {matches}")
                    for match_item in matches:
                        try:
                            actual_match_str = match_item if isinstance(match_item, str) else match_item[0]
                            count_str = actual_match_str.replace(',', '')
                            if not count_str.isdigit():
                                if self.debug_mode:
                                    self.logger.warning(f"      ⚠️ 非数字内容: '{count_str}' (来自: '{actual_match_str}')")
                                continue
                            count = int(count_str)
                            if 1 <= count <= 50000:
                                self.logger.info(f"🎯 发现目标产品总数: {count} (来自模式: '{pattern}', 原文: '{actual_match_str}')")
                                return count
                            else:
                                if self.debug_mode:
                                    self.logger.info(f"      🔶 数量 {count} 不在有效范围 [1, 50000] (来自: '{actual_match_str}')")
                        except (ValueError, IndexError) as e_inner:
                            self.logger.warning(f"      ⚠️ 处理匹配项 '{match_item}' 时出错: {e_inner}", exc_info=self.debug_mode)
                            continue
                else:
                    if self.debug_mode:
                        self.logger.info(f"    ❌ 模式 {pattern} 未匹配到任何内容")
            
            self.logger.info("⚠️ 未能提取到目标产品总数")
            return 0
            
        except Exception as e:
            self.logger.warning(f"⚠️ 提取目标产品总数失败: {e}", exc_info=self.debug_mode)
            return 0

    def monitor_progress(self, current_count: int, target_count: int, round_name: str = ""):
        """监控抓取进度"""
        if target_count > 0:
            progress = (current_count / target_count) * 100
            remaining = target_count - current_count
            if self.debug_mode or not hasattr(self, '_last_logged_progress') or abs(progress - getattr(self, '_last_logged_progress', 0)) >= 10.0 or progress >= 95.0 :
                 self.logger.info(f"📈 {round_name}进度: {current_count}/{target_count} ({progress:.1f}%), 还需抓取: {remaining}")
                 self._last_logged_progress = progress
        else:
            if self.debug_mode or not hasattr(self, '_last_logged_count') or abs(current_count - getattr(self, '_last_logged_count', 0)) >= 50:
                self.logger.info(f"📊 {round_name}当前数量: {current_count}")
                self._last_logged_count = current_count
    
    def scroll_full(self, page: Page, current_products: int = 0, target_count: int = 0):
        """逐步滚动到页面底部，带随机人类行为"""
        if self.debug_mode:
            self.logger.info("📜 开始随机化滚动...")
        
        last_height = page.evaluate("document.body.scrollHeight")
        scroll_steps = random.randint(4, 7)
        if self.debug_mode:
            self.logger.info(f"  📜 随机选择 {scroll_steps} 步滚动")
        
        for step in range(scroll_steps):
            position = last_height * (step + 1) / scroll_steps
            page.evaluate(f"window.scrollTo(0, {position});")
            if self.debug_mode:
                self.logger.info(f"  📜 滚动步骤 {step + 1}/{scroll_steps}")
            
            current_progress = (current_products / target_count * 100) if target_count > 0 else 50
            wait_time = random.uniform(0.3, 0.8) if current_progress < 80 else random.uniform(0.5, 1.2)
            time.sleep(wait_time)
            
            if random.random() < 0.3:
                back_scroll = random.randint(20, 100)
                page.evaluate(f"window.scrollBy(0, -{back_scroll});")
                if self.debug_mode:
                    self.logger.info(f"  🔙 随机回滚 {back_scroll}px")
                time.sleep(random.uniform(0.3, 0.8))
                page.evaluate(f"window.scrollBy(0, {back_scroll + 20});")
        
        page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
        final_wait = random.uniform(0.8, 1.5)
        time.sleep(final_wait)
        if self.debug_mode:
            self.logger.info(f"📜 滚动完成，最终等待 {final_wait:.1f}s")

    def extract_products_on_page(self, page: Page, seen_links: set) -> List[str]:
        """提取当前页面所有含 &Product= 的 a 标签链接，去重"""
        elements = page.query_selector_all("a[href*='&Product=']")
        links = []
        for el in elements:
            href = el.get_attribute('href') or ""
            if not href or href in seen_links:
                continue
            if '&Product=' not in href:
                continue
            parsed = urlparse(href)
            if '/product/' not in parsed.path:
                continue
            seen_links.add(href)
            links.append(href)
        return links

    def append_page_size(self, url: str, size: int = 500) -> str:
        """若 URL 中未包含 PageSize 参数，则补充一个较大的值，减少分页次数。"""
        if 'PageSize=' in url:
            return url
        params = f"PageSize={size}&ShowAll=true&IncludeVariants=true"
        return f"{url}{'&' if '?' in url else '?'}{params}"

    def click_show_more_if_any(self, page: Page, target_count: int = 0) -> bool:
        """若页面存在 'Show more results' 按钮，则点击并返回 True"""
        try:
            all_buttons = page.query_selector_all("button")
            if self.debug_mode:
                self.logger.info(f"🔍 页面共有 {len(all_buttons)} 个按钮")
            
            show_more_buttons_details = []
            for i, btn_el in enumerate(all_buttons):
                try:
                    btn_text = (btn_el.text_content() or "").lower()
                    if self.debug_mode and btn_text:
                         pass
                    if 'show' in btn_text and 'more' in btn_text:
                        show_more_buttons_details.append({'index': i, 'element': btn_el, 'text': btn_text})
                        if self.debug_mode:
                           self.logger.info(f"🎯 候选Show More按钮 {i}: '{btn_text}' (visible: {btn_el.is_visible()}, enabled: {btn_el.is_enabled()})")
                except Exception:
                    continue
            
            if self.debug_mode:
                self.logger.info(f"🎯 总共找到 {len(show_more_buttons_details)} 个候选Show More按钮")
            
            btn_to_click = None
            selectors = [
                "button:has-text('Show more')", "button:has-text('Show More')", 
                "button:has-text('Load more')", "button:has-text('More results')",
                "a:has-text('Show more')", ".show-more, .load-more",
                "button[class*='show-more'], button[class*='load-more']"
            ]
            
            for selector in selectors:
                try:
                    btn_to_click = page.query_selector(selector)
                    if btn_to_click and btn_to_click.is_visible() and btn_to_click.is_enabled():
                        self.logger.info(f"✅ 使用选择器找到按钮: {selector}")
                        break
                    btn_to_click = None
                except Exception:
                    btn_to_click = None
                    continue
            
            if not btn_to_click:
                self.logger.info("❌ 所有选择器都未找到可点击的Show More按钮")
                return False

            self.logger.info(f"👆 找到可点击的Show More按钮: '{btn_to_click.text_content()}'")
            btn_to_click.scroll_into_view_if_needed()
            time.sleep(random.uniform(0.5, 1.0))
            
            try:
                btn_to_click.click(timeout=5000)
                self.logger.info("✅ 普通点击成功")
            except Exception as e_click:
                self.logger.warning(f"⚠️ 普通点击失败 ('{btn_to_click.text_content()}'): {e_click}，尝试JS点击")
                try:
                    page.evaluate("arguments[0].click();", btn_to_click)
                    self.logger.info("✅ JavaScript点击成功")
                except Exception as e_js_click:
                    self.logger.error(f"❌ JS点击也失败 ('{btn_to_click.text_content()}'): {e_js_click}")
                    return False

            current_after_click = len(page.query_selector_all("a[href*='&Product=']"))
            progress_after_click = (current_after_click / target_count * 100) if target_count > 0 else 50
            
            post_click_wait = random.uniform(0.2, 0.5) if progress_after_click < 80 else random.uniform(0.4, 0.8)
            up_scroll_prob = 0.3 if progress_after_click < 80 else 0.5
            final_wait_after_scroll = random.uniform(0.4, 0.8) if progress_after_click < 80 else random.uniform(0.8, 1.5)
                
            time.sleep(post_click_wait)
            
            if random.random() < up_scroll_prob:
                up_scroll = random.randint(80, 150)
                page.evaluate(f"window.scrollBy(0, -{up_scroll});")
                if self.debug_mode:
                     self.logger.info(f"  👀 随机上滚查看 {up_scroll}px")
                time.sleep(random.uniform(0.1, 0.3))
            
            page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(final_wait_after_scroll)
            return True
            
        except Exception as e:
            self.logger.warning(f"⚠️ 点击Show More按钮过程中出错: {e}", exc_info=self.debug_mode)
            time.sleep(1)
        return False

    def _check_pagination_signs(self, page: Page) -> bool:
        """检查页面是否有分页或Show More的迹象"""
        try:
            # 检查是否有Show More相关按钮
            show_more_selectors = [
                "button:has-text('Show more')", "button:has-text('Show More')", 
                "button:has-text('Load more')", "button:has-text('More results')",
                "a:has-text('Show more')", ".show-more", ".load-more",
                "button[class*='show-more']", "button[class*='load-more']"
            ]
            
            for selector in show_more_selectors:
                try:
                    element = page.query_selector(selector)
                    if element and element.is_visible():
                        self.logger.info(f"✅ 发现分页迹象：Show More按钮 ({selector})")
                        return True
                except:
                    continue
            
            # 检查是否有分页相关元素
            pagination_selectors = [
                ".pagination", ".pager", ".page-nav",
                "a:has-text('Next')", "a:has-text('下一页')",
                "button:has-text('Next')", "button:has-text('下一页')",
                "[class*='page']", "[class*='next']"
            ]
            
            for selector in pagination_selectors:
                try:
                    element = page.query_selector(selector)
                    if element and element.is_visible():
                        self.logger.info(f"✅ 发现分页迹象：分页元素 ({selector})")
                        return True
                except:
                    continue
            
            # 检查页面文本是否包含分页相关词汇
            page_text = page.text_content("body").lower()
            pagination_keywords = [
                "show more", "load more", "more results", "next page", 
                "下一页", "加载更多", "显示更多"
            ]
            
            for keyword in pagination_keywords:
                if keyword in page_text:
                    self.logger.info(f"✅ 发现分页迹象：关键词 '{keyword}'")
                    return True
            
            self.logger.info("❌ 未发现明显的分页迹象")
            return False
            
        except Exception as e:
            self.logger.warning(f"⚠️ 检查分页迹象时出错: {e}")
            return False  # 出错时保守处理，认为没有分页

    def load_all_results(self, page: Page, target_count: int = 0):
        """持续滚动并点击 'Show more results'，直到全部产品都加载完"""
        
        # 早期检查：如果没有目标数量且初始产品很少，快速判断是否需要加载更多
        initial_products = len(page.query_selector_all("a[href*='&Product=']"))
        
        # 检查页面是否有分页或Show More的迹象
        has_pagination_signs = self._check_pagination_signs(page)
        
        if target_count == 0 and initial_products <= 5 and not has_pagination_signs:
            self.logger.info(f"🎯 页面产品数量少({initial_products}个)且无分页迹象，跳过加载更多结果的尝试")
            return
        
        attempt_count = 0
        max_attempts = 100
        
        no_product_change_rounds = 0
        consecutive_click_failures = 0
        MAX_CONSECUTIVE_CLICK_FAILURES = 3

        # 根据情况调整容忍度
        if target_count > 0:
            max_no_product_change = 5  # 有目标时更宽容
        elif has_pagination_signs:
            max_no_product_change = 3  # 有分页迹象时正常处理
        else:
            max_no_product_change = 2  # 无目标且无分页迹象时更严格
        
        self.logger.info(f"🔄 开始加载所有结果 (目标: {target_count if target_count > 0 else 'N/A'}, 初始: {initial_products}个)...")

        while (attempt_count < max_attempts and
               no_product_change_rounds < max_no_product_change and
               consecutive_click_failures < MAX_CONSECUTIVE_CLICK_FAILURES):
            
            current_products_on_page = len(page.query_selector_all("a[href*='&Product=']"))
            loop_round_name = f"主循环第 {attempt_count + 1}/{max_attempts} 轮"
            self.monitor_progress(current_products_on_page, target_count, loop_round_name)
            
            log_suffix = f"(无产品变化: {no_product_change_rounds}/{max_no_product_change}, 点击失败: {consecutive_click_failures}/{MAX_CONSECUTIVE_CLICK_FAILURES})"
            if self.debug_mode:
                 self.logger.info(f"🚀 {loop_round_name} 开始... {log_suffix}")

            if target_count > 0:
                current_progress_percent = (current_products_on_page / target_count * 100)
                if current_progress_percent >= 100.0:
                    self.logger.info(f"🎯 进度已达 {current_progress_percent:.1f}%，目标完成! (主循环, 跳过最终确认)")
                    return 
                if current_progress_percent >= 95.0 and no_product_change_rounds >= 2:
                    self.logger.info(f"🎯 进度 ({current_progress_percent:.1f}%) >= 95% 且连续 {no_product_change_rounds} 轮无变化，认为抓取完成 (主循环)")
                    break 
                
                if current_progress_percent < 95.0:
                    if self.debug_mode:
                        self.logger.info(f"⚡ 当前进度 {current_progress_percent:.1f}% < 95%，尝试快速点击/滚动...")
                    time.sleep(random.uniform(0.5, 1.5))
                    
                    clicked_in_fast_retry = self.click_show_more_if_any(page, target_count)
                    attempt_count += 1

                    if clicked_in_fast_retry:
                        consecutive_click_failures = 0
                        after_quick_click_products = len(page.query_selector_all("a[href*='&Product=']"))
                        if after_quick_click_products > current_products_on_page:
                            no_product_change_rounds = 0
                            if self.debug_mode:
                                self.logger.info(f"⚡ 快速模式点击：产品数量增加 {current_products_on_page} → {after_quick_click_products}")
                        else:
                            no_product_change_rounds += 1
                            if self.debug_mode:
                                self.logger.info(f"⚡ 快速模式点击：无增长，累计无产品变化轮次 {no_product_change_rounds}")
                        
                        if target_count > 0 and after_quick_click_products >= target_count:
                            self.logger.info(f"🎯 快速模式点击后已达目标产品数量: {after_quick_click_products}/{target_count} (跳过最终确认)")
                            return
                        continue
                    else:
                        consecutive_click_failures += 1
                        if self.debug_mode:
                             self.logger.info(f"⚡ 快速模式：未找到Show More按钮 (连续点击失败: {consecutive_click_failures})，将滚动重试")
                        self.scroll_full(page, current_products_on_page, target_count)
                        no_product_change_rounds += 1 
                    continue

            self.scroll_full(page, current_products_on_page, target_count)
            
            clicked_this_round = self.click_show_more_if_any(page, target_count)
            attempt_count += 1

            if clicked_this_round:
                consecutive_click_failures = 0
                after_std_click_products = len(page.query_selector_all("a[href*='&Product=']"))
                self.monitor_progress(after_std_click_products, target_count, loop_round_name)
                
                if after_std_click_products == current_products_on_page:
                    no_product_change_rounds += 1
                    self.logger.warning(f"⚠️ 点击Show More后产品数量无增加 ({loop_round_name}, 无产品变化轮次: {no_product_change_rounds})")
                else:
                    no_product_change_rounds = 0
                    if self.debug_mode:
                        self.logger.info(f"✅ 点击Show More后产品数量增加 {current_products_on_page} -> {after_std_click_products}")

                if target_count > 0 and after_std_click_products >= target_count:
                    self.logger.info(f"🎯 标准点击后已达目标产品数量: {after_std_click_products}/{target_count} (跳过最终确认)")
                    return
            else:
                consecutive_click_failures += 1
                no_product_change_rounds += 1 
                self.logger.warning(f"⚠️ 未找到或未能点击Show More按钮 ({loop_round_name}, {log_suffix})")
                
                # 特殊处理：如果没有目标数量且产品很少，连续找不到按钮时提前退出
                if target_count == 0 and current_products_on_page <= 10 and consecutive_click_failures >= 2:
                    self.logger.info(f"🎯 无目标数量且产品少({current_products_on_page}个)，连续{consecutive_click_failures}次未找到Show More，提前结束")
                    break

        if attempt_count >= max_attempts:
            self.logger.warning(f"⚠️ 主加载阶段因达到最大尝试次数 ({max_attempts}) 而停止")
        elif no_product_change_rounds >= max_no_product_change:
            self.logger.info(f"✅ 主加载阶段因连续 {max_no_product_change} 轮无产品数量变化而停止")
        elif consecutive_click_failures >= MAX_CONSECUTIVE_CLICK_FAILURES:
            self.logger.warning(f"⚠️ 主加载阶段因连续 {MAX_CONSECUTIVE_CLICK_FAILURES} 次未能点击Show More按钮而停止")
            
        # 最终确认阶段 - 根据情况调整强度
        if target_count == 0 and not has_pagination_signs:
            self.logger.info("🔄 开始简化最终确认阶段（无目标数量且无分页迹象）...")
            final_scroll_rounds_count = 2  # 简化为2轮
        else:
            self.logger.info("🔄 开始最终彻底确认阶段...")
            final_scroll_rounds_count = 5  # 标准5轮
            
        consecutive_no_change_final = 0
        consecutive_no_button_final = 0

        for final_scroll_iter in range(final_scroll_rounds_count):
            before_final_scroll_products = len(page.query_selector_all("a[href*='&Product=']"))
            final_round_name = f"最终确认第 {final_scroll_iter + 1}/{final_scroll_rounds_count} 轮"
            self.monitor_progress(before_final_scroll_products, target_count, final_round_name)
            if self.debug_mode:
                 self.logger.info(f"📊 {final_round_name} 开始，当前产品数: {before_final_scroll_products}")
            
            self.scroll_full(page, before_final_scroll_products, target_count)
            time.sleep(random.uniform(2.5, 3.5)) 
            page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(random.uniform(2.5, 3.5))
            
            if self.debug_mode:
                self.logger.info(f"  🔍 {final_round_name}：检查是否还有Show More按钮...")
            
            button_was_clicked_final_round = self.click_show_more_if_any(page, target_count)

            if button_was_clicked_final_round:
                if self.debug_mode:
                    self.logger.info(f"  🎯 {final_round_name}：发现并点击了Show More按钮！继续检查...")
                time.sleep(random.uniform(3.0, 4.0))
                consecutive_no_change_final = 0 
                consecutive_no_button_final = 0 
            else:
                consecutive_no_button_final += 1
                if self.debug_mode:
                     self.logger.info(f"  ❌ {final_round_name}：未找到/点击Show More按钮 (连续未找到: {consecutive_no_button_final})")
                
                # 根据模式调整退出条件
                max_no_button_tolerance = 2 if (target_count == 0 and not has_pagination_signs) else 3
                if consecutive_no_button_final >= max_no_button_tolerance:
                    self.logger.info(f"🎯 连续 {consecutive_no_button_final} 轮最终确认未找到/点击Show More，确认已到页面底部！")
                    break
            
            after_final_scroll_products = len(page.query_selector_all("a[href*='&Product=']"))
            if self.debug_mode:
                self.logger.info(f"📊 {final_round_name} 结果: {before_final_scroll_products} → {after_final_scroll_products}")
            
            if after_final_scroll_products == before_final_scroll_products:
                consecutive_no_change_final += 1
                if self.debug_mode:
                     self.logger.info(f"  ✅ {final_round_name} 无新增产品 (连续无变化: {consecutive_no_change_final})")
                
                # 根据模式调整无变化容忍度
                max_no_change_tolerance = 2 if (target_count == 0 and not has_pagination_signs) else 3
                if consecutive_no_change_final >= max_no_change_tolerance:
                    self.logger.info(f"🎯 连续 {consecutive_no_change_final} 轮最终确认无变化，确认抓取完成！")
                    break
            else:
                consecutive_no_change_final = 0 
                if self.debug_mode:
                    self.logger.info(f"  🆕 {final_round_name} 发现新产品: +{after_final_scroll_products - before_final_scroll_products}")
        
        final_product_count = len(page.query_selector_all("a[href*='&Product=']"))
        self.logger.info(f"🏁 load_all_results完成，最终产品链接数: {final_product_count}")
        if target_count > 0:
            final_progress_percent = (final_product_count / target_count) * 100
            self.logger.info(f"📊 最终进度: {final_progress_percent:.1f}% ({final_product_count}/{target_count})")

    def _perform_login(self, page: Page, email: Optional[str] = None, password: Optional[str] = None) -> bool:
        """Performs stealth login if module and credentials available."""
        if not self.stealth11i:
            self.logger.info("⏭️ Stealth模块未加载，跳过登录。")
            return False

        login_email = email or os.getenv("TRACEPARTS_EMAIL")
        login_password = password or os.getenv("TRACEPARTS_PASSWORD")

        if not login_email or not login_password:
            self.logger.warning("⚠️ 未提供登录邮箱或密码 (通过参数或环境变量 TRACEPARTS_EMAIL/PASSWORD)，跳过登录。")
            return False

        self.logger.info(f"🔐 使用邮箱 {login_email[:5]}... 进行stealth登录流程...")
        try:
            if self.stealth11i.stealth_login(page, login_email, login_password):
                self.logger.info("✅ 登录成功！")
                return True
            else:
                self.logger.warning("⚠️ 登录失败，但继续尝试抓取...")
                return False
        except Exception as e:
            self.logger.error(f"❌ 登录过程中发生严重错误: {e}", exc_info=self.debug_mode)
            return False

    def _tp_code_from_url(self, url: str) -> str:
        """从 leaf URL 提取 TP 编码，例 TP01002002006"""
        qs_part = urlparse(url).query
        params = parse_qs(qs_part)
        cp = params.get('CatalogPath', [''])[0]
        if cp.startswith('TRACEPARTS:'):
            cp = cp.split(':',1)[1]
        return cp if cp else "UNKNOWN_TP_CODE"

    def collect_all_product_links(self, leaf_url: str, 
                                  tp_code: Optional[str] = None, 
                                  page_text_content: Optional[str] = None,
                                  email: Optional[str] = None, 
                                  password: Optional[str] = None,
                                  p: Optional[Playwright] = None,
                                  browser_instance: Optional[Browser] = None,
                                  context_instance: Optional[BrowserContext] = None
                                 ) -> Tuple[List[str], Dict[str, Any]]:
        """
        主抓取函数：访问 leaf 页面，滚动+点击加载全部产品，并收集链接。
        移植并适配 test-08 的 main() 和 collect_all_product_links() 逻辑。

        Args:
            leaf_url: The URL of the leaf category page.
            tp_code: Optional TraceParts code for this leaf, used for logging/output.
            page_text_content: Optional pre-fetched page text. (Currently not used for re-check here)
            email: Optional email for login.
            password: Optional password for login.
            p: Optional existing Playwright instance.
            browser_instance: Optional existing Browser instance.
            context_instance: Optional existing BrowserContext instance.

        Returns:
            Tuple: (List of product links, progress_info dictionary)
        """
        _internal_playwright = False
        _internal_browser = False
        _internal_context = False
        
        page_to_use: Optional[Page] = None

        actual_tp_code = tp_code or self._tp_code_from_url(leaf_url)
        self.logger.info(f"🚀 开始为叶节点 [{actual_tp_code}] ({leaf_url}) 提取产品链接 (V2 logic)..." )
        
        if hasattr(self, '_last_logged_progress'):
            delattr(self, '_last_logged_progress')
        if hasattr(self, '_last_logged_count'):
            delattr(self, '_last_logged_count')

        try:
            if p is None:
                p = self._ensure_playwright_running()
            
            if browser_instance is None:
                if self.stealth11i:
                    browser_instance, context_instance, page_to_use = self.stealth11i.create_stealth_browser(p, headless=self.headless)
                    _internal_browser = True
                    _internal_context = True
                else:
                    self.logger.warning("Stealth module not available, launching standard browser.")
                    browser_instance = p.chromium.launch(headless=self.headless)
                    _internal_browser = True
                    context_instance = browser_instance.new_context()
                    _internal_context = True
                    page_to_use = context_instance.new_page()
            elif context_instance is None:
                context_instance = browser_instance.new_context()
                _internal_context = True
                page_to_use = context_instance.new_page()
            elif page_to_use is None:
                page_to_use = context_instance.new_page()

            if page_to_use is None:
                self.logger.error("❌ Critical: Could not obtain a page object.")
                return [], {"error": "Failed to obtain page object"}

            login_skipped_or_failed = False
            if self.stealth11i and (email or os.getenv("TRACEPARTS_EMAIL")):
                if not self._perform_login(page_to_use, email, password):
                    login_skipped_or_failed = True
            else:
                self.logger.info("⏭️ 登录跳过 (无stealth模块或未配置邮箱).")
                login_skipped_or_failed = True

            enhanced_url = self.append_page_size(leaf_url, 500)
            self.logger.info(f"🌐 访问增强URL: {enhanced_url}")
            
            page_to_use.goto(enhanced_url, timeout=60000, wait_until='networkidle')

            is_leaf, target_count = self.detect_leaf_node_and_target_count(page_to_use)
            if not is_leaf:
                self.logger.warning(f"⚠️ 页面 {leaf_url} 似乎不是叶节点 (基于test-08逻辑)，但继续尝试抓取...")

            initial_elements = page_to_use.query_selector_all("a[href*='&Product=']")
            self.logger.info(f"📊 页面初始加载的产品链接数: {len(initial_elements)}")
            if target_count > 0:
                self.logger.info(f"🎯 目标产品总数 (来自页面提取): {target_count}")
                if len(initial_elements) > target_count:
                    self.logger.warning(f"⚠️ 初始加载数 ({len(initial_elements)}) 大于提取到的目标数 ({target_count}). 将以目标数为准进行进度判断，但可能全部已加载。")

            self.load_all_results(page_to_use, target_count)
            
            seen_links_set = set()
            all_product_links = self.extract_products_on_page(page_to_use, seen_links_set)
            
            final_extracted_count = len(all_product_links)
            self.logger.info(f"🎯 最终抓取结果 for [{actual_tp_code}]: {final_extracted_count} 个产品链接")
            
            progress_info = {
                "leaf_url": leaf_url,
                "tp_code": actual_tp_code,
                "extracted_count": final_extracted_count,
                "target_count_on_page": target_count,
                "initial_load_count": len(initial_elements),
                "progress_percentage": 0.0,
                "completion_status": "unknown",
                "login_skipped_or_failed": login_skipped_or_failed,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            
            if target_count > 0:
                final_progress = (final_extracted_count / target_count) * 100 if target_count > 0 else 0.0
                missing_count = target_count - final_extracted_count
                progress_info["progress_percentage"] = round(final_progress, 1)
                
                self.logger.info(f"📊 完成度 for [{actual_tp_code}]: {final_progress:.1f}% ({final_extracted_count}/{target_count})")
                if missing_count > 0:
                    self.logger.warning(f"⚠️ 可能遗漏 for [{actual_tp_code}]: {missing_count} 个产品 (目标: {target_count}, 抓取: {final_extracted_count})")
                    progress_info["completion_status"] = "partial_match_to_target" if final_extracted_count > 0 else "no_match_to_target"
                elif missing_count < 0:
                    self.logger.info(f"✅ 超出目标数量完成 for [{actual_tp_code}]! (目标: {target_count}, 抓取: {final_extracted_count})")
                    progress_info["completion_status"] = "exceeded_target"
                else:
                    self.logger.info(f"✅ 精确达到目标数量 for [{actual_tp_code}]!")
                    progress_info["completion_status"] = "complete_match_to_target"
            else:
                self.logger.info(f"📊 未检测到页面目标数量 for [{actual_tp_code}]，按实际抓取结果 ({final_extracted_count}) 统计")
                progress_info["completion_status"] = "no_target_on_page" if final_extracted_count > 0 else "no_target_and_no_links"

            return all_product_links, progress_info

        except Exception as e_main:
            self.logger.error(f"❌ 在为 {leaf_url} 提取产品链接时发生严重错误: {e_main}", exc_info=self.debug_mode)
            return [], {"error": str(e_main), "leaf_url": leaf_url, "tp_code": actual_tp_code}
        
        finally:
            if page_to_use and (_internal_browser or _internal_context):
                 try:
                     page_to_use.close()
                 except Exception as e_close:
                     self.logger.warning(f"Error closing page for {leaf_url}: {e_close}", exc_info=self.debug_mode)
            
            if _internal_context and context_instance:
                 try:
                     context_instance.close()
                 except Exception as e_close:
                     self.logger.warning(f"Error closing context for {leaf_url}: {e_close}", exc_info=self.debug_mode)

            if _internal_browser and browser_instance:
                 try:
                     browser_instance.close()
                 except Exception as e_close:
                     self.logger.warning(f"Error closing browser for {leaf_url}: {e_close}", exc_info=self.debug_mode)
            
            if self._created_playwright_internally and self.playwright_instance:
                try:
                    self.playwright_instance.stop()
                    self.playwright_instance = None
                    self._created_playwright_internally = False
                except Exception as e_stop:
                     self.logger.warning(f"Error stopping internal Playwright: {e_stop}", exc_info=self.debug_mode)

    def close(self):
        """
        Clean up any persistent resources, like a Playwright instance
        if it was started by this class and not passed in.
        """
        if self._created_playwright_internally and self.playwright_instance:
            try:
                self.playwright_instance.stop()
                self.logger.info("Playwright instance stopped by UltimateProductLinksCrawlerV2.close().")
                self.playwright_instance = None
                self._created_playwright_internally = False
            except Exception as e:
                self.logger.error(f"Error stopping Playwright in close(): {e}", exc_info=self.debug_mode)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s')
    
    test_leaf_url_no_target = "https://www.traceparts.com/en/search/traceparts-classification-fasteners?CatalogPath=TRACEPARTS%3ATP02"
    test_leaf_url_small_target = "https://www.traceparts.cn/en/search/traceparts-classification-simulation-models-flexible-objects-belts-flat-belts?CatalogPath=TRACEPARTS%3ATP08001001001"

    crawler = UltimateProductLinksCrawlerV2(log_level=logging.DEBUG, headless=True, debug_mode=True)
    
    with crawler:
        links_small, info_small = crawler.collect_all_product_links(test_leaf_url_small_target)
        print(f"\n--- Results for Small Target URL: {test_leaf_url_small_target} ---")
        print(f"Found {len(links_small)} links.")
        print(f"Info: {json.dumps(info_small, indent=2)}")

    print("\nExample run finished.")