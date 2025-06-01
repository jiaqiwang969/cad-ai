#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 10 —— 终极自动 CAD 下载脚本
依赖 utils/captcha_solver (GPT-4o OCR) + 11i 隐身浏览器。
运行: make test-10
"""
import os, sys, time, re
from pathlib import Path
from playwright.sync_api import sync_playwright
import importlib.util
from urllib.parse import urlparse, parse_qs

# 导入工具
sys.path.append(str(Path(__file__).parent.parent))
from utils.captcha_solver import CaptchaSolver

CAP_DIR = Path("results/captcha_samples") # 实际截图由 solver 的 debug 控制
CAP_DIR.mkdir(parents=True, exist_ok=True)

# PRODUCT_URL = os.getenv("TRACEPARTS_PRODUCT_URL", "https://www.traceparts.cn/en/product/rs-pro-abs-plastic-sheet-stock1220x610x15mm?CatalogPath=TRACEPARTS%3ATP05009&Product=90-03062024-057087")
PRODUCT_URL = os.getenv("TRACEPARTS_PRODUCT_URL", "https://www.traceparts.cn/en/product/emile-maurin-a37-etce-acier-de-construction-non-allie-a37-etire-a-froid-corniere-egale?CatalogPath=TRACEPARTS%3ATP05001&Product=10-14012020-079962")
preferred_formats = ["STEP AP214", "STEP AP203", "STL", "IGES", "SOLIDWORKS", "Parasolid"]

# --------- 动态加载 stealth11i 模块 ---------
BASE_DIR = Path(__file__).parent
# 使用 legacy 目录中的 11i-stealth_cad_downloader.py
path_to_11i = BASE_DIR / "legacy" / "11i-stealth_cad_downloader.py"
if not path_to_11i.exists():
    print(f"❌ Critical: 11i-stealth_cad_downloader.py not found at expected location: {path_to_11i}")
    sys.exit(1)

MOD11 = importlib.util.spec_from_file_location(
    "stealth11i", path_to_11i)
stealth11i = importlib.util.module_from_spec(MOD11)  # type: ignore
MOD11.loader.exec_module(stealth11i)  # type: ignore

# 登录账号
EMAIL = os.getenv("TRACEPARTS_EMAIL", "demo@example.com")
PASSWORD = os.getenv("TRACEPARTS_PASSWORD", "pass")

def extract_product_info(product_url):
    """从产品URL中提取产品信息"""
    try:
        parsed_url = urlparse(product_url)
        path_parts = parsed_url.path.split('/')
        
        # 提取产品名称（URL路径的最后一部分）
        product_name = path_parts[-1] if path_parts else "unknown-product"
        
        # 解析查询参数
        query_params = parse_qs(parsed_url.query)
        product_id = query_params.get('Product', ['unknown-id'])[0]
        catalog_path = query_params.get('CatalogPath', ['unknown-catalog'])[0]
        
        # 清理产品名称，限制长度
        clean_name = re.sub(r'[^\w\-]', '', product_name)[:50]
        
        return {
            'product_name': clean_name,
            'product_id': product_id,
            'catalog_path': catalog_path,
            'short_id': product_id.split('-')[-1] if '-' in product_id else product_id
        }
    except Exception as e:
        print(f"⚠️ 解析产品URL失败: {e}")
        return {
            'product_name': 'unknown-product',
            'product_id': 'unknown-id',
            'catalog_path': 'unknown-catalog',
            'short_id': 'unknown'
        }

def get_selected_specification(page):
    """获取当前选择的产品规格信息"""
    spec_info = {
        'dimensions': '',
        'material': '',
        'selected_row': '',
        'format': ''
    }
    
    try:
        print("🔍 获取选择的产品规格信息...")
        
        # 尝试获取选择的格式
        format_selectors = [
            'select option:checked',
            '.selected-format',
            '[class*="format"] .selected',
            'button[class*="selected"]'
        ]
        
        for selector in format_selectors:
            element = page.query_selector(selector)
            if element:
                format_text = element.text_content() or ''
                if any(fmt.lower() in format_text.lower() for fmt in preferred_formats):
                    spec_info['format'] = format_text.strip()
                    print(f"📋 检测到选择格式: {spec_info['format']}")
                    break
        
        # 尝试获取产品选择表格中的选中行
        table_selectors = [
            'tr.selected',
            'tr[class*="selected"]',
            'tr[class*="highlight"]',
            'tr[style*="background"]',
            '.product-selection tr.selected',
            'tbody tr.selected'
        ]
        
        for selector in table_selectors:
            rows = page.query_selector_all(selector)
            if rows:
                for row in rows:
                    try:
                        cells = row.query_selector_all('td')
                        if cells and len(cells) >= 2:
                            # 获取尺寸信息（通常在前几列）
                            dimensions = []
                            for i, cell in enumerate(cells[:4]):  # 只取前4列
                                text = (cell.text_content() or '').strip()
                                if text and text not in ['', '-', '—']:
                                    dimensions.append(text)
                            
                            spec_info['dimensions'] = 'x'.join(dimensions)
                            spec_info['selected_row'] = ' '.join(dimensions)
                            print(f"📏 检测到选择规格: {spec_info['dimensions']}")
                            break
                    except Exception as e_cell:
                        print(f"⚠️ 解析表格行失败: {e_cell}")
        
        # 如果没有找到选中行，尝试获取突出显示的行
        if not spec_info['dimensions']:
            try:
                # 查找包含数字和x的单元格（可能是尺寸信息）
                dimension_cells = page.query_selector_all('td:has-text("x"), td:has-text("×")')
                for cell in dimension_cells[:3]:  # 只检查前3个
                    text = (cell.text_content() or '').strip()
                    if 'x' in text and any(c.isdigit() for c in text):
                        spec_info['dimensions'] = text
                        print(f"📏 通过模糊匹配找到规格: {text}")
                        break
            except Exception as e_fuzzy:
                print(f"⚠️ 模糊匹配规格失败: {e_fuzzy}")
        
        # 尝试获取材料信息
        material_selectors = [
            '.material-info',
            '[class*="material"]',
            'h1, h2, h3',  # 产品标题可能包含材料信息
        ]
        
        for selector in material_selectors:
            elements = page.query_selector_all(selector)
            for element in elements:
                text = (element.text_content() or '').strip()
                if text and len(text) < 100:  # 避免过长的文本
                    if any(keyword in text.lower() for keyword in ['steel', 'aluminum', 'plastic', 'acier', '钢', '铝']):
                        spec_info['material'] = text[:30]  # 限制长度
                        break
    
    except Exception as e:
        print(f"⚠️ 获取规格信息时出错: {e}")
    
    print(f"📋 最终规格信息: {spec_info}")
    return spec_info

def generate_download_filename(product_info, spec_info, original_filename):
    """生成规范的下载文件名"""
    try:
        # 获取文件扩展名
        file_ext = Path(original_filename).suffix or '.step'
        
        # 构建文件名组件
        components = []
        
        # 1. 产品短ID
        if product_info['short_id'] and product_info['short_id'] != 'unknown':
            components.append(f"ID{product_info['short_id']}")
        
        # 2. 产品名称（简化）
        if product_info['product_name'] and product_info['product_name'] != 'unknown-product':
            # 提取产品名称的关键部分
            name_parts = product_info['product_name'].split('-')
            key_parts = []
            for part in name_parts[:3]:  # 只取前3个部分
                if len(part) > 2:  # 过滤掉太短的部分
                    key_parts.append(part)
            if key_parts:
                components.append('-'.join(key_parts)[:20])  # 限制长度
        
        # 3. 规格尺寸
        if spec_info['dimensions']:
            # 清理和格式化尺寸信息
            clean_dimensions = re.sub(r'[^\w\.\-x×]', '', spec_info['dimensions'])
            if clean_dimensions:
                components.append(f"spec-{clean_dimensions}")
        
        # 4. 文件格式
        if spec_info['format']:
            format_clean = re.sub(r'[^\w]', '', spec_info['format'])
            if format_clean:
                components.append(format_clean)
        
        # 5. 时间戳（用于唯一性）
        timestamp = str(int(time.time()))[-6:]  # 取时间戳后6位
        
        # 组合文件名
        if components:
            filename = '_'.join(components) + f'_t{timestamp}' + file_ext
        else:
            # 兜底方案
            filename = f"traceparts_{product_info['short_id']}_{timestamp}{file_ext}"
        
        # 清理特殊字符并限制总长度
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        if len(filename) > 100:
            filename = filename[:95] + file_ext
        
        print(f"📝 生成文件名: {filename}")
        return filename
        
    except Exception as e:
        print(f"⚠️ 生成文件名失败: {e}")
        # 兜底方案
        timestamp = str(int(time.time()))[-6:]
        return f"traceparts_download_{timestamp}.step"

def select_format(page):
    selected_format = None
    for sel in ['select', 'button:has-text("Please select")']:
        el = page.query_selector(sel)
        if el:
            if el.evaluate("el => el.tagName").lower()=="select":
                options = el.query_selector_all('option')
                for fmt in preferred_formats:
                    for idx,opt in enumerate(options):
                        if fmt.lower() in (opt.text_content() or "").lower():
                            el.select_option(index=idx)
                            print("选择格式:",fmt)
                            selected_format = fmt
                            return selected_format
            else:
                el.click()
                page.wait_for_timeout(500)
                for fmt in preferred_formats:
                    opt=page.query_selector(f'li:has-text("{fmt}")')
                    if opt:
                        opt.click();print("选择格式:",fmt)
                        selected_format = fmt
                        return selected_format
    return selected_format

def find_captcha_input_enhanced(page, solver):
    """增强版验证码输入框查找器"""
    print("🔍 开始增强型验证码输入框搜索...")
    
    # 等待iframe加载完成
    print("⏳ 等待iframe加载完成...")
    page.wait_for_timeout(2000)
    
    # 更全面的CSS选择器
    enhanced_selectors = [
        # 基于属性的选择器
        'input[placeholder*="captcha" i]',
        'input[placeholder*="验证码" i]',
        'input[placeholder*="verification" i]',
        'input[placeholder*="code" i]',
        'input[name*="captcha" i]',
        'input[id*="captcha" i]',
        'input[class*="captcha" i]',
        'input[aria-label*="captcha" i]',
        'input[data-testid*="captcha" i]',
        
        # MTCaptcha特定选择器
        'input[id*="mtcaptcha" i]',
        'input[name*="mtcaptcha" i]',
        'input[class*="mtcaptcha" i]',
        
        # 通用文本输入框
        'input[type="text"]',
        'input[type="text"][autocomplete*="off"]',
        'input[autocomplete="off"]',
        
        # 其他可能的模式
        'input[maxlength="4"]',
        'input[maxlength="5"]',
        'input[maxlength="6"]',
        
        # 基于父元素的选择器
        '.captcha input',
        '.verification input',
        '.mtcaptcha input',
        '[class*="captcha"] input',
        '[id*="captcha"] input',
        
        # 更宽泛的搜索
        'input:not([type="hidden"]):not([type="submit"]):not([type="button"]):not([type="email"]):not([type="password"])'
    ]
    
    frames_to_scan = page.frames
    print(f"📄 将扫描 {len(frames_to_scan)} 个frame寻找验证码输入框")
    
    all_found_inputs = []
    
    for frame_idx, frame in enumerate(frames_to_scan):
        frame_name = frame.name or f'[frame-{frame_idx}]'
        frame_url = "[unavailable]"
        try:
            frame_url = frame.url
        except Exception:
            pass
            
        print(f"🔍 扫描 Frame {frame_idx}: '{frame_name}' - {frame_url}")
        
        for sel_idx, sel in enumerate(enhanced_selectors):
            try:
                elements = frame.query_selector_all(sel)
                
                if elements:
                    print(f"  📝 选择器 '{sel}' 找到 {len(elements)} 个元素")
                    
                    for el_idx, el in enumerate(elements):
                        try:
                            # 获取元素详细信息
                            tag_name = el.evaluate("el => el.tagName").lower()
                            input_type = el.get_attribute("type") or "text"
                            placeholder = el.get_attribute("placeholder") or ""
                            name_attr = el.get_attribute("name") or ""
                            id_attr = el.get_attribute("id") or ""
                            class_attr = el.get_attribute("class") or ""
                            current_value = el.input_value() or ""
                            
                            is_visible = el.is_visible()
                            is_editable = el.is_editable()
                            
                            input_info = {
                                'element': el,
                                'frame': frame,
                                'frame_name': frame_name,
                                'selector': sel,
                                'tag': tag_name,
                                'type': input_type,
                                'placeholder': placeholder,
                                'name': name_attr,
                                'id': id_attr,
                                'class': class_attr,
                                'value': current_value,
                                'visible': is_visible,
                                'editable': is_editable,
                                'score': 0
                            }
                            
                            # 打印详细信息
                            print(f"    🎯 元素 {el_idx+1}: tag={tag_name}, type={input_type}")
                            print(f"       📍 id='{id_attr}', name='{name_attr}', class='{class_attr}'")
                            print(f"       📝 placeholder='{placeholder}', value='{current_value}'")
                            print(f"       👁️ visible={is_visible}, editable={is_editable}")
                            
                            # 计算匹配得分
                            score = 0
                            
                            # 基于属性内容评分
                            keywords = ['captcha', 'verification', 'verify', 'code', 'mtcaptcha']
                            for keyword in keywords:
                                if keyword in placeholder.lower():
                                    score += 10
                                if keyword in name_attr.lower():
                                    score += 8
                                if keyword in id_attr.lower():
                                    score += 8
                                if keyword in class_attr.lower():
                                    score += 6
                            
                            # 可见和可编辑加分
                            if is_visible:
                                score += 5
                            if is_editable:
                                score += 5
                            
                            # 空值加分（验证码输入框通常为空）
                            if not current_value.strip():
                                score += 3
                                
                            # text类型加分
                            if input_type == "text":
                                score += 2
                            
                            input_info['score'] = score
                            all_found_inputs.append(input_info)
                            
                            print(f"       🏆 得分: {score}")
                            
                        except Exception as e_el:
                            print(f"    ❌ 检查元素时出错: {e_el}")
                            
            except Exception as e_sel:
                if solver.debug:
                    print(f"    ⚠️ 查询选择器 '{sel}' 时出错: {e_sel}")
    
    # 按得分排序
    all_found_inputs.sort(key=lambda x: x['score'], reverse=True)
    
    print(f"\n🎯 总共找到 {len(all_found_inputs)} 个可能的输入框")
    
    if all_found_inputs:
        print("🏆 按得分排序的候选输入框:")
        for i, info in enumerate(all_found_inputs[:5]):  # 只显示前5个
            print(f"  {i+1}. 得分:{info['score']} Frame:'{info['frame_name']}' "
                  f"ID:'{info['id']}' Name:'{info['name']}' "
                  f"Visible:{info['visible']} Editable:{info['editable']}")
    
    # 返回得分最高且可用的输入框
    for info in all_found_inputs:
        if info['visible'] and info['editable'] and info['score'] > 0:
            print(f"✅ 选择最佳匹配: Frame '{info['frame_name']}', 得分 {info['score']}")
            return info['element']
    
    print("❌ 未找到合适的验证码输入框")
    return None

def main():
    with sync_playwright() as p:
        browser, ctx, page = stealth11i.create_stealth_browser(p, headless=False) # Keep headless=False for debugging

        # ---- 提取产品信息 ----
        print("🔍 解析产品URL信息...")
        product_info = extract_product_info(PRODUCT_URL)
        print(f"📋 产品信息: ID={product_info['short_id']}, Name={product_info['product_name'][:30]}")

        # ---- 下载文件保存设置 ----
        DOWNLOAD_DIR = Path("results/downloads")
        DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

        # 全局变量用于存储规格信息
        current_spec_info = {}

        def _on_download(download):
            try:
                suggested = download.suggested_filename
                print(f"📥 原始文件名: {suggested}")
                
                # 生成规范的文件名
                new_filename = generate_download_filename(product_info, current_spec_info, suggested)
                dest_path = DOWNLOAD_DIR / new_filename
                
                download.save_as(str(dest_path))
                print(f"💾 下载完成，已保存到: {dest_path.resolve()}")
                print(f"📝 文件命名规则: 产品ID_{产品名}_{规格}_{格式}_{时间戳}")
            except Exception as e_dl:
                print(f"❌ 保存下载文件失败: {e_dl}")
                # 兜底保存
                try:
                    fallback_path = DOWNLOAD_DIR / suggested
                    download.save_as(str(fallback_path))
                    print(f"💾 兜底保存到: {fallback_path.resolve()}")
                except Exception as e_fallback:
                    print(f"❌ 兜底保存也失败: {e_fallback}")

        ctx.on("download", _on_download)

        if not stealth11i.stealth_login(page, EMAIL, PASSWORD):
            print("❌ 登录失败，退出测试")
            browser.close()
            return
        
        page.goto(PRODUCT_URL)
        try:
            page.wait_for_load_state('networkidle',timeout=60000)
        except Exception as e:
            print(f"⚠️ 页面加载可能超时或未完全空闲: {e}")
            page.screenshot(path=str(CAP_DIR / f"page_load_issue_{int(time.time())}.png"))

        # ---- 选择格式并获取规格信息 ----
        selected_format = select_format(page)
        page.wait_for_timeout(1000) # Wait a bit after format selection
        
        # 获取当前选择的规格信息
        current_spec_info.update(get_selected_specification(page))
        current_spec_info['format'] = selected_format or current_spec_info.get('format', '')
        
        print(f"📋 当前下载配置: 格式={current_spec_info.get('format', 'unknown')}, 规格={current_spec_info.get('dimensions', 'unknown')}")
        page.wait_for_timeout(500)
        
        print("🤖 初始化GPT-4o验证码识别器...")
        solver = CaptchaSolver(
            debug=True, 
            ocr_method="gpt4o"  # Explicitly use GPT-4o
        )


        
                # 滚动页面确保验证码区域在可视范围内
        print("📜 滚动页面确保验证码区域可见...")
        try:
            # 先尝试找到验证码相关元素并滚动到其位置
            captcha_indicators = [
                'iframe[src*="mtcaptcha"]',
                'iframe[src*="captcha"]', 
                '.mtcaptcha',
                '.captcha',
                '[id*="captcha"]',
                '[class*="captcha"]',
                'input[placeholder*="captcha" i]',
                'input[placeholder*="verification" i]'
            ]
            
            scrolled_to_captcha = False
            for indicator in captcha_indicators:
                element = page.query_selector(indicator)
                if element:
                    try:
                        element.scroll_into_view_if_needed()
                        page.wait_for_timeout(500)
                        print(f"✅ 已滚动到验证码区域 (通过 {indicator})")
                        scrolled_to_captcha = True
                        break
                    except Exception as e_scroll:
                        print(f"⚠️ 滚动到 {indicator} 失败: {e_scroll}")
            
            if not scrolled_to_captcha:
                # 如果没找到验证码元素，尝试向下滚动一些距离
                print("🔽 未找到验证码元素，尝试向下滚动...")
                page.evaluate("window.scrollBy(0, 300)")
                page.wait_for_timeout(500)
                
        except Exception as e_scroll_general:
            print(f"⚠️ 页面滚动过程中出错: {e_scroll_general}")

        # It's good to take a screenshot before trying to solve, for debugging
        pre_solve_screenshot_path = CAP_DIR / f"pre_solve_page_10_{int(time.time())}.png"
        page.screenshot(path=str(pre_solve_screenshot_path))
        print(f"📸 尝试解验证码前的截图已保存到: {pre_solve_screenshot_path}")

        

        text = solver.solve_from_playwright_page(page)  # 直接返回文本
        
        if text:
            print(f'✅ 验证码识别成功 (GPT-4o): {text}')
            
            # 使用增强版输入框查找器
            input_box = find_captcha_input_enhanced(page, solver)
            
            # 输入逻辑 (如果找到了 input_box)
            if input_box:
                try:
                    print("📝 开始填入验证码...")
                    # 确保输入框在可视范围内
                    input_box.scroll_into_view_if_needed()
                    page.wait_for_timeout(500)
                    print("✅ 验证码输入框已滚动到可视范围内") 
                    input_box.focus()
                    page.wait_for_timeout(300) 
                    input_box.fill('') 
                    page.wait_for_timeout(200)
                    
                    # 使用慢速输入模拟人工操作
                    for char in text:
                        input_box.type(char, delay=200)
                        page.wait_for_timeout(100)
                    
                    print(f"✅ 已向定位到的输入框填入: {text}")
                    
                    # 验证填入结果
                    filled_value = input_box.input_value()
                    print(f"🔍 验证填入结果: '{filled_value}'")
                    
                    if filled_value != text:
                        print(f"⚠️ 填入值不匹配，重试...")
                        input_box.fill('')
                        page.wait_for_timeout(300)
                        input_box.type(text, delay=150)
                        
                except Exception as e:
                    print(f"❌ 尝试向定位的输入框填入文本时失败: {e}")
                    # 保存失败时的截图
                    error_screenshot_path = CAP_DIR / f"input_error_{int(time.time())}.png"
                    page.screenshot(path=str(error_screenshot_path))
                    print(f"📸 输入错误截图: {error_screenshot_path}")
            else: 
                 print("❌ 未找到验证码输入框，无法输入验证码。")
                 # 保存调试截图
                 debug_screenshot_path = CAP_DIR / f"no_input_found_{int(time.time())}.png"
                 page.screenshot(path=str(debug_screenshot_path))
                 print(f"📸 未找到输入框调试截图: {debug_screenshot_path}")

        else:
            print("❌ 验证码识别失败 (GPT-4o)")
            # Save screenshot on failure
            failure_screenshot_path = CAP_DIR / f"captcha_failure_10_{int(time.time())}.png"
            page.screenshot(path=str(failure_screenshot_path))
            print(f"📸 验证码识别失败，截图已保存到: {failure_screenshot_path}")
            
        page.wait_for_timeout(1000) # Wait for text to be possibly processed by JS

        print("🔽 尝试点击下载按钮...")
        download_triggered = False
        # Enhanced download button selectors
        download_selectors = [
            'button:has-text("Download"):visible',
            'a[href*="download"]:visible',
            'button[id*="download"]:visible',
            'input[type="submit"][value*="Download" i]:visible',
            '[role="button"]:has-text("Download"):visible'
        ]
        for sel in download_selectors:
            btn = page.query_selector(sel)
            if btn:
                try:
                    print(f"✅ 找到下载按钮: {sel}")
                    btn.click()
                    download_triggered = True
                    break
                except Exception as e:
                    print(f"⚠️ 点击下载按钮 ({sel}) 失败: {e}")
        
        if not download_triggered:
            print("❌ 未找到或未能点击下载按钮")
            final_screenshot_path = CAP_DIR / f"no_download_trigger_10_{int(time.time())}.png"
            page.screenshot(path=str(final_screenshot_path))
            print(f"📸 未触发下载，截图: {final_screenshot_path}")

        print("⏳ 等待5秒观察下载情况或页面跳转...")
        time.sleep(5)

        # ----- 第二阶段：点击右侧活动面板中的下载图标 -----
        print("🔍 检测右侧活动面板中的下载图标...")

        second_download_selectors = [
            'button:has(svg[data-icon="download"])',
            '[class*="download"]:is(button, a)',
            'div[role="button"]:has(svg[data-icon="download"])',
            'button[aria-label*="Download" i]',
            'a[download]',
            '.fa-download',
            'svg[data-icon="download"]'
        ]

        second_clicked = False
        for attempt in range(10): # 尝试约5秒
            for sel in second_download_selectors:
                btn2 = page.query_selector(sel)
                if btn2 and btn2.is_visible():
                    try:
                        print(f"✅ 第二次下载按钮找到并点击: {sel}")
                        with page.expect_download(timeout=60000) as dl_info:
                            btn2.click()
                        download_obj = dl_info.value
                        suggested = download_obj.suggested_filename
                        
                        # 使用规范命名
                        new_filename = generate_download_filename(product_info, current_spec_info, suggested)
                        dest_path = DOWNLOAD_DIR / new_filename
                        try:
                            download_obj.save_as(str(dest_path))
                            print(f"💾 下载完成，已保存到: {dest_path.resolve()}")
                        except Exception as e_save:
                            print(f"❌ 保存下载文件失败: {e_save}")
                            # 兜底保存
                            try:
                                fallback_path = DOWNLOAD_DIR / suggested
                                download_obj.save_as(str(fallback_path))
                                print(f"💾 兜底保存到: {fallback_path.resolve()}")
                            except Exception as e_fallback:
                                print(f"❌ 兜底保存也失败: {e_fallback}")
                        second_clicked = True
                        break
                    except Exception as e2:
                        print(f"⚠️ 点击第二次下载按钮 ({sel}) 失败: {e2}")
            if second_clicked:
                break
            page.wait_for_timeout(500)

        if not second_clicked:
            print("❌ 可能验证码错误，尝试重新识别并提交...")

            max_retries = 2
            for attempt in range(1, max_retries+1):
                solver.extra_prompt = f"Previous OCR guess '{text}' was incorrect. Please re-extract the exact characters from the image only."
                new_text = solver.solve_from_playwright_page(page)
                if not new_text or new_text == text:
                    print(f"⚠️ 第{attempt}次重试未得到新结果: '{new_text}'. 终止重试。")
                    break

                print(f"🔄 第{attempt}次重试获得新验证码: {new_text}")

                # 重新填写验证码
                if input_box and input_box.is_visible():
                    try:
                        input_box.fill("")
                        page.wait_for_timeout(100)
                        input_box.type(new_text, delay=100)
                    except Exception as e_input:
                        print(f"❌ 重试时填写验证码失败: {e_input}")
                        break

                # 再次点击下载
                try:
                    with page.expect_download(timeout=60000) as dl_info:
                        for sel in download_selectors:
                            btn_retry = page.query_selector(sel)
                            if btn_retry and btn_retry.is_visible():
                                btn_retry.click()
                                break
                    download_obj = dl_info.value
                    suggested = download_obj.suggested_filename
                    
                    # 使用规范命名
                    new_filename = generate_download_filename(product_info, current_spec_info, suggested)
                    dest_path = DOWNLOAD_DIR / new_filename
                    try:
                        download_obj.save_as(str(dest_path))
                        print(f"💾 重试下载完成，已保存到: {dest_path.resolve()}")
                    except Exception as e_save2:
                        print(f"❌ 重试保存下载文件失败: {e_save2}")
                        # 兜底保存
                        try:
                            fallback_path = DOWNLOAD_DIR / suggested
                            download_obj.save_as(str(fallback_path))
                            print(f"💾 兜底保存到: {fallback_path.resolve()}")
                        except Exception as e_fallback:
                            print(f"❌ 兜底保存也失败: {e_fallback}")
                    second_clicked = True
                    break
                except Exception as e_retry:
                    print(f"⚠️ 重试点击下载失败或未捕获下载: {e_retry}")

            if not second_clicked:
                print("❌ 重试仍未成功，请人工检查。")

        # 再等待几秒
        time.sleep(3)

        # 保持浏览器与页面开启，方便手动检查；按 Ctrl+C 可终止脚本并关闭浏览器
        print("⚠️ 脚本已暂停，浏览器保持打开状态。按 Ctrl+C 结束并关闭浏览器。")
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            print("🛑 收到退出信号，正在关闭浏览器...")
            browser.close()

if __name__=='__main__':
    main() 