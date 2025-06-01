#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TraceParts 爬虫主入口
====================
使用重构后的模块化架构运行爬虫
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.pipelines.full_pipeline import main

if __name__ == '__main__':
    main() 