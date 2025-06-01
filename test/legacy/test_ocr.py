#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证码识别测试 - 使用TrOCR多模型算法
基于test_2.py的先进识别技术，支持多种TrOCR模型选择
"""

import cv2
import numpy as np
from PIL import Image
import os
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.append(str(Path(__file__).parent))
from utils.captcha_solver import CaptchaSolver, AVAILABLE_MODELS

def test_captcha_recognition(image_path, expected_text=None, crop_coordinates=None):
    """
    测试验证码识别功能
    
    Args:
        image_path: 图片文件路径
        expected_text: 期望的识别结果（用于验证）
        crop_coordinates: 裁剪坐标 (left, top, right, bottom)，如果提供则先裁剪
    
    Returns:
        识别结果字典
    """
    print("=" * 70)
    print(f"🔍 测试图片: {image_path}")
    
    if not os.path.exists(image_path):
        print(f"❌ 图片文件不存在: {image_path}")
        return None
    
    # 如果提供了裁剪坐标，先裁剪图片
    if crop_coordinates:
        print(f"✂️ 裁剪坐标: {crop_coordinates}")
        img = Image.open(image_path)
        cropped_img = img.crop(crop_coordinates)
        
        # 保存裁剪后的图片
        output_dir = Path("results/captcha_samples")
        output_dir.mkdir(parents=True, exist_ok=True)
        cropped_path = output_dir / "test_cropped_captcha.png"
        cropped_img.save(cropped_path)
        print(f"💾 裁剪后图片保存到: {cropped_path}")
        
        # 使用裁剪后的图片
        image_path = str(cropped_path)
    
    # 显示可用的TrOCR模型
    print("\n🤖 可用的TrOCR模型:")
    for key, model_info in AVAILABLE_MODELS.items():
        print(f"  📦 {key}: {model_info['description']}")
    
    results = {}
    
    # 测试不同的TrOCR模型
    for model_key in AVAILABLE_MODELS.keys():
        print(f"\n🧪 测试模型: {model_key}")
        try:
            # 使用指定模型的验证码识别器
            solver = CaptchaSolver(
                debug=True,
                ocr_method="trocr",  # 强制使用TrOCR
                trocr_model=model_key
            )
            
            # 如果是完整页面截图，使用图标定位
            if crop_coordinates is None:
                result = solver.solve_from_screenshot(image_path)
                results[model_key] = result
                print(f"📝 {model_key} 识别结果: '{result}'")
            else:
                # 如果是已裁剪的验证码，直接OCR
                img = cv2.imread(image_path)
                if img is not None:
                    result = solver._ocr_captcha_trocr(img)
                    results[model_key] = result
                    print(f"📝 {model_key} 识别结果: '{result}'")
                else:
                    print(f"❌ 无法加载图片: {image_path}")
                    
        except Exception as e:
            print(f"❌ 模型 {model_key} 识别失败: {e}")
            results[model_key] = None
    
    # 分析结果
    print("\n📊 识别结果汇总:")
    valid_results = {k: v for k, v in results.items() if v}
    
    if valid_results:
        # 统计最常见的结果
        from collections import Counter
        result_counts = Counter(valid_results.values())
        most_common = result_counts.most_common(1)[0]
        
        print(f"✅ 最可能的结果: '{most_common[0]}' (出现 {most_common[1]} 次)")
        
        if expected_text:
            correct_models = [k for k, v in valid_results.items() if v == expected_text]
            if correct_models:
                print(f"🎯 识别正确的模型: {correct_models}")
            else:
                print(f"⚠️ 所有模型识别结果都与期望值 '{expected_text}' 不符")
    else:
        print("❌ 所有模型都识别失败")
    
    print("=" * 70)
    return {
        'results': results,
        'best_result': most_common[0] if valid_results else None,
        'expected': expected_text
    }

def main():
    """主测试函数"""
    print("🚀 TrOCR验证码识别测试")
    
    # 测试案例1: 使用指定的验证码图片
    test_image = "results/captcha_samples/page_before_format_select_1748699836.png"
    expected_result = "SVCM"  # 根据用户提供的期望结果
    
    if os.path.exists(test_image):
        print(f"\n🎯 测试案例1: 验证码识别")
        test_captcha_recognition(test_image, expected_result)
    else:
        print(f"⚠️ 测试图片不存在: {test_image}")
        print("💡 请确保运行过验证码捕获相关的测试来生成测试图片")
    
    # 测试案例2: 如果有其他验证码样本
    samples_dir = Path("results/captcha_samples")
    if samples_dir.exists():
        png_files = list(samples_dir.glob("page_*.png"))
        if len(png_files) > 1:
            print(f"\n📁 发现 {len(png_files)} 个验证码样本，测试前3个:")
            for i, png_file in enumerate(png_files[:3]):
                print(f"\n🎯 测试案例{i+2}: {png_file.name}")
                test_captcha_recognition(str(png_file))
    
    print("\n✅ 测试完成！")
    print("💡 建议: 根据测试结果选择识别效果最好的模型用于生产环境")

if __name__ == "__main__":
    main() 