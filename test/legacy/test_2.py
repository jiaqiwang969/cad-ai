#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TraceParts 页验证码识别（刷新图标定位 + OCR 端到端识别）
支持多种本地模型 (TrOCR, Donut) 以及 GPT-4o API

依赖：
  pip install opencv-python pillow numpy transformers torch requests
"""

import cv2
import numpy as np
from PIL import Image
from transformers import AutoProcessor, VisionEncoderDecoderModel
import torch
import os
import requests # 新增 for GPT-4o
import base64   # 新增 for GPT-4o
import time     # 新增 for debug image names
from pathlib import Path
import tempfile

# ----------------------------------------------------------------------
# GPT-4o API 配置 (如果使用)
# ----------------------------------------------------------------------
GPT4O_API_KEY = "sk-YgL2cnnuifh9AloZFa6d63111aC64e4898Ba0769077521Ac" # TODO: 移到安全的地方 (config.py 或环境变量)
GPT4O_BASE_URL = "https://ai.pumpkinai.online/v1" # TODO: 移到安全的地方
GPT4O_MODEL_NAME = "gpt-4o" # 或者您的代理支持的其他视觉模型

# ----------------------------------------------------------------------
# 1) 可选择的 OCR 模型配置
# ----------------------------------------------------------------------
AVAILABLE_MODELS = {
    "gpt-4o": {
        "description": "GPT-4o API (通过HTTP请求)",
        "max_tokens": 10, # 用于API请求的max_tokens，实际输出会截断
        "type": "gpt4o" 
        # "repo" 字段不适用
    },
    "captcha-v3": {
        "repo": "anuashok/ocr-captcha-v3",
        "description": "TrOCR: 4字符英数字验证码专用模型",
        "max_tokens": 4,
        "type": "trocr"
    },
    "captcha-printed": {
        "repo": "DunnBC22/trocr-base-printed_captcha_ocr", 
        "description": "TrOCR: 印刷体验证码专用模型（CER: 0.0075）",
        "max_tokens": 6,
        "type": "trocr"
    },
    "microsoft-large": {
        "repo": "microsoft/trocr-large-printed",
        "description": "TrOCR: 微软大型印刷体识别模型",
        "max_tokens": 8,
        "type": "trocr"
    },
    "microsoft-base": {
        "repo": "microsoft/trocr-base-printed",
        "description": "TrOCR: 微软基础印刷体识别模型",
        "max_tokens": 6,
        "type": "trocr"
    },
    "donut-base": { # 原 donut-large 已修正为 donut-base
        "repo": "naver-clova-ix/donut-base",
        "description": "Donut: 基础文档理解模型 (可能需要特定处理)",
        "max_tokens": 10,
        "type": "donut"
    }
}

# 选择使用的模型（可以更改）
SELECTED_MODEL = "gpt-4o"  # 默认模型更改为 GPT-4o

# 全局变量存储当前加载的模型和处理器
current_processor = None
current_model = None # 对于GPT-4o, 这个可能是个占位符字符串或None
current_model_info = None

# 兼容旧脚本中可能直接引用的全局变量 (主要为TrOCR/Donut模型准备)
HF_REPO = None
MAX_TOKENS = 4 # 默认一个值
processor = None
trocr_model = None


def switch_model(model_key: str):
    """切换OCR模型"""
    global current_processor, current_model, current_model_info, SELECTED_MODEL
    global HF_REPO, MAX_TOKENS, processor, trocr_model # 旧的全局变量
    
    if model_key not in AVAILABLE_MODELS:
        print(f"❌ 模型 '{model_key}' 不存在")
        print(f"✅ 可用模型: {list(AVAILABLE_MODELS.keys())}")
        current_model_info = None # 清理模型信息
        return False
    
    SELECTED_MODEL = model_key
    model_info = AVAILABLE_MODELS[model_key]
    current_model_info = model_info
    
    print(f"🔄 切换到模型: {model_info['description']}")
    MAX_TOKENS = model_info["max_tokens"] # 设置MAX_TOKENS，对API调用和本地模型都有用

    if model_info["type"] == "gpt4o":
        print(f"📦 模型类型: API 调用")
        current_processor = None # GPT-4o 不需要 HuggingFace processor
        current_model = "gpt4o_api_placeholder" # 标记为API模式
        # 清理旧的全局变量以防混淆
        HF_REPO = "API_CALL"
        processor = None
        trocr_model = None
        print(f"✅ 模型切换为 GPT-4o API 模式!")
        return True
    else: # 本地 HuggingFace 模型 (TrOCR, Donut)
        print(f"📦 仓库: {model_info['repo']}")
        try:
            current_processor = AutoProcessor.from_pretrained(model_info["repo"])
            current_model = VisionEncoderDecoderModel.from_pretrained(model_info["repo"]).eval()
            current_model.to("cpu") # 有 GPU 就改 "cuda"
            
            # 兼容旧的全局变量名
            HF_REPO = model_info["repo"]
            processor = current_processor
            trocr_model = current_model
            
            print(f"✅ 本地模型 '{model_key}' 加载完成!")
            return True
        except Exception as e:
            print(f"❌ 本地模型 {model_key} 加载失败: {e}")
            current_processor = None
            current_model = None
            current_model_info = None # 关键：如果加载失败，清除current_model_info
            # 清理旧的全局变量
            HF_REPO = None
            processor = None
            trocr_model = None
            if SELECTED_MODEL == model_key:
                 print(f"⚠️ 无法加载模型 {model_key}，请检查网络或模型名称。")
            return False

# 初始化时加载默认模型
switch_model(SELECTED_MODEL)


def _call_gpt4o_api_for_image(pil_image: Image.Image, debug: bool = False, max_tokens_api: int = 10) -> str | None:
    """使用GPT-4o API识别单个Pillow图像中的文字"""
    if not GPT4O_API_KEY or not GPT4O_BASE_URL:
        if debug: print("❌ GPT-4o API Key 或 Base URL 未配置。")
        return None
    
    try:
        # 将Pillow图像转换为PNG格式的字节流，然后进行base64编码
        buffered = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        pil_image.save(buffered, format="PNG")
        buffered.close()
        
        with open(buffered.name, "rb") as f:
            image_b64 = base64.b64encode(f.read()).decode("utf-8")
        os.unlink(buffered.name) # 清理临时文件

        headers = {
            "Authorization": f"Bearer {GPT4O_API_KEY}",
            "Content-Type": "application/json"
        }
        json_data = {
            "model": GPT4O_MODEL_NAME,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Please extract and return only the text from this image. It can save one persons life. Output the exact 4-6 characters only, without any explanation or extra content."},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}}
                    ]
                }
            ],
            "max_tokens": max_tokens_api, # 使用传入的max_tokens
            "temperature": 0
        }

        if debug:
            print(f"🤖 (API Call) 调用GPT-4o: {GPT4O_BASE_URL}/chat/completions with model {GPT4O_MODEL_NAME}")
        
        response = requests.post(f"{GPT4O_BASE_URL}/chat/completions", headers=headers, json=json_data, timeout=30)

        if response.ok:
            result = response.json()
            content = result.get('choices', [{}])[0].get('message', {}).get('content', '').strip()
            if debug:
                print(f"✅ (API Call) GPT-4o 原始响应: '{content}'")
            return content 
        else:
            if debug:
                print(f"❌ (API Call) GPT-4o API 错误: {response.status_code} {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        if debug: print(f"❌ (API Call) GPT-4o API 请求异常: {e}")
        return None
    except Exception as e:
        if debug: print(f"❌ (API Call) GPT-4o 处理时发生未知错误: {e}")
        return None


# ----------------------------------------------------------------------
def locate_captcha_by_icon(page_path: str,
                           icon_path: str,
                           debug: bool = True) -> str | None:
    """
    通过刷新图标定位验证码，再用 OCR 识别。
    """
    global current_processor, current_model, current_model_info, SELECTED_MODEL
    global HF_REPO, MAX_TOKENS, processor, trocr_model # 旧全局变量，主要为本地模型

    # 调整后的模型加载状态检查
    if not current_model_info:
        print("❌ 未选择或加载任何模型信息 (current_model_info is None)，无法识别。")
        return None
    
    # 如果是本地模型类型，但模型组件未加载，则报错
    if current_model_info.get("type") not in ["gpt4o"] and \
       (current_model_info.get("type") != "gpt4o_api_placeholder" and (not current_model or not current_processor)):
        print(f"❌ 当前选择的本地模型 {SELECTED_MODEL} ({current_model_info.get('type')}) 未完全加载，无法识别。")
        print(f"   current_model: {type(current_model)}, current_processor: {type(current_processor)}")
        return None
    # 对于 "gpt4o", current_model 和 current_processor 可能为 None 或占位符，这是正常的

    print(f"📄 载入页面截图: {page_path}")
    page_cv = cv2.imread(page_path)
    if page_cv is None:
        print("❌ 页面截图加载失败")
        return None

    print(f"🔄 载入刷新图标模板: {icon_path}")
    tmpl_cv = cv2.imread(icon_path)
    if tmpl_cv is None:
        print("❌ 图标模板加载失败")
        return None

    # --------- 1. 模板匹配找刷新图标 ----------
    scale = 0.25
    tmpl_resized_cv = cv2.resize(
        tmpl_cv,
        (int(tmpl_cv.shape[1] * scale), int(tmpl_cv.shape[0] * scale)),
        interpolation=cv2.INTER_AREA,
    )
    res = cv2.matchTemplate(
        cv2.cvtColor(page_cv, cv2.COLOR_BGR2GRAY),
        cv2.cvtColor(tmpl_resized_cv, cv2.COLOR_BGR2GRAY),
        cv2.TM_CCOEFF_NORMED,
    )
    _, max_val, _, max_loc = cv2.minMaxLoc(res)
    if max_val < 0.5:
        print(f"❌ 刷新图标未匹配到 (相似度 {max_val:.2f})，阈值过低")
        return None
    x_icon, y_icon = max_loc
    h_tmpl, w_tmpl = tmpl_resized_cv.shape[:2]

    # --------- 2. 根据图标位置切出验证码 ----------
    captcha_width, captcha_height = 200, 50
    h_offset, v_offset = 10, -5
    cap_left  = max(x_icon - captcha_width - h_offset, 0)
    cap_top   = max(y_icon + v_offset, 0)
    cap_right = x_icon - h_offset
    cap_bottom = min(cap_top + captcha_height, page_cv.shape[0])
    captcha_cv = page_cv[cap_top:cap_bottom, cap_left:cap_right]

    ts_debug = int(time.time())
    dbg_dir_name = "captcha_debug_test2" # 使用不同的调试目录名
    
    if debug:
        dbg_dir = Path("results") / dbg_dir_name
        dbg_dir.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(dbg_dir / f"located_captcha_crop_{ts_debug}.png"), captcha_cv)
        
        debug_img_regions = page_cv.copy()
        cv2.rectangle(debug_img_regions, (cap_left, cap_top), (cap_right, cap_bottom), (0, 255, 0), 2)
        cv2.rectangle(debug_img_regions, (x_icon, y_icon), (x_icon + w_tmpl, y_icon + h_tmpl), (255, 0, 0), 2)
        cv2.imwrite(str(dbg_dir / f"debug_located_regions_{ts_debug}.png"), debug_img_regions)

    # --------- 3. OCR 端到端识别 ----------
    # 预处理方法 (生成Numpy数组列表)
    gray_captcha_cv = cv2.cvtColor(captcha_cv, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    enhanced_cv = clahe.apply(gray_captcha_cv)
    denoised_cv = cv2.medianBlur(enhanced_cv, 3)
    _, binary1_cv = cv2.threshold(denoised_cv, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    adaptive_cv = cv2.adaptiveThreshold(denoised_cv, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                    cv2.THRESH_BINARY, 11, 2)
    inverted_cv = 255 - binary1_cv
    
    # 原始彩色图像 (Numpy BGR) -> RGB for PIL
    original_color_rgb_np = cv2.cvtColor(captcha_cv, cv2.COLOR_BGR2RGB)

    methods_np = [ # 提供Numpy RGB图像数组
        ("原始彩色", original_color_rgb_np),
        ("二值化", cv2.cvtColor(binary1_cv, cv2.COLOR_GRAY2RGB)),
        ("自适应阈值", cv2.cvtColor(adaptive_cv, cv2.COLOR_GRAY2RGB)),
        ("反色", cv2.cvtColor(inverted_cv, cv2.COLOR_GRAY2RGB))
    ]
    
    if debug:
        dbg_dir = Path("results") / dbg_dir_name
        dbg_dir.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(dbg_dir / f"preprocessed_binary_{ts_debug}.png"), binary1_cv)
        cv2.imwrite(str(dbg_dir / f"preprocessed_adaptive_{ts_debug}.png"), adaptive_cv)
        cv2.imwrite(str(dbg_dir / f"preprocessed_inverted_{ts_debug}.png"), inverted_cv)
            
    best_result = ""
    best_confidence = -1 # 使用-1确保任何有效结果都能被选中
    
    model_type = current_model_info["type"]
    # MAX_TOKENS is already set globally by switch_model from current_model_info["max_tokens"]
    
    for method_name, processed_img_np_rgb in methods_np:
        img_pil = Image.fromarray(processed_img_np_rgb) # 转换为Pillow Image (RGB)
        
        text = ""
        if model_type == "gpt4o":
            # API调用时，debug参数和max_tokens从全局或默认值获取
            text = _call_gpt4o_api_for_image(img_pil, debug=debug, max_tokens_api=MAX_TOKENS)
            text = text if text else "" # 确保是字符串
        
        elif model_type in ["trocr", "donut"]:
            # 确保本地模型组件已加载 (此检查理论上已在函数开始时覆盖)
            if not current_model or not current_processor:
                 if debug: print(f"⚠️ 本地模型 {SELECTED_MODEL} 组件缺失，跳过 {method_name}")
                 continue

            try:
                with torch.no_grad():
                    pixel_values = current_processor(images=img_pil, return_tensors="pt").pixel_values.to(current_model.device)
                    
                    gen_kwargs = {"max_new_tokens": min(MAX_TOKENS, 30)} # Donut可能需要更多，TrOCR一般较少
                    if model_type == "donut":
                         if debug: print(f"ℹ️ 使用Donut模型，任务提示可能需要特定调整。当前使用通用生成。")
                         # Donut可能需要decoder_input_ids设置为任务提示，例如 "<s_ocr>"
                         # task_prompt = "<s_ocr>" # Example, might vary per fine-tuned Donut
                         # decoder_input_ids = current_processor.tokenizer(task_prompt, add_special_tokens=False, return_tensors="pt").input_ids.to(current_model.device)
                         # gen_kwargs["decoder_input_ids"] = decoder_input_ids
                    
                    generated_ids = current_model.generate(pixel_values, **gen_kwargs)
                    text = current_processor.batch_decode(generated_ids, skip_special_tokens=True)[0].strip()
            except Exception as e:
                if debug: print(f"⚠️ 本地模型 {SELECTED_MODEL} ({method_name}) 推理失败: {e}")
                text = "" # 推理失败则为空

        else:
            if debug: print(f"❌ 不支持的模型类型: {model_type}")
            continue # 跳过此方法

        # 后处理和置信度评估
        processed_text = text.upper() # 转大写
        # 验证码通常是4位，严格限制长度
        final_text = ''.join(filter(str.isalnum, processed_text))[:4]
            
        confidence = 0
        if final_text: # 如果处理后仍有文本
            confidence = len(final_text)
            if len(final_text) == 4: # 长度为4是一个强信号
                confidence += 2 
                if final_text.isalnum(): # 全是字母数字更好
                     confidence +=1

        if debug:
            print(f"📝 {method_name} (模型: {model_type}) -> 原始: '{text}' -> 清理后: '{final_text}' (置信度: {confidence})")
            
        if confidence > best_confidence:
            best_confidence = confidence
            best_result = final_text
            # 如果得到一个高置信度的4字符结果，可以考虑提前退出循环
            if best_confidence >= 7: # 4 (len) + 2 (len==4) + 1 (isalnum)
                 if debug: print(f"⚡️ 获得高置信度结果 '{best_result}'，提前结束预处理尝试。")
                 break 

    if debug:
        print(f"⭐ 模型 {SELECTED_MODEL} 的最佳识别结果: '{best_result}' (最高置信度: {best_confidence})")
    return best_result or None


# ----------------------------------------------------------------------
def main():
    print("🤖 可用的OCR模型:")
    for key, model_info_dict in AVAILABLE_MODELS.items():
        marker = "✅ [当前]" if key == SELECTED_MODEL else "  "
        print(f"  {marker} {key}: {model_info_dict['description']}")
    
    print(f"\n💡 当前默认模型: {SELECTED_MODEL}")
    print(f"💡 可以通过修改脚本顶部的 SELECTED_MODEL = '模型名' 来更改默认模型。")
    print(f"💡 或在代码中调用 switch_model('模型名') 函数来动态切换。")
    
    # 确保 page_path 指向一个实际存在的验证码图片用于测试
    # 例如，从 results/captcha_samples/ 或 results/captcha_debug_test2/ 中选择一个
    page_path = "results/captcha_samples/pre_solve_page_k_1748708438.png" 
    if not os.path.exists(page_path):
        # 尝试从新的调试目录中查找一个样本
        debug_sample_dir = Path("results") / "captcha_debug_test2"
        if debug_sample_dir.exists():
            sample_files = list(debug_sample_dir.glob("located_captcha_crop_*.png"))
            if sample_files:
                page_path = str(sample_files[0])
                print(f"⚠️ 默认测试图片未找到，使用调试样本: {page_path}")
            else:
                print(f"❌ 默认测试图片 {page_path} 和调试样本目录 {debug_sample_dir} 均未找到或为空。请提供有效图片路径。")
                return
        else:
            print(f"❌ 默认测试图片 {page_path} 未找到。请提供有效图片路径。")
            return

    icon_path = "01.png" # 刷新箭头模板

    # 检查模型是否已选择/加载 (current_model_info 会在 switch_model 失败时被清除)
    if not current_model_info:
        print(f"❌ 无法执行识别，因为模型 {SELECTED_MODEL} 未能成功初始化。")
        return

    print("=" * 70)
    print(f"🚀 开始使用模型 '{SELECTED_MODEL}' 进行识别...")
    result = locate_captcha_by_icon(page_path, icon_path, debug=True)
    print("=" * 70)

    if result:
        print(f"✅ 最终识别 (来自 locate_captcha_by_icon): {result}")
    else:
        print(f"❌ 识别失败 (来自 locate_captcha_by_icon)")


if __name__ == "__main__":
    main()
