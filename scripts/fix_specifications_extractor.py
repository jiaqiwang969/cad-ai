#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
规格提取器修复脚本
专门解决文本内容获取失败的问题
"""

import sys
sys.path.append('.')

import time
import json
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 测试URL
TEST_URL = "https://www.traceparts.cn/en/product/ntn-europe-usc200t20-cartridge-unit-from-grey-cast-high-temperature?CatalogPath=TRACEPARTS%3ATP01002002006&Product=34-17112021-055894"

def create_enhanced_driver():
    """创建增强版浏览器驱动"""
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    
    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(10)
    return driver

def wait_for_content_loaded(driver, timeout=30):
    """等待页面内容完全加载"""
    logger.info("⏳ 等待页面内容加载...")
    
    # 等待表格出现
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.TAG_NAME, 'table'))
        )
        logger.info("✅ 表格元素已加载")
    except TimeoutException:
        logger.warning("⚠️ 未检测到表格元素")
    
    # 额外等待动态内容
    time.sleep(5)
    
    # 滚动页面确保内容完全展示
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)
    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(2)

def get_cell_text_enhanced(cell_element):
    """增强版文本获取函数"""
    # 方法1: 标准 text 属性
    text = cell_element.text.strip()
    if text:
        return text
    
    # 方法2: textContent 属性
    text = cell_element.get_attribute('textContent')
    if text and text.strip():
        return text.strip()
    
    # 方法3: innerText 属性
    text = cell_element.get_attribute('innerText')
    if text and text.strip():
        return text.strip()
    
    # 方法4: innerHTML 并提取纯文本
    html = cell_element.get_attribute('innerHTML')
    if html:
        # 简单的HTML标签去除
        import re
        text = re.sub(r'<[^>]+>', '', html).strip()
        if text:
            return text
    
    # 方法5: 子元素文本
    try:
        child_elements = cell_element.find_elements(By.XPATH, './/*')
        texts = []
        for child in child_elements:
            child_text = child.text.strip()
            if child_text:
                texts.append(child_text)
        if texts:
            return ' '.join(texts)
    except:
        pass
    
    return ''

def find_all_tables_enhanced(driver):
    """增强版表格查找"""
    logger.info("🔍 查找页面中的所有表格...")
    
    tables_info = []
    
    # 查找所有表格
    tables = driver.find_elements(By.TAG_NAME, 'table')
    logger.info(f"📊 找到 {len(tables)} 个表格")
    
    for i, table in enumerate(tables):
        try:
            rows = table.find_elements(By.TAG_NAME, 'tr')
            if not rows:
                continue
                
            # 分析表格内容
            non_empty_rows = 0
            total_cells = 0
            sample_texts = []
            
            for row in rows[:5]:  # 只检查前5行
                cells = row.find_elements(By.CSS_SELECTOR, 'td, th')
                if cells:
                    total_cells += len(cells)
                    row_texts = []
                    for cell in cells:
                        cell_text = get_cell_text_enhanced(cell)
                        if cell_text:
                            row_texts.append(cell_text)
                    
                    if row_texts:
                        non_empty_rows += 1
                        sample_texts.extend(row_texts[:3])  # 取前3个单元格文本
            
            table_info = {
                'index': i,
                'rows_count': len(rows),
                'non_empty_rows': non_empty_rows,
                'total_cells': total_cells,
                'sample_texts': sample_texts[:10],  # 最多10个样本
                'element': table
            }
            
            tables_info.append(table_info)
            
            logger.info(f"  表格 {i+1}: {len(rows)} 行, {non_empty_rows} 行有内容, 样本: {sample_texts[:3]}")
            
        except Exception as e:
            logger.warning(f"  表格 {i+1} 分析失败: {e}")
    
    return tables_info

def extract_specifications_enhanced(driver):
    """增强版规格提取"""
    logger.info("🚀 开始增强版规格提取...")
    
    # 等待内容加载
    wait_for_content_loaded(driver)
    
    # 查找所有表格
    tables_info = find_all_tables_enhanced(driver)
    
    if not tables_info:
        logger.error("❌ 未找到任何表格")
        return []
    
    # 选择最有希望的表格（有内容的最大表格）
    best_table = max(tables_info, key=lambda t: t['non_empty_rows'] * t['rows_count'])
    logger.info(f"🎯 选择表格 {best_table['index']+1} 进行详细分析")
    
    table_element = best_table['element']
    rows = table_element.find_elements(By.TAG_NAME, 'tr')
    
    logger.info(f"📊 详细分析表格，共 {len(rows)} 行")
    
    specifications = []
    seen_references = set()
    
    # 逐行分析
    for i, row in enumerate(rows):
        try:
            cells = row.find_elements(By.CSS_SELECTOR, 'td, th')
            if not cells:
                continue
            
            # 使用增强版文本提取
            cell_texts = []
            for cell in cells:
                text = get_cell_text_enhanced(cell)
                cell_texts.append(text)
            
            # 显示行内容（调试用）
            if cell_texts and any(cell_texts):
                logger.info(f"  行 {i+1}: {cell_texts[:5]}...")
                
                # 检查是否包含产品编号
                for j, cell_text in enumerate(cell_texts):
                    if (cell_text and len(cell_text) >= 3 and 
                        cell_text not in seen_references and
                        is_likely_product_reference_enhanced(cell_text)):
                        
                        spec_info = {
                            'reference': cell_text,
                            'row_index': i,
                            'column_index': j,
                            'all_cells': cell_texts,
                            'extraction_method': 'enhanced'
                        }
                        
                        specifications.append(spec_info)
                        seen_references.add(cell_text)
                        logger.info(f"  📦 找到规格: {cell_text}")
                        
                        # 每行只取第一个规格
                        break
            else:
                logger.debug(f"  行 {i+1}: 空行或无内容")
                
        except Exception as e:
            logger.warning(f"  行 {i+1} 处理失败: {e}")
    
    logger.info(f"✅ 总共提取到 {len(specifications)} 个规格")
    return specifications

def is_likely_product_reference_enhanced(text):
    """增强版产品编号判断"""
    if not text or len(text) < 3:
        return False
    
    # 排除明显的非产品编号
    exclude_patterns = [
        r'^https?://',  # URL
        r'^www\.',      # 网址
        r'@',           # 邮箱
        r'^\d{4}-\d{2}-\d{2}',  # 日期
        r'^\+?\d{10,}$',  # 电话
        r'^[\s\-_]*$',  # 只有空格和符号
    ]
    
    import re
    for pattern in exclude_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return False
    
    # 排除常见描述词
    common_words = [
        'description', 'manufacturer', 'material', 'color', 'size',
        'weight', 'length', 'width', 'height', 'diameter', 'thickness',
        'please', 'select', 'bearing', 'unit', 'assembly', 'component',
        'parts', 'mounted', 'not', 'items', 'per', 'page', 'documentation',
        'contact', 'supplier', 'disclaimer', 'liability'
    ]
    
    text_lower = text.lower()
    if text_lower in common_words:
        return False
    
    # 积极指标
    positive_score = 0
    
    # 包含数字
    if any(c.isdigit() for c in text):
        positive_score += 2
    
    # 包含连字符
    if '-' in text or '_' in text:
        positive_score += 1
    
    # 包含大写字母（除第一个）
    if any(c.isupper() for c in text[1:]):
        positive_score += 1
    
    # 长度合适
    if 3 <= len(text) <= 50:
        positive_score += 1
    
    # 特殊模式
    special_patterns = [
        r'^\w+-\w+-\w+$',  # ABC-123-DEF
        r'^[A-Z]+\d+',     # SLS50
        r'^\d+[A-Z]+',     # 200T20
        r'^[A-Z0-9]+[-_][A-Z0-9]+',  # USC200T20
        r'^[A-Z]{2,}\d{2,}',  # USC200
    ]
    
    for pattern in special_patterns:
        if re.match(pattern, text):
            positive_score += 3
            break
    
    return positive_score >= 3

def test_enhanced_extraction():
    """测试增强版提取功能"""
    logger.info("🧪 测试增强版规格提取")
    logger.info(f"📍 目标URL: {TEST_URL}")
    
    driver = None
    try:
        driver = create_enhanced_driver()
        
        # 访问页面
        logger.info("🌐 访问目标页面...")
        driver.get(TEST_URL)
        
        # 提取规格
        specifications = extract_specifications_enhanced(driver)
        
        # 保存结果
        if specifications:
            timestamp = int(time.time())
            results = {
                'test_url': TEST_URL,
                'extraction_time': time.strftime('%Y-%m-%d %H:%M:%S'),
                'specifications_count': len(specifications),
                'specifications': specifications
            }
            
            # 保存到文件
            results_dir = Path("results/debug")
            results_dir.mkdir(parents=True, exist_ok=True)
            
            results_file = results_dir / f"enhanced_extraction_{timestamp}.json"
            with open(results_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            
            logger.info(f"💾 结果已保存: {results_file}")
            
            # 显示结果摘要
            logger.info("\n" + "="*60)
            logger.info("📋 提取结果摘要")
            logger.info("="*60)
            logger.info(f"✅ 成功提取 {len(specifications)} 个规格")
            
            for i, spec in enumerate(specifications[:10], 1):
                logger.info(f"{i:2d}. {spec['reference']}")
            
            if len(specifications) > 10:
                logger.info(f"... 还有 {len(specifications) - 10} 个规格")
        else:
            logger.error("❌ 未提取到任何规格")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if driver:
            driver.quit()

if __name__ == '__main__':
    success = test_enhanced_extraction()
    if success:
        logger.info("✅ 增强版提取测试成功")
    else:
        logger.error("❌ 增强版提取测试失败") 