#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenAI API 访问测试脚本
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openai import OpenAI
from config import get_openai_config, get_masked_api_key, validate_config

def test_openai_api():
    """测试OpenAI API访问"""
    
    # 从环境变量加载API配置
    try:
        config = get_openai_config()
        if not validate_config(config):
            return False
    except Exception as e:
        print(f"❌ 配置加载失败: {e}")
        return False
    
    api_key = config["api_key"]
    base_url = config["base_url"] 
    model = config["model"]
    
    print("=" * 50)
    print("OpenAI API 访问测试")
    print("=" * 50)
    print(f"Base URL: {base_url}")
    print(f"Model: {model}")
    print(f"API Key: {get_masked_api_key(api_key)}")
    print("-" * 50)
    
    try:
        # 创建OpenAI客户端
        client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        
        print("✅ OpenAI客户端创建成功")
        
        # 发送测试消息
        print("🚀 发送测试消息...")
        
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": "你好！请简单介绍一下你自己，并确认你能正常工作。"}
            ],
            temperature=0.7,
            max_tokens=200
        )
        
        print("✅ API调用成功！")
        print("-" * 50)
        print("📝 响应信息:")
        print(f"ID: {response.id}")
        print(f"Model: {response.model}")
        print(f"Created: {response.created}")
        print("-" * 50)
        print("💬 AI回复:")
        print(response.choices[0].message.content)
        print("-" * 50)
        print("📊 Token使用情况:")
        print(f"输入tokens: {response.usage.prompt_tokens}")
        print(f"输出tokens: {response.usage.completion_tokens}")
        print(f"总计tokens: {response.usage.total_tokens}")
        print("=" * 50)
        print("🎉 测试完成！OpenAI API访问正常")
        
        return True
        
    except Exception as e:
        print(f"❌ 错误: {str(e)}")
        print(f"错误类型: {type(e).__name__}")
        print("=" * 50)
        print("⚠️  测试失败！请检查API配置")
        return False

def test_with_environment_variables():
    """使用环境变量测试"""
    print("\n" + "=" * 50)
    print("使用环境变量测试")
    print("=" * 50)
    
    try:
        # 直接使用环境变量创建客户端（OpenAI SDK会自动读取环境变量）
        client = OpenAI()
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": "环境变量测试：1+1等于多少？"}
            ],
            max_tokens=50
        )
        
        print("✅ 环境变量方式访问成功！")
        print(f"回复: {response.choices[0].message.content}")
        return True
        
    except Exception as e:
        print(f"❌ 环境变量方式失败: {str(e)}")
        print("提示：请确保已设置 OPENAI_API_KEY 和 OPENAI_BASE_URL 环境变量")
        return False

if __name__ == "__main__":
    # 测试1: 直接配置方式
    success1 = test_openai_api()
    
    # 测试2: 环境变量方式
    success2 = test_with_environment_variables()
    
    print("\n" + "=" * 50)
    print("测试总结")
    print("=" * 50)
    print(f"直接配置方式: {'✅ 成功' if success1 else '❌ 失败'}")
    print(f"环境变量方式: {'✅ 成功' if success2 else '❌ 失败'}")
    
    if success1 or success2:
        print("🎊 至少一种方式访问成功！OpenAI代理配置正确")
    else:
        print("�� 所有测试都失败了，请检查配置") 