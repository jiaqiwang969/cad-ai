#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复 specifications_optimized.py 中的缩进错误
"""

import re

def fix_indentation():
    """修复 specifications_optimized.py 中的缩进错误"""
    file_path = "src/crawler/specifications_optimized.py"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 修复模式1: try: 后面直接跟opt.click() 缺少缩进
    content = re.sub(
        r'(\s+try:\n)(\s+)(opt\.click\(\))',
        r'\1\2    \3',
        content
    )
    
    # 修复模式2: try: 后面直接跟elem.click() 缺少缩进  
    content = re.sub(
        r'(\s+try:\n)(\s+)(elem\.click\(\))',
        r'\1\2    \3',
        content
    )
    
    # 修复模式3: try: 后面直接跟best_option.click() 缺少缩进
    content = re.sub(
        r'(\s+try:\n)(\s+)(best_option\.click\(\))',
        r'\1\2    \3',
        content
    )
    
    # 修复模式4: try: 后面直接跟max_option.click() 缺少缩进
    content = re.sub(
        r'(\s+try:\n)(\s+)(max_option\.click\(\))',
        r'\1\2    \3',
        content
    )
    
    # 修复模式5: try: 后面直接跟all_option.click() 缺少缩进
    content = re.sub(
        r'(\s+try:\n)(\s+)(all_option\.click\(\))',
        r'\1\2    \3',
        content
    )
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ 已修复所有缩进错误")

if __name__ == "__main__":
    fix_indentation() 