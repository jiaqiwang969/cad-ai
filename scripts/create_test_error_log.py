#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
创建测试用的错误日志文件
======================
模拟各种错误情况，用于测试错误日志查看功能
"""

import json
from pathlib import Path
from datetime import datetime


def create_test_error_log():
    """创建测试用的错误日志"""
    
    # 创建错误日志目录
    error_logs_dir = Path('results/cache/error_logs')
    error_logs_dir.mkdir(parents=True, exist_ok=True)
    
    # 生成时间戳
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # 模拟错误数据
    error_data = {
        'generated': datetime.now().isoformat(),
        'version': f'v{timestamp}',
        'summary': {
            'total_product_errors': 3,
            'total_specification_errors': 8,
            'zero_specs_count': 5,
            'exception_count': 3
        },
        'details': {
            'products': [
                {
                    'timestamp': datetime.now().isoformat(),
                    'version': f'v{timestamp}',
                    'error_type': 'zero_products',
                    'leaf_code': 'TP12001001',
                    'leaf_name': 'Mobile offices',
                    'leaf_url': 'https://www.traceparts.cn/en/search/traceparts-classification-building-constructions-materials-and-equipments-buildings-mobile-offices?CatalogPath=TRACEPARTS%3ATP12001001',
                    'product_count': 0,
                    'note': '页面访问正常但未找到产品'
                },
                {
                    'timestamp': datetime.now().isoformat(),
                    'version': f'v{timestamp}',
                    'error_type': 'product_extraction_failed',
                    'leaf_code': 'TP12001003',
                    'leaf_name': 'Industrial buildings',
                    'leaf_url': 'https://www.traceparts.cn/en/search/example-url',
                    'exception': 'TimeoutException: Page load timeout after 30 seconds',
                    'exception_type': 'TimeoutException'
                },
                {
                    'timestamp': datetime.now().isoformat(),
                    'version': f'v{timestamp}',
                    'error_type': 'product_extraction_exception',
                    'leaf_code': 'TP12001004',
                    'leaf_name': 'Commercial buildings',
                    'leaf_url': 'https://www.traceparts.cn/en/search/example-url-2',
                    'exception': 'ElementNotFound: Product listing table not found',
                    'exception_type': 'ElementNotFound',
                    'note': '产品链接爬取过程中发生异常'
                }
            ],
            'specifications': [
                {
                    'timestamp': datetime.now().isoformat(),
                    'version': f'v{timestamp}',
                    'error_type': 'zero_specifications',
                    'product_url': 'https://www.traceparts.cn/en/product/example-product-1',
                    'leaf_code': 'TP12001002',
                    'spec_count': 0,
                    'success': True,
                    'note': '页面访问成功但未提取到产品规格'
                },
                {
                    'timestamp': datetime.now().isoformat(),
                    'version': f'v{timestamp}',
                    'error_type': 'zero_specifications',
                    'product_url': 'https://www.traceparts.cn/en/product/example-product-2',
                    'leaf_code': 'TP12001002',
                    'spec_count': 0,
                    'success': True,
                    'note': '页面访问成功但未提取到产品规格'
                },
                {
                    'timestamp': datetime.now().isoformat(),
                    'version': f'v{timestamp}',
                    'error_type': 'specification_extraction_failed',
                    'product_url': 'https://www.traceparts.cn/en/product/example-product-3',
                    'leaf_code': 'TP12001002',
                    'spec_count': 0,
                    'success': False,
                    'exception': 'element click intercepted: Element is not clickable',
                    'note': '产品规格爬取完全失败'
                },
                {
                    'timestamp': datetime.now().isoformat(),
                    'version': f'v{timestamp}',
                    'error_type': 'low_specification_count',
                    'product_url': 'https://www.traceparts.cn/en/product/example-product-4',
                    'leaf_code': 'TP12001002',
                    'spec_count': 1,
                    'success': True,
                    'note': '规格数量较少，可能存在提取问题',
                    'specifications': [
                        {
                            'reference': 'ABC-123',
                            'row_index': 1,
                            'column_name': 'Part Number',
                            'dimensions': '',
                            'weight': '',
                            'table_type': 'horizontal'
                        }
                    ]
                },
                {
                    'timestamp': datetime.now().isoformat(),
                    'version': f'v{timestamp}',
                    'error_type': 'zero_specifications',
                    'product_url': 'https://www.traceparts.cn/en/product/example-product-5',
                    'leaf_code': 'TP12001002',
                    'spec_count': 0,
                    'success': True,
                    'note': '页面访问成功但未提取到产品规格'
                },
                {
                    'timestamp': datetime.now().isoformat(),
                    'version': f'v{timestamp}',
                    'error_type': 'specification_extraction_failed',
                    'product_url': 'https://www.traceparts.cn/en/product/example-product-6',
                    'leaf_code': 'TP12001002',
                    'spec_count': 0,
                    'success': False,
                    'exception': 'NoSuchElementException: Unable to locate element',
                    'note': '产品规格爬取完全失败'
                },
                {
                    'timestamp': datetime.now().isoformat(),
                    'version': f'v{timestamp}',
                    'error_type': 'zero_specifications',
                    'product_url': 'https://www.traceparts.cn/en/product/example-product-7',
                    'leaf_code': 'TP12001002',
                    'spec_count': 0,
                    'success': True,
                    'note': '页面访问成功但未提取到产品规格'
                },
                {
                    'timestamp': datetime.now().isoformat(),
                    'version': f'v{timestamp}',
                    'error_type': 'specification_extraction_failed',
                    'product_url': 'https://www.traceparts.cn/en/product/example-product-8',
                    'leaf_code': 'TP12001002',
                    'spec_count': 0,
                    'success': False,
                    'exception': 'TimeoutException: Waiting for element timed out',
                    'note': '产品规格爬取完全失败'
                }
            ]
        }
    }
    
    # 保存错误日志文件
    error_file = error_logs_dir / f'error_log_v{timestamp}.json'
    with open(error_file, 'w', encoding='utf-8') as f:
        json.dump(error_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 测试错误日志已创建: {error_file}")
    print(f"📊 错误统计:")
    print(f"   • 产品链接失败: {error_data['summary']['total_product_errors']} 个")
    print(f"   • 规格爬取失败: {error_data['summary']['total_specification_errors']} 个")
    print(f"   • 零规格产品: {error_data['summary']['zero_specs_count']} 个")
    print(f"   • 异常数量: {error_data['summary']['exception_count']} 个")
    
    print(f"\n🔍 查看错误日志:")
    print(f"   python run_cache_manager.py --errors")
    
    return error_file


if __name__ == '__main__':
    create_test_error_log() 