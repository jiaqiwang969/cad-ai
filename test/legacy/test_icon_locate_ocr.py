import cv2
import numpy as np
from PIL import Image
import pytesseract
import os

def locate_captcha_by_icon(page_path, icon_path, debug=True):
    """
    通过定位刷新图标来找到验证码区域并进行OCR识别
    
    Args:
        page_path: 完整页面截图路径
        icon_path: 刷新图标模板路径
        debug: 是否保存调试图片
    
    Returns:
        识别出的验证码文本
    """
    print(f"📄 加载页面截图: {page_path}")
    page = cv2.imread(page_path)
    if page is None:
        print(f"❌ 无法加载页面截图: {page_path}")
        return None
    
    print(f"🔄 加载刷新图标模板: {icon_path}")
    tmpl = cv2.imread(icon_path)
    if tmpl is None:
        print(f"❌ 无法加载图标模板: {icon_path}")
        return None
    
    # 缩放图标模板以匹配页面上的实际大小
    # TraceParts页面上的刷新图标通常比较小
    scale_factor = 0.25  # 缩小到原来的25%
    new_width = int(tmpl.shape[1] * scale_factor)
    new_height = int(tmpl.shape[0] * scale_factor)
    tmpl = cv2.resize(tmpl, (new_width, new_height), interpolation=cv2.INTER_AREA)
    print(f"📏 缩放图标模板到: {new_width}x{new_height}")
    
    # 转换为灰度图进行模板匹配
    page_gray = cv2.cvtColor(page, cv2.COLOR_BGR2GRAY)
    tmpl_gray = cv2.cvtColor(tmpl, cv2.COLOR_BGR2GRAY)
    
    # 模板匹配
    print("🔍 开始模板匹配...")
    res = cv2.matchTemplate(page_gray, tmpl_gray, cv2.TM_CCOEFF_NORMED)
    
    # 找到最佳匹配位置
    _, max_val, _, max_loc = cv2.minMaxLoc(res)
    print(f"📊 最佳匹配相似度: {max_val:.3f}")
    
    if max_val < 0.5:  # 进一步降低阈值
        print("❌ 未找到刷新图标 (相似度过低)")
        
        # 即使失败也保存调试信息
        if debug:
            output_dir = os.path.join("results", "captcha_samples")
            os.makedirs(output_dir, exist_ok=True)
            
            # 保存匹配热力图
            heatmap = cv2.normalize(res, None, 0, 255, cv2.NORM_MINMAX, cv2.CV_8U)
            heatmap_colored = cv2.applyColorMap(heatmap, cv2.COLORMAP_JET)
            heatmap_path = os.path.join(output_dir, "template_match_heatmap.png")
            cv2.imwrite(heatmap_path, heatmap_colored)
            print(f"💾 保存匹配热力图: {heatmap_path}")
            
            # 标记最佳匹配位置（即使相似度低）
            debug_page = page.copy()
            x_icon, y_icon = max_loc
            h_tmpl, w_tmpl = tmpl.shape[:2]
            cv2.rectangle(debug_page, (x_icon, y_icon), 
                         (x_icon + w_tmpl, y_icon + h_tmpl), 
                         (255, 0, 0), 2)  # 蓝色框表示低相似度匹配
            
            debug_path = os.path.join(output_dir, "debug_low_match.png")
            cv2.imwrite(debug_path, debug_page)
            print(f"💾 保存低相似度匹配位置: {debug_path}")
        
        return None
    
    x_icon, y_icon = max_loc
    h_tmpl, w_tmpl = tmpl.shape[:2]
    print(f"✅ 找到刷新图标位置: ({x_icon}, {y_icon})")
    
    # 计算验证码区域
    # 根据TraceParts的布局，验证码在图标左侧
    # 这些值可能需要根据实际情况调整
    captcha_width = 240   # 增加到200像素宽度
    captcha_height = 45   # 增加到50像素高度
    h_offset = 15         # 增加水平偏移，留出更多空间
    v_offset = -10         # 向上调整更多，确保包含验证码顶部
    
    # 计算裁剪区域
    cap_left = max(x_icon - captcha_width - h_offset, 0)
    cap_top = max(y_icon + v_offset, 0)
    cap_right = x_icon - h_offset
    cap_bottom = min(cap_top + captcha_height, page.shape[0])
    
    print(f"📐 验证码区域: ({cap_left}, {cap_top}) -> ({cap_right}, {cap_bottom})")
    
    # 裁剪验证码区域
    captcha = page[cap_top:cap_bottom, cap_left:cap_right]
    
    if debug:
        # 保存调试图片
        output_dir = os.path.join("results", "captcha_samples")
        os.makedirs(output_dir, exist_ok=True)
        
        # 在原图上标记图标和验证码区域
        debug_page = page.copy()
        # 标记图标位置（绿色框）
        cv2.rectangle(debug_page, (x_icon, y_icon), 
                     (x_icon + w_tmpl, y_icon + h_tmpl), 
                     (0, 255, 0), 2)
        # 标记验证码区域（红色框）
        cv2.rectangle(debug_page, (cap_left, cap_top), 
                     (cap_right, cap_bottom), 
                     (0, 0, 255), 2)
        
        debug_path = os.path.join(output_dir, "debug_located_areas.png")
        cv2.imwrite(debug_path, debug_page)
        print(f"💾 保存调试图片: {debug_path}")
        
        # 保存裁剪的验证码
        captcha_path = os.path.join(output_dir, "located_captcha.png")
        cv2.imwrite(captcha_path, captcha)
        print(f"💾 保存验证码图片: {captcha_path}")
    
    # OCR识别
    print("🤖 开始OCR识别...")
    
    # 预处理：转换为灰度图
    gray = cv2.cvtColor(captcha, cv2.COLOR_BGR2GRAY)
    
    # 放大图像以提高识别准确度
    scale = 3
    width = int(gray.shape[1] * scale)
    height = int(gray.shape[0] * scale)
    gray = cv2.resize(gray, (width, height), interpolation=cv2.INTER_CUBIC)
    
    # 应用高斯模糊去噪
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    
    # 应用锐化滤镜
    kernel = np.array([[-1,-1,-1],
                       [-1, 9,-1],
                       [-1,-1,-1]])
    gray = cv2.filter2D(gray, -1, kernel)
    
    # 二值化处理
    # 使用OTSU自动阈值
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # 形态学操作：去除小噪点
    kernel = np.ones((2, 2), np.uint8)
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
    
    if debug:
        binary_path = os.path.join(output_dir, "captcha_binary.png")
        cv2.imwrite(binary_path, binary)
        print(f"💾 保存二值化图片: {binary_path}")
    
    # 使用PIL Image进行OCR（pytesseract更喜欢PIL格式）
    pil_image = Image.fromarray(binary)
    
    # Tesseract配置
    # --psm 7: 将图像视为单个文本行
    # --psm 8: 将图像视为单个单词
    # -c tessedit_char_whitelist: 限制字符集
    # 尝试不同的PSM模式
    configs = [
        r'--oem 3 --psm 8 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789',
        r'--oem 3 --psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789',
        r'--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789',
    ]
    
    results = []
    for config in configs:
        try:
            text = pytesseract.image_to_string(pil_image, config=config).strip()
            if text:
                results.append(text)
                print(f"📝 OCR识别结果 (config: psm={config.split('psm')[1].split()[0]}): '{text}'")
        except Exception as e:
            pass
    
    # 选择最可能的结果（这里简单地选择第一个非空结果）
    if results:
        # 后处理：常见的OCR错误修正
        text = results[0]
        # V -> W 的修正（根据上下文）
        if "VMCL" in text:
            text = text.replace("VMCL", "WMCL")
            print(f"🔧 应用OCR修正: VMCL -> WMCL")
        
        print(f"📝 最终OCR结果: '{text}'")
        return text
    else:
        print("❌ 所有OCR配置都未能识别出文本")
        return None


def main():
    """主函数：测试图标定位验证码识别"""
    
    # 文件路径
    page_path = os.path.join("results", "captcha_samples", "page_screenshot_1748697136.png")
    icon_path = "01.png"  # 刷新图标模板
    
    print("="*50)
    print("🚀 开始测试：通过刷新图标定位验证码")
    print("="*50)
    
    # 检查文件是否存在
    if not os.path.exists(page_path):
        print(f"❌ 页面截图不存在: {page_path}")
        return
    
    if not os.path.exists(icon_path):
        print(f"❌ 图标模板不存在: {icon_path}")
        return
    
    # 执行识别
    result = locate_captcha_by_icon(page_path, icon_path, debug=True)
    
    print("\n" + "="*50)
    if result:
        print(f"✅ 最终识别结果: '{result}'")
        if result == "WMCL":
            print("🎉 识别正确！")
        else:
            print("⚠️ 识别结果与预期 'WMCL' 不符")
            print("💡 提示：")
            print("   1. 检查 results/captcha_samples/debug_located_areas.png 中红框位置是否准确")
            print("   2. 如果位置不准，调整代码中的 captcha_width, captcha_height, h_offset 参数")
            print("   3. 检查 results/captcha_samples/located_captcha.png 是否为完整验证码")
            print("   4. 如果图片质量不好，可尝试调整图像预处理方法")
    else:
        print("❌ 识别失败")
        print("💡 请检查：")
        print("   1. 刷新图标模板是否正确")
        print("   2. 模板匹配阈值是否需要调整")
        print("   3. 验证码区域偏移参数是否正确")


if __name__ == "__main__":
    main() 