#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 12k —— 精确提取验证码区域并OCR识别
专门针对TraceParts验证码区域进行精确截图和识别
"""

import time
import random
import os
from pathlib import Path
import importlib.util
from playwright.sync_api import sync_playwright, Page
from PIL import Image, ImageEnhance, ImageFilter
import cv2
import numpy as np
from utils.captcha_solver import solve_file
import mimetypes

# ---------- 动态加载 11j 作为模块 -------------
BASE_DIR = Path(__file__).parent
J11_PATH = BASE_DIR / "11j-stealth_cad_downloader_captcha.py"
_spec = importlib.util.spec_from_file_location("stealth11j", J11_PATH)
stealth11j = importlib.util.module_from_spec(_spec)  # type: ignore
_spec.loader.exec_module(stealth11j)  # type: ignore

# 复用函数
create_stealth_browser = stealth11j.create_stealth_browser
fast_stealth_login = stealth11j.fast_stealth_login
fast_navigate_to_product = stealth11j.fast_navigate_to_product

# ---------- 常量 ----------
CAPTCHA_DIR = Path("results/captcha_samples")
CAPTCHA_DIR.mkdir(parents=True, exist_ok=True)

def locate_captcha_element(page: Page):
    """智能定位验证码元素 - 基于位置关系和图片特征"""
    print("🧠 开始智能定位验证码...")
    
    # 第一步：定位captcha输入框获取基准位置
    print("1️⃣ 定位captcha输入框作为基准...")
    captcha_input = None
    input_info = None
    
    input_selectors = [
        "input[name='captcha']",
        "input[placeholder*='captcha']",
        "input[placeholder*='验证码']",
    ]
    
    for selector in input_selectors:
        try:
            elem = page.query_selector(selector)
            if elem and elem.is_visible():
                captcha_input = elem
                input_info = elem.bounding_box()
                print(f"✅ 找到captcha输入框: {selector}")
                print(f"   输入框位置: x={input_info['x']}, y={input_info['y']}, 宽度={input_info['width']}, 高度={input_info['height']}")
                break
        except Exception as e:
            print(f"   错误检查 {selector}: {e}")
            continue
    
    if not captcha_input or not input_info:
        print("❌ 未找到captcha输入框，无法继续定位")
        return None
    
    # 第二步：在输入框附近区域搜索所有图片
    print("2️⃣ 搜索输入框附近的所有图片...")
    
    # 定义搜索区域：输入框左右各300px，上下各100px
    search_area = {
        'left': max(0, input_info['x'] - 300),
        'right': input_info['x'] + input_info['width'] + 300, 
        'top': max(0, input_info['y'] - 100),
        'bottom': input_info['y'] + input_info['height'] + 100
    }
    
    print(f"   搜索区域: 左={search_area['left']}, 右={search_area['right']}, 上={search_area['top']}, 下={search_area['bottom']}")
    
    # 获取搜索区域内的所有图片信息
    nearby_images = page.evaluate(f"""
        () => {{
            const searchArea = {search_area};
            const imgs = document.querySelectorAll('img');
            const candidates = [];
            
            imgs.forEach((img, index) => {{
                const rect = img.getBoundingClientRect();
                
                // 检查图片是否在搜索区域内
                if (rect.left >= searchArea.left && 
                    rect.right <= searchArea.right &&
                    rect.top >= searchArea.top && 
                    rect.bottom <= searchArea.bottom &&
                    rect.width > 0 && rect.height > 0) {{
                    
                    // 获取图片的样式信息
                    const computedStyle = window.getComputedStyle(img);
                    const backgroundColor = computedStyle.backgroundColor;
                    
                    candidates.push({{
                        index: index,
                        src: img.src,
                        alt: img.alt || '',
                        className: img.className,
                        x: rect.x,
                        y: rect.y,
                        width: rect.width,
                        height: rect.height,
                        backgroundColor: backgroundColor,
                        parentTagName: img.parentElement ? img.parentElement.tagName : '',
                        nearbyText: img.parentElement ? img.parentElement.innerText.slice(0, 50) : ''
                    }});
                }}
            }});
            
            return candidates;
        }}
    """)
    
    print(f"   在搜索区域内找到 {len(nearby_images)} 个图片:")
    
    # 第三步：智能分析哪个图片最可能是验证码
    print("3️⃣ 智能分析验证码候选图片...")
    
    best_candidates = []
    
    for i, img in enumerate(nearby_images):
        print(f"   图片{img['index']}: 位置({img['x']:.0f},{img['y']:.0f}) 尺寸{img['width']:.0f}x{img['height']:.0f}")
        print(f"     src: {img['src'][:60]}...")
        print(f"     背景色: {img['backgroundColor']}")
        print(f"     父元素: {img['parentTagName']}, 附近文本: {img['nearbyText']}")
        
        # 验证码特征评分
        score = 0
        reasons = []
        
        # 尺寸评分：验证码通常是合理的矩形尺寸
        if 80 <= img['width'] <= 200 and 25 <= img['height'] <= 80:
            score += 30
            reasons.append("合理尺寸")
        
        # 宽高比评分：验证码通常宽度大于高度
        if img['width'] > img['height'] and 2 <= (img['width'] / img['height']) <= 6:
            score += 20
            reasons.append("合理宽高比")
        
        # src特征评分
        src_lower = img['src'].lower()
        if any(kw in src_lower for kw in ['captcha', 'verify', 'code', 'challenge']):
            score += 40
            reasons.append("src包含验证码关键词")
        elif src_lower.startswith('data:image'):
            score += 25
            reasons.append("base64图片")
        
        # 位置关系评分：通常在输入框右侧
        distance_from_input = abs(img['x'] - (input_info['x'] + input_info['width']))
        if distance_from_input < 50:  # 距离输入框很近
            score += 35
            reasons.append("紧邻输入框")
        elif distance_from_input < 150:
            score += 15
            reasons.append("接近输入框")
        
        # 上下文评分
        context = (img['nearbyText'] + img['parentTagName']).lower()
        if any(kw in context for kw in ['captcha', 'verify', '验证', 'code']):
            score += 20
            reasons.append("上下文相关")
        
        print(f"     评分: {score} 分 - {', '.join(reasons)}")
        
        if score >= 30:  # 最低分数阈值
            best_candidates.append((score, img, reasons))
    
    # 选择得分最高的候选
    if best_candidates:
        best_candidates.sort(key=lambda x: x[0], reverse=True)
        best_score, best_img, best_reasons = best_candidates[0]
        
        print(f"🎯 选择最佳验证码候选 (得分: {best_score}):")
        print(f"   图片{best_img['index']}: {best_img['width']:.0f}x{best_img['height']:.0f}")
        print(f"   理由: {', '.join(best_reasons)}")
        
        # 返回对应的页面元素
        return page.locator("img").nth(best_img['index'])
    
    print("❌ 未找到符合条件的验证码图片")
    
    # 如果仍然找不到，显示所有候选供调试
    if nearby_images:
        print("🔍 所有附近图片信息供调试:")
        for img in nearby_images:
            print(f"   图片{img['index']}: {img['width']:.0f}x{img['height']:.0f}, src={img['src'][:40]}...")
    
    return None

def extract_captcha_region(page: Page):
    """提取验证码区域截图"""
    timestamp = int(time.time())
    
    # 方法1: 直接定位验证码元素并截图
    captcha_element = locate_captcha_element(page)
    if captcha_element:
        print("📸 直接截图验证码元素...")
        captcha_path = CAPTCHA_DIR / f"captcha_direct_{timestamp}.png"
        captcha_element.screenshot(path=str(captcha_path))
        print(f"✅ 验证码元素截图: {captcha_path}")
        return captcha_path
    
    # 方法2: 全页面截图后裁剪验证码区域
    print("📸 全页面截图后智能裁剪...")
    full_page_path = CAPTCHA_DIR / f"full_page_{timestamp}.png"
    page.screenshot(path=str(full_page_path), full_page=True)
    
    # 使用图像处理技术找到验证码区域
    captcha_region = crop_captcha_from_fullpage(full_page_path, timestamp)
    if captcha_region:
        return captcha_region
    
    # 方法3: 基于输入框位置推断验证码位置（扩大裁剪范围 & 检查canvas）
    print("🎯 基于输入框位置推断验证码...")
    captcha_input = None
    input_selectors = [
        "input[name='captcha']",
        "input[placeholder*='captcha']",
        "input[type='text']:below(label:has-text('captcha'))"
    ]
    
    for selector in input_selectors:
        try:
            captcha_input = page.query_selector(selector)
            if captcha_input and captcha_input.is_visible():
                break
        except:
            continue
    
    if captcha_input:
        # 获取输入框位置，推断验证码图片位置
        box = captcha_input.bounding_box()
        if box:
            # 尝试截图兄弟 canvas
            parent_locator = captcha_input.locator("xpath=..")
            try:
                canvas_elem = parent_locator.locator("canvas").first
                if canvas_elem and canvas_elem.is_visible():
                    canvas_path = CAPTCHA_DIR / f"captcha_canvas_{timestamp}.png"
                    canvas_elem.screenshot(path=str(canvas_path))
                    print(f"✅ 截取canvas验证码: {canvas_path}")
                    return canvas_path
            except Exception:
                pass

            crop_box = {
                'x': box['x'] + box['width'] + 5,  # 输入框右侧紧邻
                'y': max(0, box['y'] - 15),
                'width': 200,  # 更大宽度
                'height': max(60, box['height'] + 30)  # 更高高度
            }

            inferred_path = CAPTCHA_DIR / f"captcha_inferred_{timestamp}.png"
            try:
                page.screenshot(path=str(inferred_path), clip=crop_box)
                print(f"✅ 推断位置截图: {inferred_path}")
                return inferred_path
            except Exception as e:
                print(f"⚠️ 推断截图失败: {e}")
                return None
    
    print("❌ 所有方法都无法定位验证码")
    return None

def crop_captcha_from_fullpage(full_page_path: Path, timestamp: int):
    """从全页面截图中智能裁剪验证码区域"""
    try:
        # 读取图片
        img = cv2.imread(str(full_page_path))
        if img is None:
            return None
        
        # 转换为HSV颜色空间，寻找橙色区域（验证码背景）
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        
        # 橙色范围 (根据截图中的橙色背景调整)
        lower_orange = np.array([10, 100, 100])
        upper_orange = np.array([25, 255, 255])
        
        # 创建橙色掩码
        mask = cv2.inRange(hsv, lower_orange, upper_orange)
        
        # 查找轮廓
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if contours:
            # 找到最大的橙色区域
            largest_contour = max(contours, key=cv2.contourArea)
            x, y, w, h = cv2.boundingRect(largest_contour)
            
            # 扩展边界以包含完整验证码
            margin = 10
            x = max(0, x - margin)
            y = max(0, y - margin)
            w = min(img.shape[1] - x, w + 2 * margin)
            h = min(img.shape[0] - y, h + 2 * margin)
            
            # 裁剪验证码区域
            captcha_region = img[y:y+h, x:x+w]
            
            # 保存裁剪后的验证码
            cropped_path = CAPTCHA_DIR / f"captcha_cropped_{timestamp}.png"
            cv2.imwrite(str(cropped_path), captcha_region)
            print(f"✅ 智能裁剪验证码: {cropped_path} (位置: {x},{y} 尺寸: {w}x{h})")
            return cropped_path
        
    except Exception as e:
        print(f"❌ 智能裁剪失败: {e}")
    
    return None

def enhance_captcha_image(image_path: Path):
    """增强验证码图片质量以提高OCR准确率"""
    try:
        # 使用PIL增强图片
        img = Image.open(image_path)
        
        # 放大图片
        img = img.resize((img.width * 3, img.height * 3), Image.Resampling.LANCZOS)
        
        # 增强对比度
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(2.0)
        
        # 增强锐度
        enhancer = ImageEnhance.Sharpness(img)
        img = enhancer.enhance(2.0)
        
        # 转为灰度
        img = img.convert('L')
        
        # 二值化
        img = img.point(lambda x: 0 if x < 128 else 255, '1')
        
        # 保存增强后的图片
        enhanced_path = image_path.parent / f"enhanced_{image_path.name}"
        img.save(enhanced_path)
        print(f"✨ 图片增强完成: {enhanced_path}")
        return enhanced_path
        
    except Exception as e:
        print(f"❌ 图片增强失败: {e}")
        return image_path

def main():
    """主函数"""
    email = os.getenv("TRACEPARTS_EMAIL", "SearcherKerry36154@hotmail.com")
    password = os.getenv("TRACEPARTS_PASSWORD", "Vsn220mh@")
    
    print("🎯 TraceParts 验证码区域提取器")
    print("=" * 50)
    print(f"账号: {email}")
    
    with sync_playwright() as p:
        browser, context, page = create_stealth_browser(p, headless=False)
        
        try:
            # 快速登录和导航
            if not fast_stealth_login(page, email, password):
                print("❌ 登录失败")
                return
            
            if not fast_navigate_to_product(page):
                print("❌ 产品页面访问失败")
                return
            
            # 网络嗅探：拦截 image 响应
            print("🎣 启用网络嗅探，捕获验证码图片...")
            captured_images = []

            def save_response(resp):
                try:
                    ct = resp.headers.get("content-type", "")
                    if "image" in ct and any(ext in ct for ext in ["png", "jpeg", "jpg"]):
                        body = resp.body()
                        if body and len(body) < 50 * 1024:  # 限小于50KB
                            ts = int(time.time() * 1000)
                            ext = ".png" if "png" in ct else ".jpg"
                            file_path = CAPTCHA_DIR / f"net_{ts}{ext}"
                            with open(file_path, "wb") as imgf:
                                imgf.write(body)
                            print(f"📥 网络捕获图片: {file_path} 大小={len(body)//1024}KB URL={resp.url[:60]}...")
                            captured_images.append(file_path)
                except Exception:
                    pass

            page.on("response", save_response)

            # 页面标题出现后验证码已加载，立即提取
            print("🎯 页面标题已显示，验证码应该已加载，开始提取...")
            captcha_path = extract_captcha_region(page)
            
            if captcha_path:
                print(f"📸 验证码截图成功: {captcha_path}")
                
                # 增强图片质量
                enhanced_path = enhance_captcha_image(captcha_path)
                
                # OCR识别
                print("🔍 开始OCR识别...")
                
                # 尝试原图
                original_text = solve_file(str(captcha_path))
                print(f"📖 原图OCR结果: '{original_text}'")
                
                # 尝试增强图
                enhanced_text = solve_file(str(enhanced_path))
                print(f"✨ 增强图OCR结果: '{enhanced_text}'")
                
                # 选择最佳结果
                best_text = enhanced_text if len(enhanced_text) >= 4 else original_text
                
                if best_text and len(best_text) >= 4:
                    print(f"🎉 最终识别结果: '{best_text}'")
                else:
                    print("⚠️ OCR识别可能不准确，请手动检查图片")
                
            else:
                print("❌ 无法定位验证码元素，尝试网络捕获的图片...")
                if captured_images:
                    # 取最后一个捕获的图片作为验证码猜测
                    candidate = captured_images[-1]
                    print(f"🔍 尝试OCR网络捕获的最后一张图片: {candidate}")
                    enhanced_path = enhance_captcha_image(candidate)
                    text_guess = solve_file(str(enhanced_path))
                    print(f"📖 OCR识别结果: '{text_guess}'")
                else:
                    print("⚠️ 网络嗅探未捕获到符合条件的图片")
            
            input("\n按回车键关闭浏览器...")
            
        finally:
            browser.close()

if __name__ == "__main__":
    main() 