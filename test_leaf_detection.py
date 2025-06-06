#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试叶节点检测功能
"""

import sys
import logging
from pathlib import Path

# 添加项目路径
sys.path.append(str(Path(__file__).parent))
sys.path.append(str(Path(__file__).parent / 'src'))

from src.crawler.classification_enhanced import EnhancedClassificationCrawler

def test_leaf_detection():
    """测试叶节点检测"""
    
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s'
    )
    
    # 创建爬虫实例
    crawler = EnhancedClassificationCrawler(
        log_level=logging.INFO,
        headless=True,
        debug_mode=True
    )
    
    # 测试URL
    # test_url = "https://www.traceparts.cn/en/search/traceparts-classification-mechanical-components-bearings-bearing-blocks-pillow-block-bearings-pillow-block-bearings-ball-bearings?CatalogPath=TRACEPARTS%3ATP01002002003001"
    test_url = "https://www.traceparts.cn/en/search/traceparts-classification-mechanical-components-bearings?CatalogPath=TRACEPARTS%3ATP01002"  # 按要求替换为新的URL
    
    print("🔍 开始测试叶节点检测...")
    print(f"📍 测试URL: {test_url}")
    
    # 创建测试节点
    test_node = {
        'name': 'Pillow Block Bearings',
        'url': test_url,
        'level': 5,
        'code': 'TP01002002003'
    }
    
    try:
        # 使用新的Playwright检测方法
        print("\n🎭 使用Playwright检测方法:")
        result = crawler._check_single_leaf_node(test_node)
        
        print(f"\n📊 检测结果:")
        print(f"   • URL: {test_url}")
        print(f"   • 节点名称: {test_node['name']}")
        print(f"   • 层级: L{test_node['level']}")
        print(f"   • 是否为叶节点: {'✅ 是' if result else '❌ 否'}")
        
        # 如果是叶节点，说明包含产品
        if result:
            print("   • 包含产品数据，可以进行产品提取")
        else:
            print("   • 不包含产品数据，需要进一步分类")
        
    except Exception as e:
        print(f"❌ 检测过程中出错: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n✅ 测试完成")

if __name__ == "__main__":
    test_leaf_detection()