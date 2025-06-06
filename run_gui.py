#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TraceParts GUI 启动脚本
======================

快速启动图形界面来查看缓存数据
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    # 导入GUI模块
    from traceparts_gui import TracepartsDataViewer
    import tkinter as tk
    
    print("🚀 启动 TraceParts 数据可视化工具...")
    
    # 创建主窗口
    root = tk.Tk()
    
    # 创建应用实例
    app = TracepartsDataViewer(root)
    
    print("✅ GUI界面已启动！")
    print("📁 默认缓存目录: results/cache")
    print("🎯 左侧导航栏显示数据结构，右侧预留图形可视化")
    
    # 启动主循环
    root.mainloop()
    
except ImportError as e:
    print(f"❌ 导入错误: {e}")
    print("💡 请确保已安装必要的依赖包")
    sys.exit(1)
except Exception as e:
    print(f"❌ 启动失败: {e}")
    sys.exit(1)