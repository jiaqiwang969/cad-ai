#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试实时规格提取功能
演示修改后的 extend_to_specifications 是否能实时写入文件
"""

import sys
import logging
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.pipelines.cache_manager import CacheManager, CacheLevel

def main():
    # 设置日志级别为 INFO
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # 创建缓存管理器（限制并发数便于观察）
    cache_manager = CacheManager(cache_dir='results/cache_test', max_workers=4)
    
    # 测试数据：使用少量产品URL
    test_products = [
        {
            'product_url': 'https://www.traceparts.cn/en/product/roverplastik-spa-rover-wood-blok-bls-slidingdoor-mosquito-net?CatalogPath=TRACEPARTS%3ATP12002018003001&Product=10-06112015-101633',
            'leaf_code': 'TEST001'
        },
        {
            'product_url': 'https://www.traceparts.cn/en/product/roverplastik-spa-rover-wood-blok-blt-slidingdoor-mosquito-net?CatalogPath=TRACEPARTS%3ATP12002018003001&Product=10-06112015-101646',
            'leaf_code': 'TEST002'
        },
        {
            'product_url': 'https://www.traceparts.cn/en/product/roverplastik-spa-rover-wood-blok-bls-slidingdoor-no-mosquito-net?CatalogPath=TRACEPARTS%3ATP12002018003001&Product=10-06112015-101636',
            'leaf_code': 'TEST003'
        }
    ]
    # 构造测试数据结构
    test_data = {
        'leaves': [
            {
                'code': 'TEST001',
                'name': 'Test Category 1',
                'products': [test_products[0]]
            },
            {
                'code': 'TEST002', 
                'name': 'Test Category 2',
                'products': [test_products[1]]
            },
            {
                'code': 'TEST003',
                'name': 'Test Category 3',
                'products': [test_products[2]]
            }
        ]
    }
    
    print(f"\n🧪 测试实时规格提取功能")
    print(f"📁 缓存目录: {cache_manager.specs_cache_dir}")
    print(f"🔢 测试产品数: {len(test_products)}")
    print(f"⚙️  并发线程数: {cache_manager.max_workers}")
    print("="*60)
    
    # 监控缓存目录
    print(f"\n👀 请在另一个终端监控缓存目录:")
    print(f"   watch -n 1 'ls -la {cache_manager.specs_cache_dir}/'")
    print(f"\n🚀 开始测试...\n")
    
    # 运行规格扩展
    try:
        result = cache_manager.extend_to_specifications(test_data)
        print(f"\n✅ 测试完成！")
        
        # 检查结果
        spec_files = list(cache_manager.specs_cache_dir.glob("*.json"))
        print(f"\n📊 结果统计:")
        print(f"   • 生成的规格文件数: {len(spec_files)}")
        for f in spec_files:
            print(f"     - {f.name} ({f.stat().st_size} bytes)")
            
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main() 