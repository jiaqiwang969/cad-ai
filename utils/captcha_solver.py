#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证码识别模块 - 通过刷新图标定位并识别验证码
支持pytesseract, TrOCR多模型识别, 以及GPT-4o API
"""

import cv2
import numpy as np
from PIL import Image
import pytesseract
import os
import tempfile
from pathlib import Path
import requests
import base64
import time

# TrOCR相关导入（可选，如果导入失败则回退到pytesseract）
try:
    import torch
    from transformers import TrOCRProcessor, VisionEncoderDecoderModel
    TROCR_AVAILABLE = True
    print("🤖 TrOCR模块已加载")
except ImportError:
    TROCR_AVAILABLE = False
    print("⚠️ TrOCR模块未安装，将使用pytesseract")

# GPT-4o API 配置 (从 test_4o.py 获取)
GPT4O_API_KEY = "sk-YgL2cnnuifh9AloZFa6d63111aC64e4898Ba0769077521Ac" # TODO: Move to config or env
GPT4O_BASE_URL = "https://ai.pumpkinai.online/v1" # TODO: Move to config or env
GPT4O_MODEL_NAME = "gpt-4o"

# TrOCR模型配置
AVAILABLE_MODELS = {
    "captcha-v3": {
        "repo": "anuashok/ocr-captcha-v3",
        "description": "4字符英数字验证码专用模型",
        "max_tokens": 4
    },
    "microsoft-large": {
        "repo": "microsoft/trocr-large-printed",
        "description": "微软大型印刷体识别模型",
        "max_tokens": 8
    },
    "microsoft-base": {
        "repo": "microsoft/trocr-base-printed",
        "description": "微软基础印刷体识别模型",
        "max_tokens": 6
    }
}

class CaptchaSolver:
    """验证码识别器 - 支持pytesseract, TrOCR多模型, 和GPT-4o API"""
    
    def __init__(self, icon_template_path=["01.png", "02.png"], debug=False, 
                 ocr_method="auto", trocr_model="microsoft-large"):
        """
        初始化验证码识别器
        
        Args:
            icon_template_path: 刷新图标模板路径（可以是单个路径或路径列表）
            debug: 是否开启调试模式（保存中间图片）
            ocr_method: OCR方法选择 ("auto", "pytesseract", "trocr", "gpt4o")
            trocr_model: TrOCR模型选择 (见AVAILABLE_MODELS)
        """
        # 支持单个路径或路径列表
        if isinstance(icon_template_path, str):
            self.icon_template_paths = [icon_template_path]
        else:
            self.icon_template_paths = icon_template_path
        self.debug = debug
        self.icon_templates = []  # 存储多个模板
        
        # OCR方法配置
        self.ocr_method = ocr_method
        self.trocr_model_key = trocr_model
        self.processor = None
        self.trocr_model = None
        self.extra_prompt = ""  # 额外的 GPT 提示，可在运行时动态修改
        
        # 验证码区域参数（相对于刷新图标的位置）
        self.captcha_width = 200
        self.captcha_height = 50
        self.h_offset = 10
        self.v_offset = -5
        
        self._load_icon_template()
        
        if self.ocr_method in ("auto", "trocr"):
            self._init_trocr_model()
    
    def _init_trocr_model(self):
        """初始化TrOCR模型"""
        if not TROCR_AVAILABLE:
            if self.ocr_method == "trocr" or (self.ocr_method == "auto" and self.debug):
                print("⚠️ TrOCR不可用，无法初始化TrOCR模型。")
            if self.ocr_method == "trocr": # If explicitly TroCR, it can't work
                 print("⚠️ TrOCR方法指定但模块不可用，请检查安装或切换方法。")
            return
        
        if self.ocr_method in ("auto", "trocr"):
            try:
                if self.trocr_model_key not in AVAILABLE_MODELS:
                    print(f"❌ TrOCR模型 '{self.trocr_model_key}' 不存在，使用默认模型 'microsoft-large'")
                    self.trocr_model_key = "microsoft-large"
                
                model_info = AVAILABLE_MODELS[self.trocr_model_key]
                repo = model_info["repo"]
                
                if self.debug:
                    print(f"🤖 加载TrOCR模型: {model_info['description']}")
                    print(f"📦 仓库: {repo}")
                
                self.processor = TrOCRProcessor.from_pretrained(repo)
                self.trocr_model = VisionEncoderDecoderModel.from_pretrained(repo).eval()
                self.trocr_model.to("cpu")
                
                if self.debug:
                    print("✅ TrOCR模型加载完成")
                    
            except Exception as e:
                print(f"❌ TrOCR模型 '{self.trocr_model_key}' 加载失败: {e}")
                self.processor = None # Ensure processor is also None on failure
                self.trocr_model = None
                if self.ocr_method == "trocr": # If TroCR was explicitly chosen and failed
                    print("⚠️ TrOCR识别将不可用。")
    
    def switch_trocr_model(self, model_key):
        """切换TrOCR模型"""
        if not TROCR_AVAILABLE:
            print("⚠️ TrOCR模块不可用，无法切换模型。")
            return False
        
        if model_key not in AVAILABLE_MODELS:
            print(f"❌ 模型 '{model_key}' 不存在")
            print(f"✅ 可用模型: {list(AVAILABLE_MODELS.keys())}")
            return False
        
        self.trocr_model_key = model_key
        self._init_trocr_model() # Re-initialize with the new key
        return True if self.trocr_model and self.processor else False

    def _load_icon_template(self):
        """加载并缩放刷新图标模板"""
        self.icon_templates = []
        loaded_count = 0
        
        for template_path in self.icon_template_paths:
            if os.path.exists(template_path):
                tmpl = cv2.imread(template_path)
                if tmpl is not None:
                    scale_factor = 0.25
                    new_width = int(tmpl.shape[1] * scale_factor)
                    new_height = int(tmpl.shape[0] * scale_factor)
                    scaled_template = cv2.resize(tmpl, (new_width, new_height), 
                                               interpolation=cv2.INTER_AREA)
                    self.icon_templates.append({
                        'template': scaled_template,
                        'path': template_path,
                        'size': (new_width, new_height)
                    })
                    loaded_count += 1
                    if self.debug:
                        print(f"📏 图标模板 '{template_path}' 缩放到: {new_width}x{new_height}")
                else:
                    if self.debug:
                        print(f"⚠️ 无法加载图标模板: {template_path}")
            else:
                if self.debug:
                    print(f"⚠️ 图标模板不存在: {template_path}")
        
        if loaded_count == 0:
            raise FileNotFoundError(f"所有图标模板都无法加载: {self.icon_template_paths}")
        
        if self.debug:
            print(f"✅  {loaded_count} 个图标模板")
    
    def solve_from_screenshot(self, screenshot_path):
        """从截图文件中识别验证码"""
        page = cv2.imread(screenshot_path)
        if page is None:
            print(f"❌ 无法加载截图: {screenshot_path}")
            return None
        return self._solve_from_image(page)
    
    def solve_from_playwright_page(self, page, return_bbox=False):
        """从Playwright页面中识别验证码"""
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            tmp_path = tmp.name
        try:
            page.screenshot(path=tmp_path)
            result_data = self.solve_from_screenshot(tmp_path) # This now returns a dict or None
            if return_bbox:
                return result_data # Pass the whole dict
            return result_data["text"] if result_data else None
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    def _solve_from_image(self, image):
        """从OpenCV图像中识别验证码"""
        original_image_for_debug = image.copy()
        icon_pos = self._locate_refresh_icon(image)
        if icon_pos is None:
            return None
        
        x_icon, y_icon = icon_pos
        
        cap_left = max(x_icon - self.captcha_width - self.h_offset, 0)
        cap_top = max(y_icon + self.v_offset, 0)
        cap_right = x_icon - self.h_offset
        cap_bottom = min(cap_top + self.captcha_height, image.shape[0])
        
        captcha_crop_cv2 = image[cap_top:cap_bottom, cap_left:cap_right]
        
        if self.debug:
            self._save_debug_images(original_image_for_debug,
                                  x_icon, y_icon, 
                                  cap_left, cap_top, cap_right, cap_bottom, 
                                  captcha_crop_cv2)
        
        text = self._ocr_captcha(captcha_crop_cv2) # Pass OpenCV image
        
        # 使用匹配到的模板尺寸
        if hasattr(self, 'last_matched_template') and self.last_matched_template:
            width, height = self.last_matched_template['size']
        else:
            # 兜底：使用第一个模板的尺寸
            width, height = self.icon_templates[0]['size'] if self.icon_templates else (32, 32)
        
        return {
            "text": text,
            "icon_bbox": {"x": x_icon, "y": y_icon, "width": width, "height": height}
        }
    
    def _locate_refresh_icon(self, image):
        """在图像中定位刷新图标"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        best_match = None
        best_score = 0
        best_template_info = None
        
        # 尝试所有模板，找到最佳匹配
        for template_info in self.icon_templates:
            template = template_info['template']
            template_path = template_info['path']
            
            gray_tmpl = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
            
            res = cv2.matchTemplate(gray, gray_tmpl, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(res)
            
            if self.debug:
                print(f"🔍 模板 '{template_path}' 匹配相似度: {max_val:.2f}")
            
            if max_val > best_score:
                best_score = max_val
                best_match = max_loc
                best_template_info = template_info
        
        if best_score < 0.5:
            if self.debug:
                print(f"❌ 所有刷新图标模板都未匹配到 (最佳相似度: {best_score:.2f})")
            return None
        
        if self.debug:
            print(f"✅ 刷新图标已定位 (使用模板: {best_template_info['path']}), 相似度: {best_score:.2f}")
        
        # 存储最佳匹配的模板信息，供调试使用
        self.last_matched_template = best_template_info
        return best_match
    
    def _apply_ocr_corrections(self, text):
        """保持原始识别结果，不做任何处理"""
        if not text: 
            return ""
        # 只去除首尾空格，保持原始大小写和长度
        return text.strip()

    def _ocr_captcha_gpt4o(self, captcha_img_cv2, extra_prompt: str = ""):
        """使用GPT-4o API识别验证码图像 (OpenCV格式输入)"""
        if not GPT4O_API_KEY or not GPT4O_BASE_URL or not GPT4O_MODEL_NAME:
            print("❌ GPT-4o API Key, Base URL, or Model Name 未配置，无法使用GPT-4o识别")
            return None
        
        try:
            _, buffer = cv2.imencode('.png', captcha_img_cv2)
            image_b64 = base64.b64encode(buffer).decode("utf-8")

            headers = {
                "Authorization": f"Bearer {GPT4O_API_KEY}",
                "Content-Type": "application/json"
            }
            prompt_text = ("Please extract and return only the text from this image. "
                           "Output the exact characters only, without any explanation or extra content.")
            if extra_prompt:
                prompt_text = extra_prompt + " " + prompt_text

            json_data = {
                "model": GPT4O_MODEL_NAME,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt_text},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}}
                        ]
                    }
                ],
                "max_tokens": 10,
                "temperature": 0
            }

            if self.debug:
                print(f"🤖 调用GPT-4o API: {GPT4O_BASE_URL}/chat/completions with model {GPT4O_MODEL_NAME}")
            
            response = requests.post(f"{GPT4O_BASE_URL}/chat/completions", headers=headers, json=json_data, timeout=30)

            if response.ok:
                result = response.json()
                content = result.get('choices', [{}])[0].get('message', {}).get('content', '').strip()
                if self.debug:
                    print(f"✅ GPT-4o 原始响应: {content}")
                # Correction is now handled by _apply_ocr_corrections
                return content 
            else:
                if self.debug:
                    print(f"❌ GPT-4o API 错误: {response.status_code} {response.text}")
                return None
        except requests.exceptions.RequestException as e:
            if self.debug:
                print(f"❌ GPT-4o API 请求异常: {e}")
            return None
        except Exception as e:
            if self.debug:
                print(f"❌ GPT-4o 处理时发生未知错误: {e}")
            return None

    def _ocr_captcha_trocr(self, captcha_img_pil): # Expects Pillow Image
        """使用TrOCR模型识别验证码 (Pillow Image 输入)"""
        if not TROCR_AVAILABLE or not self.trocr_model or not self.processor:
            if self.debug: print("TrOCR不可用或未初始化，无法执行TrOCR识别。")
            return None
        
        best_result = ""
        best_confidence = -1 
        
        model_max_tokens = AVAILABLE_MODELS.get(self.trocr_model_key, {}).get("max_tokens", 4)

        # Preprocessing similar to test_2.py
        cv_img_for_preprocessing = cv2.cvtColor(np.array(captcha_img_pil), cv2.COLOR_RGB2BGR)
        gray_captcha = cv2.cvtColor(cv_img_for_preprocessing, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        enhanced = clahe.apply(gray_captcha)
        denoised = cv2.medianBlur(enhanced, 3)
        _, binary1 = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        adaptive = cv2.adaptiveThreshold(denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                        cv2.THRESH_BINARY, 11, 2)
        inverted = 255 - binary1

        # Include original color image from PIL input
        methods = [
            ("原始彩色", captcha_img_pil), 
            ("二值化", Image.fromarray(cv2.cvtColor(binary1, cv2.COLOR_GRAY2RGB))),
            ("自适应阈值", Image.fromarray(cv2.cvtColor(adaptive, cv2.COLOR_GRAY2RGB))),
            ("反色", Image.fromarray(cv2.cvtColor(inverted, cv2.COLOR_GRAY2RGB)))
        ]
        
        for method_name, processed_img_pil in methods:
            try:
                with torch.no_grad():
                    pixel_values = self.processor(images=processed_img_pil, return_tensors="pt").pixel_values.to(self.trocr_model.device)
                    generated_ids = self.trocr_model.generate(pixel_values, max_new_tokens=min(model_max_tokens, 10)) # Truncate to 10 for safety, will be cut by corrections
                    text = self.processor.batch_decode(generated_ids, skip_special_tokens=True)[0].strip()
                
                confidence = len(text)
                if len(text) == 4 and text.isalnum(): # Basic confidence
                    confidence += 2
                
                if self.debug:
                    print(f"📝 TrOCR ({method_name}) 识别结果: '{text}' (置信度: {confidence})")
                
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_result = text
                    if len(best_result) == 4 and best_result.isalnum(): # Good enough, stop early
                        break 
            except Exception as e:
                if self.debug:
                    print(f"⚠️ TrOCR ({method_name}) 处理异常: {e}")
        
        if self.debug:
            print(f"📝 TrOCR 最佳识别: '{best_result}'")
        return best_result if best_result else None

    def _ocr_captcha_pytesseract(self, captcha_img_pil): # Expects Pillow Image
        """使用pytesseract识别验证码 (Pillow Image输入)"""
        try:
            # Pytesseract often works better with some preprocessing
            gray_pil = captcha_img_pil.convert('L')
            # Optionally, apply thresholding if it helps
            # enhanced_pil = gray_pil.point(lambda x: 0 if x < 128 else 255, '1')
            
            custom_config = r'--oem 3 --psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
            text = pytesseract.image_to_string(gray_pil, config=custom_config).strip()
            
            if self.debug:
                print(f"📝 Pytesseract 识别结果: '{text}'")
            return text
        except Exception as e:
            if self.debug:
                print(f"❌ Pytesseract OCR 失败: {e}")
            return None

    def _ocr_captcha(self, captcha_img_cv2): # Expects OpenCV image
        """核心OCR识别逻辑，根据ocr_method选择不同方法"""
        # 统一，只使用 GPT-4o
        if self.debug:
            print("尝试使用 GPT-4o 进行 OCR 识别...")

        text = self._ocr_captcha_gpt4o(captcha_img_cv2, self.extra_prompt)
        # 重置额外提示，避免影响下次调用
        self.extra_prompt = ""

        final_text = self._apply_ocr_corrections(text if text else "")

        if self.debug:
            print(f"最终 OCR 结果: '{final_text}'")

        return final_text


    def _save_debug_images(self, original_image, x_icon, y_icon, 
                          cap_left, cap_top, cap_right, cap_bottom, captcha_cv2_crop):
        """保存调试过程中的图像"""
        dbg_dir = Path("results") / "captcha_debug"
        dbg_dir.mkdir(parents=True, exist_ok=True)
        
        ts = int(time.time()) # Add timestamp to filenames to avoid overwrites

        # 1. 保存原始截图 (如果尚未保存或需要每次都保存新版本)
        cv2.imwrite(str(dbg_dir / f"original_screenshot_for_debug_{ts}.png"), original_image)

        # 2. 保存定位和裁剪区域的调试图
        debug_img_regions = original_image.copy()
        # 绘制验证码区域 (绿色)
        cv2.rectangle(debug_img_regions, (cap_left, cap_top), (cap_right, cap_bottom), (0, 255, 0), 2)
        # 绘制图标区域 (蓝色)
        if hasattr(self, 'last_matched_template') and self.last_matched_template:
            w_tmpl, h_tmpl = self.last_matched_template['size']
        else:
            # 兜底：使用第一个模板的尺寸
            w_tmpl, h_tmpl = self.icon_templates[0]['size'] if self.icon_templates else (32, 32)
        cv2.rectangle(debug_img_regions, (x_icon, y_icon), (x_icon + w_tmpl, y_icon + h_tmpl), (255, 0, 0), 2)
        cv2.imwrite(str(dbg_dir / f"debug_located_regions_{ts}.png"), debug_img_regions)

        # 3. 保存裁剪出的验证码本身
        cv2.imwrite(str(dbg_dir / f"located_captcha_crop_{ts}.png"), captcha_cv2_crop)
        
        # 4. (可选) 保存TrOCR预处理后的图像 (可以在_ocr_captcha_trocr内部完成)
        # Example: cv2.imwrite(str(dbg_dir / f"trocr_preprocessed_binary_{ts}.png"), binary_image_from_trocr)

        if self.debug:
            print(f"💾 调试图片已保存到: {dbg_dir.resolve()}")


def solve_captcha_from_screenshot(screenshot_path, icon_path=["01.png", "02.png"], debug=False, 
                                 ocr_method="auto", trocr_model="microsoft-large"):
    solver = CaptchaSolver(icon_template_path=icon_path, debug=debug, 
                           ocr_method=ocr_method, trocr_model=trocr_model)
    return solver.solve_from_screenshot(screenshot_path)

def solve_captcha_from_playwright(page, icon_path=["01.png", "02.png"], debug=False,
                                 ocr_method="auto", trocr_model="microsoft-large"):
    solver = CaptchaSolver(icon_template_path=icon_path, debug=debug, 
                           ocr_method=ocr_method, trocr_model=trocr_model)
    # Ensure this returns the dictionary
    return solver.solve_from_playwright_page(page, return_bbox=True)


def solve_base64_captcha(b64_png, debug=False, ocr_method="auto", trocr_model="microsoft-large"):
    """
    从Base64编码的PNG图像字符串中识别验证码
    """
    try:
        img_data = base64.b64decode(b64_png)
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            tmp.write(img_data)
            tmp_path = tmp.name
        
        solver = CaptchaSolver(debug=debug, ocr_method=ocr_method, trocr_model=trocr_model)
        # Assuming solve_from_screenshot now returns a dict: {"text": "...", "icon_bbox": ...}
        # For base64, icon_bbox might not be relevant or calculable without full page context.
        # This function might need to be re-thought if icon location is critical from base64.
        # For now, just extract text.
        result_data = solver.solve_from_screenshot(tmp_path)
        return result_data["text"] if result_data else None

    except Exception as e:
        if debug:
            print(f"❌ Base64解码或识别失败: {e}")
        return None
    finally:
        if 'tmp_path' in locals() and os.path.exists(tmp_path):
            os.unlink(tmp_path)

def solve_file(path, debug=False, ocr_method="auto", trocr_model="microsoft-large"):
    """
    直接从图像文件识别验证码 (此函数现在更像是 solve_captcha_from_screenshot 的包装器)
    """
    solver = CaptchaSolver(debug=debug, ocr_method=ocr_method, trocr_model=trocr_model)
    # Assuming solve_from_screenshot now returns a dict
    result_data = solver.solve_from_screenshot(path)
    return result_data["text"] if result_data else None

# Example Usage (for direct script testing if needed)
if __name__ == '__main__':
    # Create a dummy screenshot for testing
    dummy_image_path = "results/captcha_samples/page_before_format_select_1748699648.png"
    # Ensure the dummy image exists or provide a valid path
    if not os.path.exists(dummy_image_path):
        print(f"测试图片 {dummy_image_path} 不存在，请先准备。")
    else:
        print(f"--- 测试 CaptchaSolver with GPT-4o (指定) ---")
        solver_gpt4o = CaptchaSolver(debug=True, ocr_method="gpt4o")
        result_gpt4o = solver_gpt4o.solve_from_screenshot(dummy_image_path)
        print(f"GPT-4o (指定) 结果: {result_gpt4o}")

        print(f"\\n--- 测试 CaptchaSolver with auto (GPT-4o -> TrOCR -> Pytesseract) ---")
        solver_auto = CaptchaSolver(debug=True, ocr_method="auto", trocr_model="microsoft-base")
        result_auto = solver_auto.solve_from_screenshot(dummy_image_path)
        print(f"Auto 结果: {result_auto}")

        print(f"\\n--- 测试 CaptchaSolver with TrOCR only ---")
        solver_trocr = CaptchaSolver(debug=True, ocr_method="trocr", trocr_model="microsoft-base")
        result_trocr = solver_trocr.solve_from_screenshot(dummy_image_path)
        print(f"TrOCR (指定) 结果: {result_trocr}")

        print(f"\\n--- 测试 CaptchaSolver with Pytesseract only ---")
        solver_pytesseract = CaptchaSolver(debug=True, ocr_method="pytesseract")
        result_pytesseract = solver_pytesseract.solve_from_screenshot(dummy_image_path)
        print(f"Pytesseract (指定) 结果: {result_pytesseract}") 