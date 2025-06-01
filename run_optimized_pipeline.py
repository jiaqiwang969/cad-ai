#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
优化版Pipeline运行入口
=====================
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.pipelines.optimized_full_pipeline import main

if __name__ == '__main__':
    main() 