#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速测试5099个产品
==================
使用激进的策略快速加载大量产品
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from src.utils.browser_manager import create_browser_manager


def test_5099_fast():
    """快速测试5099个产品"""
    url = "https://www.traceparts.cn/en/search/traceparts-classification-electrical-electrical-protection-devices-circuit-breakers-molded-case-circuit-breakers-mccb?CatalogPath=TRACEPARTS%3ATP09004001008"
    
    print("⚡ 快速测试5099个产品")
    print("=" * 80)
    
    manager = create_browser_manager(pool_size=1)
    
    try:
        with manager.get_browser() as driver:
            start_time = time.time()
            driver.get(url)
            
            # 等待初始加载
            wait = WebDriverWait(driver, 10)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='&Product=']")))
            
            # 方法1：JavaScript自动点击（最快）
            print("\n📋 使用JavaScript自动点击策略")
            
            # 初始滚动
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(0.5)
            
            # JavaScript代码：快速连续点击
            js_fast_click = """
            let totalClicks = 0;
            let lastCount = 0;
            let noChangeCount = 0;
            const maxClicks = 200;  // 最多点击200次（5099/40 ≈ 128次）
            
            function clickShowMore() {
                const button = document.querySelector('button.more-results');
                const currentCount = document.querySelectorAll('a[href*="&Product="]').length;
                
                console.log(`当前产品数: ${currentCount}`);
                
                // 检查是否达到目标或没有变化
                if (currentCount >= 5000 || totalClicks >= maxClicks || noChangeCount >= 5) {
                    console.log(`停止点击 - 产品数: ${currentCount}, 总点击: ${totalClicks}`);
                    return currentCount;
                }
                
                // 检查产品数是否增加
                if (currentCount === lastCount) {
                    noChangeCount++;
                } else {
                    noChangeCount = 0;
                    lastCount = currentCount;
                }
                
                // 尝试点击按钮
                if (button && button.offsetParent !== null) {
                    button.click();
                    totalClicks++;
                    console.log(`点击 #${totalClicks}`);
                    
                    // 短暂等待后继续
                    setTimeout(() => clickShowMore(), 300);  // 300ms间隔
                } else {
                    // 没有按钮，尝试滚动
                    window.scrollTo(0, document.body.scrollHeight);
                    setTimeout(() => clickShowMore(), 500);
                }
            }
            
            // 开始自动点击
            clickShowMore();
            
            // 返回Promise以便等待
            return new Promise((resolve) => {
                const checkInterval = setInterval(() => {
                    const currentCount = document.querySelectorAll('a[href*="&Product="]').length;
                    if (currentCount >= 5000 || totalClicks >= maxClicks || noChangeCount >= 5) {
                        clearInterval(checkInterval);
                        resolve({
                            count: currentCount,
                            clicks: totalClicks
                        });
                    }
                }, 1000);
                
                // 最多等待60秒
                setTimeout(() => {
                    clearInterval(checkInterval);
                    resolve({
                        count: document.querySelectorAll('a[href*="&Product="]').length,
                        clicks: totalClicks
                    });
                }, 60000);
            });
            """
            
            # 执行自动点击
            result = driver.execute_script(js_fast_click)
            
            # 等待结果（最多60秒）
            print("⏳ 等待自动加载...")
            time.sleep(5)  # 先等待5秒
            
            # 检查进度
            for i in range(55):  # 剩余55秒
                current_count = driver.execute_script("return document.querySelectorAll('a[href*=\"&Product=\"]').length;")
                print(f"\r  进度: {current_count}/5099 产品 ({current_count/5099*100:.1f}%)", end='', flush=True)
                
                if current_count >= 5000:
                    print("\n  ✅ 达到目标！")
                    break
                    
                time.sleep(1)
            
            # 最终结果
            final_count = driver.execute_script("return document.querySelectorAll('a[href*=\"&Product=\"]').length;")
            elapsed = time.time() - start_time
            
            print(f"\n\n📊 最终结果:")
            print(f"  - 产品数: {final_count}/5099 ({final_count/5099*100:.1f}%)")
            print(f"  - 用时: {elapsed:.1f} 秒")
            print(f"  - 速度: {final_count/elapsed:.1f} 个/秒")
            
            # 评估
            print("\n✅ 评估:")
            if final_count >= 5000:
                print("  🎉 完美！获取了几乎所有产品")
            elif final_count >= 3000:
                print("  ✅ 优秀！获取了大部分产品")
            elif final_count >= 1000:
                print("  ⚠️ 一般！可能受到限制")
            else:
                print("  ❌ 需要改进！")
                
            # 获取所有产品链接
            if final_count > 0:
                links = driver.execute_script("""
                    return Array.from(new Set(
                        Array.from(document.querySelectorAll('a[href*="&Product="]'))
                            .map(a => a.href)
                    ));
                """)
                
                print(f"\n💾 实际唯一链接数: {len(links)}")
                
                # 保存结果
                if len(links) >= 1000:
                    import json
                    output_file = "results/test_5099_products.json"
                    os.makedirs("results", exist_ok=True)
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump({
                            'url': url,
                            'total': len(links),
                            'elapsed': elapsed,
                            'products': links[:100]  # 只保存前100个作为示例
                        }, f, indent=2, ensure_ascii=False)
                    print(f"  结果已保存到: {output_file}")
                    
    finally:
        manager.shutdown()
        print("\n✅ 测试完成")


if __name__ == '__main__':
    test_5099_fast() 