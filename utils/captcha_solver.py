#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Captcha 识别工具（简单字符验证码专用）"""

import base64
import io
from typing import Optional

import cv2
import numpy as np
from PIL import Image
import pytesseract

# 若 tesseract 不在 PATH，可手动指定
# pytesseract.pytesseract.tesseract_cmd = '/usr/local/bin/tesseract'

WHITELIST = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'


def preprocess_png_base64(b64_str: str) -> Image.Image:
    """将 base64 PNG 字符串转为二值化 PIL Image"""
    img_data = base64.b64decode(b64_str)
    nparr = np.frombuffer(img_data, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
    # Otsu 二值化
    _, bin_img = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    # 中值滤波去噪
    bin_img = cv2.medianBlur(bin_img, 3)
    return Image.fromarray(bin_img)


def ocr_image(img: Image.Image, psm: int = 7) -> str:
    config = f"--psm {psm} -c tessedit_char_whitelist={WHITELIST}"
    text = pytesseract.image_to_string(img, lang='eng', config=config)
    return text.strip()


def solve_base64_captcha(b64_png: str) -> str:
    img = preprocess_png_base64(b64_png)
    return ocr_image(img)


def solve_file(path: str) -> str:
    img = Image.open(path)
    return ocr_image(img) 