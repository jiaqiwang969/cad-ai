#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自适应规格解析器 - 完全集成test-09-1逻辑
==============
基于test-09-1的完整逻辑，实现产品规格的智能提取
"""

import re
import time
import logging
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urlparse, parse_qs, urlencode
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException


class AdaptiveSpecsParser:
    """自适应规格解析器 - 集成test-09-1完整逻辑"""
    
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        
        # 产品编号识别关键词（多语言支持）
        self.reference_keywords = [
            'part number', 'part no', 'part#', 'p/n',
            'product number', 'product code', 'product id',
            'model', 'model number', 'model no',
            'reference', 'ref', 'item number', 'item no',
            'catalog number', 'cat no', 'sku',
            'bestellnummer', 'artikelnummer', 'teilenummer',  # 德语
            'numéro', 'référence',  # 法语
            'número', 'codigo',  # 西班牙语
            '型号', '编号', '料号'  # 中文
        ]
    
    def parse_specifications(self, driver, url: str) -> List[Dict[str, Any]]:
        """
        主要规格解析入口 - 完全复制test-09-1逻辑
        返回格式与现有pipeline兼容的规格列表
        """
        try:
            self.logger.info(f"🎯 开始解析产品规格: {url}")
            
            # Step 1: 提取基础产品信息
            base_product_info = self.extract_base_product_info(url)
            
            # Step 2: 执行完整的产品规格提取（test-09-1核心逻辑）
            specifications, all_headers = self.extract_all_product_specifications(driver)
            
            # Step 3: 为每个规格生成详细URL
            enhanced_specifications = []
            for spec in specifications:
                spec_urls = self.generate_specification_urls(
                    base_product_info, spec.get('reference', '')
                )
                
                # 转换为pipeline兼容格式
                enhanced_spec = {
                    'reference': spec.get('reference', ''),
                    'dimensions': spec.get('dimensions', ''),
                    'weight': spec.get('weight', ''),
                    'parameters': spec.get('parameters', {}),
                    'specification_urls': spec_urls,
                    'base_product_name': base_product_info['base_product_name'],
                    'product_id': base_product_info['product_id'],
                    'table_type': spec.get('table_type', 'unknown'),
                    'row_index': spec.get('row_index', 0),
                    'headers': spec.get('headers', all_headers),
                    'all_cells': spec.get('all_cells', [])
                }
                enhanced_specifications.append(enhanced_spec)
            
            self.logger.info(f"✅ 成功解析 {len(enhanced_specifications)} 个产品规格")
            return enhanced_specifications
            
        except Exception as e:
            self.logger.error(f"❌ 规格解析失败: {e}")
            return []
    
    def extract_base_product_info(self, product_url: str) -> Dict[str, Any]:
        """提取基础产品信息 - 复制test-09-1逻辑"""
        try:
            parsed_url = urlparse(product_url)
            path_parts = parsed_url.path.split('/')
            query_params = parse_qs(parsed_url.query)
            
            # 提取产品名称（URL路径最后一部分）
            base_product_name = path_parts[-1] if path_parts else 'unknown-product'
            
            # 提取产品ID（查询参数中的Product字段）
            product_id = query_params.get('Product', ['unknown-id'])[0]
            
            result = {
                'base_product_name': base_product_name,
                'product_id': product_id,
                'query_params': query_params
            }
            
            self.logger.debug(f"📋 基础产品信息: {result}")
            return result
            
        except Exception as e:
            self.logger.error(f"基础产品信息提取失败: {e}")
            return {
                'base_product_name': 'unknown-product',
                'product_id': 'unknown-id',
                'query_params': {}
            }
    
    def extract_all_product_specifications(self, driver) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        完整的产品规格提取 - 完全复制test-09-1的extract_all_product_specifications逻辑
        """
        specifications = []
        all_headers = []
        
        try:
            # ========== Step 1: 页面预处理和稳定等待 ==========
            self.logger.debug("🔄 Step 1: 页面预处理和稳定等待")
            
            # 等待页面基本结构加载
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
            except TimeoutException:
                self.logger.warning("页面body加载超时，继续处理")
            
            # 基础等待
            time.sleep(2)
            
            # ========== Step 2: 检测动态内容并处理 ==========
            self.logger.debug("🔄 Step 2: 检测动态内容")
            
            # 查找分页信息，判断是否需要等待动态加载
            pagination_indicators = [
                "items per page", "out of", "total", "results", "showing",
                "页面", "共", "总计", "显示"
            ]
            
            has_pagination_text = False
            for indicator in pagination_indicators:
                try:
                    elements = driver.find_elements(By.XPATH, 
                        f"//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{indicator}')]")
                    for elem in elements:
                        if elem.is_displayed() and elem.text.strip():
                            has_pagination_text = True
                            self.logger.debug(f"发现分页信息: '{elem.text.strip()}'")
                            break
                    if has_pagination_text:
                        break
                except Exception:
                    continue
            
            # ========== Step 3: 6种动态加载策略 ==========
            if has_pagination_text:
                self.logger.debug("🔄 Step 3: 执行动态加载策略")
                success_strategy = self.apply_dynamic_loading_strategies(driver)
                self.logger.debug(f"动态加载策略结果: {success_strategy}")
            
            # ========== Step 4: 最终页面稳定等待 ==========
            self.logger.debug("🔄 Step 4: 最终页面稳定等待")
            time.sleep(1)
            
            # 确保页面完全渲染
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(0.5)
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(0.5)
            
            # ========== Step 5: 智能表格选择和数据提取 ==========
            self.logger.debug("🔄 Step 5: 智能表格选择")
            
            selected_table = self.intelligent_table_selection(driver)
            
            if selected_table:
                self.logger.debug("✅ 找到合适的表格，开始提取数据")
                table_specs, table_headers = self.extract_table_specifications(selected_table)
                specifications.extend(table_specs)
                all_headers = table_headers
            else:
                self.logger.warning("❌ 未找到合适的产品表格")
            
            return specifications, all_headers
            
        except Exception as e:
            self.logger.error(f"❌ 产品规格提取失败: {e}")
            return [], []
    
    def apply_dynamic_loading_strategies(self, driver) -> str:
        """应用6种动态加载策略 - 复制test-09-1逻辑"""
        strategies = [
            ("延长等待策略", self.strategy_extended_wait),
            ("强制刷新策略", self.strategy_force_refresh),
            ("多次滚动策略", self.strategy_multiple_scroll),
            ("点击触发器策略", self.strategy_click_triggers),
            ("等待元素策略", self.strategy_wait_elements),
            ("最终滚动策略", self.strategy_final_scroll)
        ]
        
        for strategy_name, strategy_func in strategies:
            try:
                self.logger.debug(f"🔄 尝试: {strategy_name}")
                result = strategy_func(driver)
                if result:
                    self.logger.debug(f"✅ {strategy_name} 成功")
                    return strategy_name
                else:
                    self.logger.debug(f"❌ {strategy_name} 无效果")
            except Exception as e:
                self.logger.debug(f"❌ {strategy_name} 异常: {e}")
                continue
        
        return "无策略成功"
    
    def strategy_extended_wait(self, driver) -> bool:
        """策略1: 延长等待策略"""
        try:
            # 等待可能的AJAX内容加载
            WebDriverWait(driver, 15).until(
                lambda d: len(d.find_elements(By.TAG_NAME, 'table')) > 0 or
                         len(d.find_elements(By.XPATH, "//div[contains(@class, 'spec')]")) > 0
            )
            time.sleep(3)
            return True
        except TimeoutException:
            return False
    
    def strategy_force_refresh(self, driver) -> bool:
        """策略2: 强制刷新策略"""
        try:
            current_url = driver.current_url
            driver.refresh()
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            time.sleep(2)
            return True
        except Exception:
            return False
    
    def strategy_multiple_scroll(self, driver) -> bool:
        """策略3: 多次滚动策略"""
        try:
            for i in range(3):
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1)
                driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(1)
            return True
        except Exception:
            return False
    
    def strategy_click_triggers(self, driver) -> bool:
        """策略4: 点击触发器策略"""
        try:
            # 尝试点击"Show All"或"All"选项
            all_selectors = [
                "//li[normalize-space(.)='All']",
                "//div[normalize-space(.)='All']",
                "//option[normalize-space(.)='All']",
                "//span[normalize-space(.)='All']",
                "//button[normalize-space(.)='All']",
                "//a[normalize-space(.)='All']",
                "//*[@role='option'][normalize-space(.)='All']",
                "//*[contains(@class,'option')][normalize-space(.)='All']",
                "//*[contains(@class,'menu-item')][normalize-space(.)='All']"
            ]
            
            clicked = False
            for selector in all_selectors:
                try:
                    elements = driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            self.logger.debug(f"找到All选项: {element.text}")
                            element.click()
                            time.sleep(3)
                            clicked = True
                            break
                    if clicked:
                        break
                except Exception:
                    continue
            
            return clicked
        except Exception:
            return False
    
    def strategy_wait_elements(self, driver) -> bool:
        """策略5: 等待元素策略"""
        try:
            # 等待特定元素出现
            wait_selectors = [
                "//table[@class]",
                "//div[@class='specifications']",
                "//div[@class='product-details']",
                "//tr[td]"
            ]
            
            for selector in wait_selectors:
                try:
                    WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, selector))
                    )
                    return True
                except TimeoutException:
                    continue
            
            return False
        except Exception:
            return False
    
    def strategy_final_scroll(self, driver) -> bool:
        """策略6: 最终滚动策略"""
        try:
            # 执行全面的页面滚动
            driver.execute_script("""
                var scrollHeight = Math.max(
                    document.body.scrollHeight,
                    document.body.offsetHeight,
                    document.documentElement.clientHeight,
                    document.documentElement.scrollHeight,
                    document.documentElement.offsetHeight
                );
                window.scrollTo(0, scrollHeight);
            """)
            time.sleep(2)
            
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)
            
            return True
        except Exception:
            return False
    
    def intelligent_table_selection(self, driver) -> Optional[Any]:
        """智能表格选择 - 完全复制test-09-1逻辑"""
        
        # ========== 方式A: 通过标题查找表格 ==========
        self.logger.debug("🔍 方式A: 通过标题查找表格")
        
        title_selectors = [
            "//h1[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'spec')]",
            "//h2[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'spec')]",
            "//h3[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'spec')]",
            "//h1[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'product')]",
            "//h2[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'product')]",
            "//div[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'spec')]",
        ]
        
        for selector_idx, selector in enumerate(title_selectors):
            try:
                elements = driver.find_elements(By.XPATH, selector)
                self.logger.debug(f"选择器 {selector_idx+1}: 找到 {len(elements)} 个元素")
                
                for elem in elements:
                    if elem.is_displayed() and elem.text.strip():
                        # 查找该元素附近的表格
                        try:
                            # 先尝试在同一父容器内查找
                            parent = elem.find_element(By.XPATH, "./..")
                            tables_in_parent = parent.find_elements(By.TAG_NAME, 'table')
                            
                            if not tables_in_parent:
                                # 尝试在后续兄弟元素中查找
                                tables_in_parent = elem.find_elements(By.XPATH, "./following-sibling::*//table")
                            
                            if not tables_in_parent:
                                # 尝试在整个文档中查找该元素之后的表格
                                tables_in_parent = elem.find_elements(By.XPATH, "./following::table")
                            
                            if tables_in_parent:
                                candidate_table = tables_in_parent[0]
                                
                                # 检查表格是否真的包含产品数据
                                if self.validate_table_content(candidate_table):
                                    self.logger.debug("✅ 通过标题找到合适的表格")
                                    return candidate_table
                                    
                        except Exception as e:
                            self.logger.debug(f"分析元素附近表格时出错: {e}")
                            
            except Exception as e:
                self.logger.debug(f"选择器 {selector_idx+1} 出错: {e}")
        
        # ========== 方式B: 表格评分机制 ==========
        self.logger.debug("🔍 方式B: 表格评分机制")
        
        tables = driver.find_elements(By.TAG_NAME, 'table')
        
        if not tables:
            self.logger.warning("页面中未找到任何表格")
            return None
        
        best_table = None
        best_score = 0
        
        self.logger.debug(f"发现 {len(tables)} 个表格，开始评分...")
        
        for i, table in enumerate(tables):
            if not table.is_displayed():
                continue
            
            score = self.score_table_for_product_specs(table)
            self.logger.debug(f"表格 {i+1} 评分: {score}")
            
            if score > best_score:
                best_score = score
                best_table = table
                self.logger.debug(f"✅ 表格 {i+1} 成为最佳候选 (评分: {score})")
        
        if best_table and best_score > 0:
            self.logger.debug(f"最终选择表格，评分: {best_score}")
            return best_table
        else:
            self.logger.warning("所有表格评分均为0，未找到合适的表格")
            return None
    
    def validate_table_content(self, table) -> bool:
        """验证表格是否包含有意义的产品数据"""
        try:
            rows = table.find_elements(By.TAG_NAME, 'tr')
            if len(rows) < 2:
                return False
            
            # 检查前几行是否有非空且有意义的内容
            meaningful_rows = 0
            for row in rows[:5]:
                cells = row.find_elements(By.CSS_SELECTOR, 'td, th')
                cell_texts = [cell.text.strip() for cell in cells]
                non_empty_cells = [text for text in cell_texts if text and len(text) > 1]
                
                if len(non_empty_cells) >= 2:
                    meaningful_rows += 1
            
            return meaningful_rows >= 2
        except:
            return False
    
    def score_table_for_product_specs(self, table) -> int:
        """为表格评分 - 完全复制test-09-1的评分逻辑"""
        score = 0
        
        try:
            rows = table.find_elements(By.TAG_NAME, 'tr')
            if len(rows) < 2:
                return 0
            
            for row in rows[:10]:  # 只检查前10行
                cells = row.find_elements(By.CSS_SELECTOR, 'td, th')
                cell_texts = [cell.text.strip() for cell in cells]
                non_empty_cells = [text for text in cell_texts if text and len(text) > 1]
                
                if len(non_empty_cells) >= 2:
                    score += len(non_empty_cells)
                    
                    # 检查是否包含产品编号相关词汇
                    for text in cell_texts:
                        text_lower = text.lower()
                        if any(keyword in text_lower for keyword in self.reference_keywords):
                            score += 10
                        # 检查是否看起来像产品编号
                        if self.is_likely_product_reference(text):
                            score += 5
            
            return score
        except:
            return 0
    
    def extract_table_specifications(self, table) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        从表格提取规格 - 完全复制test-09-1的表格处理逻辑
        """
        specifications = []
        all_headers = []
        seen_references = set()
        
        try:
            rows = table.find_elements(By.TAG_NAME, 'tr')
            if len(rows) < 1:
                return [], []
            
            # ========== 检测表格类型（纵向 vs 横向）==========
            is_vertical_table = False
            
            # 检查前几行是否都是2列格式
            two_col_count = 0
            for i, row in enumerate(rows[:5]):  # 检查前5行
                cells = row.find_elements(By.CSS_SELECTOR, 'td, th')
                if len(cells) == 2:
                    two_col_count += 1
            
            if two_col_count >= 3:  # 如果至少3行都是2列，可能是纵向表格
                is_vertical_table = True
                self.logger.debug("检测到纵向表格格式（属性-值对）")
            
            # ========== 纵向表格处理 ==========
            if is_vertical_table:
                self.logger.debug("从纵向表格提取数据...")
                for i, row in enumerate(rows):
                    cells = row.find_elements(By.CSS_SELECTOR, 'td, th')
                    if len(cells) != 2:
                        continue
                    
                    prop_name = cells[0].text.strip()
                    prop_value = cells[1].text.strip()
                    
                    if prop_value and len(prop_value) >= 2 and prop_value not in seen_references:
                        # 智能判断：如果看起来像编号（包含数字或特殊格式）
                        if self.is_likely_product_reference(prop_value):
                            spec_info = {
                                'reference': prop_value,
                                'row_index': i,
                                'dimensions': '',
                                'weight': '',
                                'property_name': prop_name,
                                'table_type': 'vertical',
                                'parameters': {prop_name: prop_value}
                            }
                            
                            specifications.append(spec_info)
                            seen_references.add(prop_value)
                            all_headers.append(prop_name)
                            self.logger.debug(f"提取规格: {prop_value} (来自: {prop_name})")
            
            # ========== 横向表格处理 ==========
            else:
                self.logger.debug("检测到横向表格格式")
                
                # 查找表头行
                header_row_index = -1
                header_cells = []
                
                for i, row in enumerate(rows):
                    cells = row.find_elements(By.CSS_SELECTOR, 'td, th')
                    if not cells:
                        continue
                    
                    # 如果是th元素，很可能是表头
                    th_cells = row.find_elements(By.TAG_NAME, 'th')
                    is_header_row = len(th_cells) == len(cells) and len(th_cells) > 0
                    
                    if is_header_row:
                        header_row_index = i
                        header_cells = [cell.text.strip() for cell in cells]
                        all_headers = header_cells
                        self.logger.debug(f"识别表头行 {i+1}: {header_cells[:5]}...")
                        break
                
                # 确定产品编号列（根据列名）
                product_columns = []
                if header_cells:
                    for j, header in enumerate(header_cells):
                        header_lower = header.lower()
                        
                        # 匹配各种语言的产品编号列名
                        for keyword in self.reference_keywords:
                            if keyword in header_lower:
                                product_columns.append(j)
                                self.logger.debug(f"识别产品编号列 {j+1}: '{header}'")
                                break
                        
                    # 使用第一个产品编号列
                    if len(product_columns) > 1:
                        product_columns = product_columns[:1]
                
                # 如果没有识别到产品编号列，使用智能判断
                use_smart_detection = not product_columns
                
                # 提取数据行
                for i, row in enumerate(rows):
                    if i <= header_row_index:  # 跳过表头及之前的行
                        continue
                        
                    cells = row.find_elements(By.CSS_SELECTOR, 'td, th')
                    if not cells:
                        continue
                    
                    cell_texts = [cell.text.strip() for cell in cells]
                    
                    # 构建参数字典
                    parameters = {}
                    for j, cell_text in enumerate(cell_texts):
                        if j < len(header_cells) and header_cells[j] and cell_text:
                            parameters[header_cells[j]] = cell_text
                    
                    # 查找可能的产品编号
                    found_reference = None
                    if use_smart_detection:
                        # 智能检测模式：扫描所有单元格
                        for j, cell_text in enumerate(cell_texts):
                            if self.is_likely_product_reference(cell_text) and cell_text not in seen_references:
                                found_reference = cell_text
                                break
                    else:
                        # 列索引模式：只检查产品编号列
                        for col_idx in product_columns:
                            if col_idx < len(cell_texts):
                                cell_text = cell_texts[col_idx]
                                if cell_text and len(cell_text) >= 2 and cell_text not in seen_references:
                                    found_reference = cell_text
                                    break
                    
                    if found_reference:
                        spec_info = {
                            'reference': found_reference,
                            'row_index': i,
                            'dimensions': self.extract_dimensions_from_cells(cell_texts),
                            'weight': self.extract_weight_from_cells(cell_texts),
                            'table_type': 'horizontal',
                            'all_cells': cell_texts,
                            'headers': header_cells,
                            'parameters': parameters
                        }
                        
                        specifications.append(spec_info)
                        seen_references.add(found_reference)
                        self.logger.debug(f"提取规格: {found_reference}")
            
            return specifications, all_headers
            
        except Exception as e:
            self.logger.error(f"表格规格提取失败: {e}")
            return [], []
    
    def is_likely_product_reference(self, text: str, debug_enabled: bool = False) -> bool:
        """智能判断文本是否可能是产品编号 - 完全复制test-09-1逻辑"""
        if debug_enabled:
            self.logger.debug(f"分析文本: '{text}'")
        
        # 放宽长度限制到2个字符，支持像'SD'这样的短产品编号
        if not text or len(text) < 2:
            if debug_enabled:
                self.logger.debug(f"❌ 文本为空或长度不足2: {len(text) if text else 0}")
            return False
        
        # 明显的排除项
        exclude_patterns = [
            r'^https?://',  # URL
            r'^www\.',      # 网址
            r'@',           # 邮箱
            r'^\d{4}-\d{2}-\d{2}',  # 日期格式
            r'^\+?\d{10,}$',  # 电话号码
        ]
        
        for pattern in exclude_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                if debug_enabled:
                    self.logger.debug(f"❌ 匹配排除模式: {pattern}")
                return False
        
        # 排除纯描述性文本（全是常见英文单词），但保留'N/A'等可能的产品编号
        common_words = [
            'description', 'manufacturer', 'material', 'color', 'size',
            'weight', 'length', 'width', 'height', 'diameter', 'thickness'
        ]
        
        text_lower = text.lower()
        # 保留 'N/A', 'TBD', 'TBA' 等可能是产品编号的值
        special_codes = ['n/a', 'na', 'tbd', 'tba', 'pending', 'standard', 'default']
        
        if text_lower in special_codes:
            if debug_enabled:
                self.logger.debug(f"✅ 保留特殊编号: {text_lower}")
            return True  # 保留这些特殊编号
        
        if any(text_lower == word for word in common_words):
            if debug_enabled:
                self.logger.debug(f"❌ 是常见描述词: {text_lower}")
            return False
        
        # 积极的指标：包含这些特征的更可能是产品编号
        positive_indicators = 0
        indicators_found = []
        
        # 1. 包含数字 (+2分)
        if any(c.isdigit() for c in text):
            positive_indicators += 2
            indicators_found.append("包含数字(+2)")
        
        # 2. 包含连字符或下划线 (+1分)
        if '-' in text or '_' in text:
            positive_indicators += 1
            indicators_found.append("包含连字符/下划线(+1)")
        
        # 3. 包含大写字母（不是句子开头）(+1分)
        if any(c.isupper() for c in text[1:]):
            positive_indicators += 1
            indicators_found.append("包含大写字母(+1)")
        
        # 4. 长度适中（2-50个字符）(+1分)
        if 2 <= len(text) <= 50:
            positive_indicators += 1
            indicators_found.append("长度适中(+1)")
        
        # 5. 特殊格式模式 (+2分)
        special_patterns = [
            r'^\d+-\d+-\d+$',  # 5-14230-00
            r'^[A-Z]+\d+',     # SLS50, DIN787
            r'^\d+[A-Z]+',     # 14W, 230V
            r'^[A-Z0-9]+[-_][A-Z0-9]+',  # QAAMC10A050S
            r'^[A-Z]{2,}\d{2,}',  # DIN787, EN561
            r'^USC\d+T\d+$',   # USC201T20, USC202T20等NTN产品编号
        ]
        
        for pattern in special_patterns:
            if re.match(pattern, text):
                positive_indicators += 2
                indicators_found.append(f"特殊格式模式(+2): {pattern}")
                break
        
        result = positive_indicators >= 3
        
        if debug_enabled:
            self.logger.debug(f"指标总分: {positive_indicators}")
            self.logger.debug(f"找到指标: {indicators_found}")
            self.logger.debug(f"最终判断: {'✅ 是产品编号' if result else '❌ 不是产品编号'}")
        
        return result
    
    def extract_dimensions_from_cells(self, cells: List[str]) -> str:
        """从单元格中提取尺寸信息"""
        for cell_text in cells:
            dimension_match = re.search(r'\d+x\d+x?\d*', cell_text)
            if dimension_match:
                return dimension_match.group()
        return ''
    
    def extract_weight_from_cells(self, cells: List[str]) -> str:
        """从单元格中提取重量或长度信息"""
        for cell_text in cells:
            measure_match = re.search(r'(\d+[,\.]\d+|\d+)\s*(mm|kg|m|cm)', cell_text.lower())
            if measure_match:
                return measure_match.group()
        return ''
    
    def generate_specification_urls(self, base_product_info: Dict[str, Any], part_number: str) -> List[str]:
        """生成规格URL - 复制test-09-1逻辑"""
        try:
            if not part_number or part_number == 'unknown':
                return []
            
            # 构建查询参数
            query_params = base_product_info.get('query_params', {}).copy()
            
            # 添加PartNumber参数
            query_params['PartNumber'] = [part_number]
            
            # 生成URL列表
            urls = []
            
            # 基础URL
            base_url = f"https://www.traceparts.cn/en/product/{base_product_info['base_product_name']}"
            
            # 构建完整的查询字符串
            query_string = urlencode(query_params, doseq=True)
            full_url = f"{base_url}?{query_string}"
            
            urls.append(full_url)
            
            return urls
            
        except Exception as e:
            self.logger.error(f"URL生成失败: {e}")
            return []

    # ========== 兼容性方法（保持与现有pipeline的接口一致）==========
    
    def detect_page_type(self, url: str, driver) -> str:
        """保留原有的页面类型检测方法，但现在统一使用新逻辑"""
        return "test-09-1-unified"
    
    def _parse_standard_table(self, driver, url: str) -> List[Dict[str, Any]]:
        """保留原有方法名，但使用新逻辑"""
        return self.parse_specifications(driver, url)