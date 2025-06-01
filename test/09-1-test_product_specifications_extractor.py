#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 09-1 —— 产品规格链接提取器 (重新设计版)
一次性加载所有产品规格，无需翻页
运行: make test-09-1
"""
import os, sys, time, re, json
from pathlib import Path
from urllib.parse import urlparse, parse_qs, urlencode

# Selenium imports
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait, Select
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    print("❌ Selenium 未安装，无法运行测试！")
    sys.exit(1)

RESULTS_DIR = Path("results/product_specifications")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# 默认产品URL（可通过环境变量覆盖）
DEFAULT_PRODUCT_URL = "https://www.traceparts.cn/en/product/jlcmc-aluminum-extrusion-txceh161515l100dalka75?Product=90-27122024-029219"
PRODUCT_URL = os.getenv("TRACEPARTS_PRODUCT_URL", DEFAULT_PRODUCT_URL)

def prepare_driver():
    """准备Chrome驱动器"""
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(40)
    return driver

def scroll_page_fully(driver):
    """完整滚动页面确保所有内容加载"""
    print("🔄 滚动页面确保内容完全加载...")
    
    # 先滚动到底部
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)
    
    # 再滚动到顶部
    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(1)
    
    # 最后滚动到页面中部
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
    time.sleep(1)

def set_items_per_page_to_all(driver):
    """设置每页显示项目数为全部"""
    print("🎯 尝试设置每页显示项目数为全部...")
    
    # 首先检查是否存在分页控件
    try:
        # 查找是否有"Items per page"相关文本
        pagination_indicators = [
            "//*[contains(text(), 'Items per page')]",
            "//*[contains(text(), 'items per page')]", 
            "//*[contains(text(), 'out of') and contains(text(), 'items')]",
            "//*[contains(text(), 'Show') and contains(text(), 'entries')]"
        ]
        
        has_pagination = False
        for selector in pagination_indicators:
            try:
                elements = driver.find_elements(By.XPATH, selector)
                if elements and any(elem.is_displayed() for elem in elements):
                    has_pagination = True
                    print(f"  ✅ 检测到分页控件: {elements[0].text.strip()[:50]}...")
                    break
            except:
                continue
        
        if not has_pagination:
            print("  ℹ️ 未检测到分页控件，可能是单页面，直接提取数据")
            return False  # 返回False表示没有分页，但这是正常情况
            
    except Exception as e:
        print(f"  ⚠️ 检测分页控件时出错: {e}")
        return False
    
    # 策略1: 寻找分页区域中的数字和下拉控件
    try:
        print("  🔍 策略1: 查找分页区域的控件...")
        
        # 先查找包含"Items per page"的分页容器
        pagination_selectors = [
            "//*[contains(text(), 'Items per page')]",
            "//*[contains(text(), 'items per page')]",
            "//*[contains(text(), 'per page')]",
            "//*[contains(text(), 'out of') and contains(text(), 'items')]"
        ]
        
        pagination_container = None
        for selector in pagination_selectors:
            try:
                elements = driver.find_elements(By.XPATH, selector)
                if elements:
                    # 获取包含分页信息的最外层容器
                    for elem in elements:
                        # 查找父容器
                        for level in range(1, 4):  # 向上查找3层
                            try:
                                container = elem.find_element(By.XPATH, f"./ancestor::*[{level}]")
                                container_text = container.text.lower()
                                if 'items per page' in container_text or 'out of' in container_text:
                                    pagination_container = container
                                    print(f"    找到分页容器，文本: {container.text[:100]}...")
                                    break
                            except:
                                continue
                        if pagination_container:
                            break
                if pagination_container:
                    break
            except:
                continue
        
        if pagination_container:
            # 在分页容器中查找所有可点击的数字
            print("    在分页容器中查找可点击数字...")
            clickable_selectors = [
                ".//select",
                ".//button[text()]",
                ".//a[text()]", 
                ".//*[@role='button']",
                ".//*[contains(@class,'select')]",
                ".//*[contains(@class,'dropdown')]",
                ".//*[contains(@onclick,'')]",
                ".//*[text()='10']",
                ".//*[text()='25']",
                ".//*[text()='50']"
            ]
            
            for selector in clickable_selectors:
                try:
                    elements = pagination_container.find_elements(By.XPATH, selector)
                    for elem in elements:
                        elem_text = elem.text.strip()
                        elem_tag = elem.tag_name
                        
                        print(f"      找到可点击元素: {elem_tag} '{elem_text}'")
                        
                        # 如果是select，检查选项
                        if elem_tag == 'select':
                            options = elem.find_elements(By.TAG_NAME, 'option')
                            option_texts = [opt.text.strip() for opt in options]
                            print(f"        选项: {option_texts}")
                            
                            # 查找All或大数字选项
                            for opt in options:
                                text = opt.text.strip().lower()
                                if text in ['all', '全部'] or (text.isdigit() and int(text) >= 50):
                                    print(f"        ✅ 选择: {opt.text}")
                                    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", opt)
                                    time.sleep(1)
                                    opt.click()
                                    time.sleep(5)
                                    return True
                        
                        # 如果是数字文本且可点击，尝试点击
                        elif elem.is_displayed() and elem.is_enabled():
                            if elem_text.isdigit() or elem_text.lower() in ['all', '全部']:
                                try:
                                    print(f"        🖱️ 尝试点击: {elem_text}")
                                    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", elem)
                                    time.sleep(1)
                                    elem.click()
                                    time.sleep(3)
                                    
                                    # 🎯 关键改进：明确查找并点击"All"选项
                                    print(f"        🔍 查找弹出菜单中的All选项...")
                                    all_found = False
                                    
                                    # 更全面的All选项查找
                                    all_selectors = [
                                        "//li[normalize-space(.)='All']",
                                        "//div[normalize-space(.)='All']",
                                        "//option[normalize-space(.)='All']",
                                        "//span[normalize-space(.)='All']",
                                        "//button[normalize-space(.)='All']",
                                        "//a[normalize-space(.)='All']",
                                        "//*[@role='option'][normalize-space(.)='All']",
                                        "//*[contains(@class,'option')][normalize-space(.)='All']",
                                        "//*[contains(@class,'menu-item')][normalize-space(.)='All']",
                                        "//li[text()='All']",
                                        "//li[normalize-space(.)='全部']"
                                    ]
                                    
                                    for all_sel in all_selectors:
                                        try:
                                            all_options = driver.find_elements(By.XPATH, all_sel)
                                            for all_option in all_options:
                                                if all_option.is_displayed() and all_option.is_enabled():
                                                    print(f"        ✅ 找到All选项: {all_option.text} ({all_option.tag_name})")
                                                    all_option.click()
                                                    print(f"        ✅ 成功选择All选项！")
                                                    time.sleep(5)
                                                    all_found = True
                                                    return True
                                        except Exception as e:
                                            continue
                                    
                                    if not all_found:
                                        # 如果没找到All，尝试找最大数字
                                        print(f"        🔍 未找到All，查找最大数字选项...")
                                        max_selectors = [
                                            "//li[text()='100']",
                                            "//li[text()='50']", 
                                            "//li[text()='25']",
                                            "//option[text()='100']",
                                            "//option[text()='50']"
                                        ]
                                        
                                        for max_sel in max_selectors:
                                            try:
                                                max_options = driver.find_elements(By.XPATH, max_sel)
                                                for max_option in max_options:
                                                    if max_option.is_displayed():
                                                        print(f"        ✅ 选择最大数字: {max_option.text}")
                                                        max_option.click()
                                                        time.sleep(5)
                                                        return True
                                            except:
                                                continue
                                        
                                        print(f"        ⚠️ 点击后未找到合适的选项")
                                    
                                except Exception as e:
                                    print(f"        ❌ 点击失败: {e}")
                                    
                except Exception as e:
                    print(f"      查找元素失败: {e}")
                    
    except Exception as e:
        print(f"  ❌ 策略1失败: {e}")
    
    # 策略2: 更直接的查找方式 - 查找包含当前页数"10"的可点击元素
    try:
        print("  🔍 策略2: 查找当前页数控件...")
        
        # 查找显示"10"的可点击元素 (当前每页显示数量)
        number_selectors = [
            "//select[option[text()='10']]",
            "//*[text()='10' and (@onclick or @role='button' or contains(@class,'select') or contains(@class,'dropdown'))]",
            "//button[text()='10']",
            "//a[text()='10']",
            "//*[@data-value='10']",
            "//*[contains(@class,'pagesize') or contains(@class,'page-size')]"
        ]
        
        for selector in number_selectors:
            try:
                elements = driver.find_elements(By.XPATH, selector)
                for elem in elements:
                    if elem.is_displayed():
                        elem_tag = elem.tag_name
                        elem_text = elem.text.strip()
                        elem_class = elem.get_attribute('class') or ''
                        
                        print(f"    找到数字控件: {elem_tag} '{elem_text}' class='{elem_class}'")
                        
                        if elem_tag == 'select':
                            # 如果是select，查找All选项
                            options = elem.find_elements(By.TAG_NAME, 'option')
                            for opt in options:
                                if opt.text.strip().lower() in ['all', '全部'] or (opt.text.strip().isdigit() and int(opt.text.strip()) >= 50):
                                    print(f"    ✅ 在select中选择: {opt.text}")
                                    opt.click()
                                    time.sleep(5)
                                    return True
                        else:
                            # 如果是可点击元素，尝试点击
                            try:
                                print(f"    🖱️ 点击数字控件: {elem_text}")
                                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", elem)
                                time.sleep(1)
                                elem.click()
                                time.sleep(3)
                                
                                # 查找弹出菜单中的All选项
                                all_options = driver.find_elements(By.XPATH, "//li[normalize-space(.)='All'] | //option[normalize-space(.)='All'] | //*[@role='option'][normalize-space(.)='All']")
                                for opt in all_options:
                                    if opt.is_displayed():
                                        opt.click()
                                        print(f"    ✅ 选择了All选项")
                                        time.sleep(5)
                                        return True
                                        
                            except Exception as e:
                                print(f"    ❌ 点击数字控件失败: {e}")
                                
            except Exception as e:
                print(f"    查找数字控件失败: {e}")
                
    except Exception as e:
        print(f"  ❌ 策略2失败: {e}")
    
    # 策略3: 查找所有select元素，专门寻找包含数字选项的
    try:
        print("  🔍 策略3: 检查所有select元素...")
        
        select_elements = driver.find_elements(By.TAG_NAME, 'select')
        print(f"    页面共有 {len(select_elements)} 个select元素")
        
        for i, select_elem in enumerate(select_elements):
            try:
                if not select_elem.is_displayed():
                    continue
                    
                options = select_elem.find_elements(By.TAG_NAME, 'option')
                option_data = []
                has_numbers = False
                
                for opt in options:
                    text = opt.text.strip()
                    value = opt.get_attribute('value')
                    option_data.append(f"{text}({value})")
                    
                    # 检查是否有数字选项（分页相关）
                    if text.isdigit() and int(text) <= 100:
                        has_numbers = True
                
                print(f"    Select {i+1}: 包含数字={has_numbers}")
                if len(option_data) <= 10:  # 只显示选项少的select
                    print(f"      选项: {option_data}")
                
                # 如果包含数字选项，可能是分页控件
                if has_numbers:
                    print(f"    🎯 这可能是分页控件，尝试选择最大值...")
                    
                    # 查找All或最大数字
                    best_option = None
                    for opt in options:
                        text = opt.text.strip().lower()
                        if text in ['all', '全部']:
                            best_option = opt
                            break
                        elif text.isdigit() and int(text) >= 50:
                            best_option = opt
                    
                    if best_option:
                        print(f"      ✅ 选择: {best_option.text}")
                        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", best_option)
                        time.sleep(1)
                        best_option.click()
                        time.sleep(5)
                        return True
                        
            except Exception as e:
                print(f"    处理select {i+1}失败: {e}")
                
    except Exception as e:
        print(f"  ❌ 策略3失败: {e}")
    
    print("  ❌ 所有策略都未能找到可用的分页控件")
    return False

def extract_all_product_specifications(driver):
    """一次性提取所有产品规格"""
    print("📋 开始提取所有产品规格...")
    
    specifications = []
    seen_references = set()
    
    try:
        # 等待页面稳定
        time.sleep(3)
        
        # 完整滚动页面
        scroll_page_fully(driver)
        
        # 查找表格
        print("🔍 查找产品规格表格...")
        tables = driver.find_elements(By.TAG_NAME, 'table')
        
        if not tables:
            print("❌ 未找到任何表格")
            return specifications
        
        # 选择最大的表格
        best_table = max(tables, key=lambda t: len(t.find_elements(By.TAG_NAME, 'tr')))
        rows = best_table.find_elements(By.TAG_NAME, 'tr')
        
        print(f"📊 找到最佳表格，共 {len(rows)} 行")
        
        # 分析表格结构
        header_row = None
        data_rows = []
        
        for i, row in enumerate(rows):
            cells = row.find_elements(By.CSS_SELECTOR, 'td, th')
            if not cells:
                continue
                
            cell_texts = [cell.text.strip() for cell in cells]
            
            # 判断是否为表头行
            is_header = any(keyword in ' '.join(cell_texts).lower() for keyword in [
                'part number', 'product', 'reference', 'model', 'specification'
            ])
            
            if is_header and header_row is None:
                header_row = i
                print(f"  📋 识别表头行 {i+1}: {cell_texts[:3]}...")
            elif not is_header and len(cell_texts) > 1:
                data_rows.append({'index': i, 'cells': cell_texts})
        
        print(f"  📊 识别出 {len(data_rows)} 行数据")
        
        # 提取产品规格
        for row_info in data_rows:
            row_index = row_info['index']
            cells = row_info['cells']
            
            # 查找产品编号
            found_reference = None
            for cell_text in cells:
                if is_valid_product_reference(cell_text) and cell_text not in seen_references:
                    found_reference = cell_text
                    break
            
            if found_reference:
                spec_info = {
                    'reference': found_reference,
                    'row_index': row_index,
                    'dimensions': extract_dimensions_from_cells(cells),
                    'weight': extract_weight_from_cells(cells),
                    'all_cells': cells
                }
                
                specifications.append(spec_info)
                seen_references.add(found_reference)
                
                if len(specifications) <= 10:  # 只显示前10个
                    print(f"  📦 规格 {len(specifications)}: {found_reference} ({spec_info['dimensions']})")
        
        if len(specifications) > 10:
            print(f"  ... 还有 {len(specifications) - 10} 个规格")
            
    except Exception as e:
        print(f"❌ 提取规格时出错: {e}")
    
    print(f"✅ 总共提取到 {len(specifications)} 个产品规格")
    return specifications

def is_valid_product_reference(text):
    """判断文本是否是有效的产品编号"""
    if not text or len(text) < 5:
        return False
    
    # 排除明显的产品描述
    if any(desc_word in text.lower() for desc_word in [
        'aluminum', 'extrusion', 'description', 'purchasing', 'links', 
        'manufacturer', 'jlcmc', 'product page'
    ]):
        return False
    
    # 必须包含TXCE-开头的产品编号模式
    if not re.search(r'^TXCE-[A-Z0-9]+-[0-9]+-[0-9]+-L[0-9]', text):
        return False
    
    # 进一步验证：必须有字母和数字
    if not (any(char.isalpha() for char in text) and any(char.isdigit() for char in text)):
        return False
    
    # 排除过长的文本（可能是描述）
    if len(text) > 50:
        return False
        
    return True

def extract_dimensions_from_cells(cells):
    """从单元格中提取尺寸信息"""
    for cell_text in cells:
        dimension_match = re.search(r'\d+x\d+x?\d*', cell_text)
        if dimension_match:
            return dimension_match.group()
    return ''

def extract_weight_from_cells(cells):
    """从单元格中提取重量或长度信息"""
    for cell_text in cells:
        measure_match = re.search(r'(\d+[,\.]\d+|\d+)\s*(mm|kg|m|cm)', cell_text.lower())
        if measure_match:
            return measure_match.group()
    return ''

def extract_base_product_info(product_url):
    """从产品URL中提取基础信息"""
    try:
        parsed_url = urlparse(product_url)
        path_parts = parsed_url.path.split('/')
        
        # 获取基础产品名称
        base_product_name = path_parts[-1] if path_parts else "unknown-product"
        
        # 解析查询参数
        query_params = parse_qs(parsed_url.query)
        product_id = query_params.get('Product', ['unknown-id'])[0]
        catalog_path = query_params.get('CatalogPath', ['unknown-catalog'])[0] if 'CatalogPath' in query_params else 'unknown-catalog'
        
        return {
            'base_url': f"{parsed_url.scheme}://{parsed_url.netloc}",
            'base_path': parsed_url.path,
            'base_product_name': base_product_name,
            'product_id': product_id,
            'catalog_path': catalog_path,
            'query_params': query_params
        }
    except Exception as e:
        print(f"⚠️ 解析产品URL失败: {e}")
        return None

def generate_specification_urls(base_info, specifications):
    """根据基础信息和规格生成特定的产品URL"""
    print("🔗 生成规格专用链接...")
    
    if not base_info:
        print("❌ 缺少基础产品信息")
        return []
    
    spec_urls = []
    
    for spec in specifications:
        try:
            reference = spec.get('reference', '')
            if not reference:
                continue
            
            # 构建查询参数
            query_params = base_info['query_params'].copy()
            query_params['PartNumber'] = [reference]
            
            # 重新编码查询字符串
            query_string = urlencode(query_params, doseq=True)
            
            # 构建完整URL
            spec_url = f"{base_info['base_url']}{base_info['base_path']}?{query_string}"
            
            spec_url_info = {
                'reference': reference,
                'dimensions': spec.get('dimensions', ''),
                'weight': spec.get('weight', ''),
                'url': spec_url,
                'original_spec_data': spec
            }
            
            spec_urls.append(spec_url_info)
            
        except Exception as e:
            print(f"⚠️ 生成规格URL时出错 ({reference}): {e}")
    
    print(f"  ✅ 成功生成 {len(spec_urls)} 个规格链接")
    return spec_urls

def save_results(base_info, specifications, spec_urls):
    """保存提取结果"""
    timestamp = int(time.time())
    
    # 🎯 改进的JSON格式
    results = {
        'extraction_info': {
            'timestamp': timestamp,
            'extraction_time': time.strftime('%Y-%m-%d %H:%M:%S'),
            'base_product_url': PRODUCT_URL,
            'total_specifications_found': len(specifications),
            'total_urls_generated': len(spec_urls)
        },
        'base_product_info': base_info,
        'product_specifications': specifications,
        'specification_urls': spec_urls,
        'summary': {
            'series_distribution': {},
            'specification_samples': []
        }
    }
    
    # 分析产品系列分布
    series_stats = {}
    for spec in specifications:
        ref = spec.get('reference', '')
        if ref.startswith('TXCE-'):
            # 提取产品系列
            series_match = re.match(r'(TXCE-[A-Z0-9]+-[0-9]+-[0-9]+)', ref)
            if series_match:
                series = series_match.group(1)
                if series not in series_stats:
                    series_stats[series] = 0
                series_stats[series] += 1
    
    results['summary']['series_distribution'] = series_stats
    
    # 添加规格样本（前10个）
    for i, spec in enumerate(specifications[:10]):
        sample = {
            'index': i + 1,
            'reference': spec.get('reference', ''),
            'dimensions': spec.get('dimensions', ''),
            'weight': spec.get('weight', ''),
            'url': spec_urls[i]['url'] if i < len(spec_urls) else ''
        }
        results['summary']['specification_samples'].append(sample)
    
    # 保存详细JSON结果
    json_file = RESULTS_DIR / f"product_specs_complete_{timestamp}.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"💾 完整结果已保存到: {json_file}")
    
    # 保存简化的规格列表JSON
    simple_specs = []
    for i, spec in enumerate(specifications):
        simple_spec = {
            'id': i + 1,
            'reference': spec.get('reference', ''),
            'dimensions': spec.get('dimensions', ''),
            'weight': spec.get('weight', ''),
            'series': '',
            'url': spec_urls[i]['url'] if i < len(spec_urls) else ''
        }
        
        # 提取系列信息
        ref = spec.get('reference', '')
        if ref.startswith('TXCE-'):
            series_match = re.match(r'(TXCE-[A-Z0-9]+-[0-9]+-[0-9]+)', ref)
            if series_match:
                simple_spec['series'] = series_match.group(1)
        
        simple_specs.append(simple_spec)
    
    simple_json_file = RESULTS_DIR / f"specs_list_{timestamp}.json"
    with open(simple_json_file, 'w', encoding='utf-8') as f:
        json.dump({
            'extraction_time': time.strftime('%Y-%m-%d %H:%M:%S'),
            'total_count': len(simple_specs),
            'specifications': simple_specs
        }, f, indent=2, ensure_ascii=False)
    print(f"📋 简化规格列表已保存到: {simple_json_file}")
    
    # 保存简化的URL列表
    urls_file = RESULTS_DIR / f"spec_urls_{timestamp}.txt"
    with open(urls_file, 'w', encoding='utf-8') as f:
        f.write(f"# 产品规格链接列表\n")
        f.write(f"# 基础产品: {PRODUCT_URL}\n")
        f.write(f"# 生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"# 找到 {len(spec_urls)} 个规格\n\n")
        
        for spec_url_info in spec_urls:
            f.write(f"# {spec_url_info['reference']} ({spec_url_info['dimensions']})\n")
            f.write(f"{spec_url_info['url']}\n\n")
    
    print(f"📄 URL列表已保存到: {urls_file}")
    
    # 输出结果摘要
    print("\n" + "="*80)
    print("📋 提取结果摘要")
    print("="*80)
    print(f"基础产品URL: {PRODUCT_URL}")
    print(f"找到规格数量: {len(specifications)}")
    print(f"生成链接数量: {len(spec_urls)}")
    
    if series_stats:
        print(f"\n📊 产品系列分布:")
        for series, count in sorted(series_stats.items()):
            print(f"  {series}: {count} 个规格")
    
    print("\n🔗 规格链接列表 (显示前10个):")
    for i, spec_url_info in enumerate(spec_urls[:10], 1):
        print(f"{i:2d}. {spec_url_info['reference']} ({spec_url_info['dimensions']})")
        print(f"    {spec_url_info['url']}")
    if len(spec_urls) > 10:
        print(f"... 还有 {len(spec_urls) - 10} 个链接")
    
    print(f"\n💾 文件输出:")
    print(f"  📋 完整JSON: {json_file.name}")
    print(f"  📋 简化JSON: {simple_json_file.name}")
    print(f"  📄 URL列表: {urls_file.name}")
    print("="*80)

def main():
    print("🎯 产品规格链接提取器 (重新设计版)")
    print(f"📍 目标产品: {PRODUCT_URL}")
    print("🔄 策略: 一次性加载所有数据，无翻页")
    
    if not SELENIUM_AVAILABLE:
        print("❌ Selenium 未安装，无法运行！")
        return False
    
    # 提取基础产品信息
    base_info = extract_base_product_info(PRODUCT_URL)
    if not base_info:
        print("❌ 无法解析基础产品信息")
        return False
    
    print(f"📦 产品ID: {base_info['product_id']}")
    
    driver = prepare_driver()
    
    try:
        # 访问产品页面
        print(f"🌐 访问产品页面...")
        driver.get(PRODUCT_URL)
        time.sleep(3)
        
        # 截图保存初始状态
        screenshot_path = RESULTS_DIR / f"initial_page_{int(time.time())}.png"
        driver.save_screenshot(str(screenshot_path))
        print(f"📸 初始页面截图: {screenshot_path}")
        
        # 尝试设置每页显示为全部
        items_per_page_success = set_items_per_page_to_all(driver)
        
        if items_per_page_success:
            print("✅ 成功设置显示全部项目")
            # 再次截图确认
            final_screenshot = RESULTS_DIR / f"after_show_all_{int(time.time())}.png"
            driver.save_screenshot(str(final_screenshot))
            print(f"📸 设置后截图: {final_screenshot}")
        else:
            print("⚠️ 未能设置显示全部，将尝试提取当前页面数据")
        
        # 确保页面完全加载
        scroll_page_fully(driver)
        
        # 提取所有规格信息
        specifications = extract_all_product_specifications(driver)
        
        if not specifications:
            print("❌ 未找到任何产品规格")
            return False
        
        # 生成规格URL
        spec_urls = generate_specification_urls(base_info, specifications)
        
        if not spec_urls:
            print("❌ 未能生成任何规格URL")
            return False
        
        # 保存结果
        save_results(base_info, specifications, spec_urls)
        
        print("✅ 规格链接提取完成！")
        return True
        
    except Exception as e:
        print(f"❌ 提取过程中发生错误: {e}")
        return False
    finally:
        driver.quit()

if __name__ == '__main__':
    success = main()
    print("✅ test-09-1 成功" if success else "❌ test-09-1 失败") 