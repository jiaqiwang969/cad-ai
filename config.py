#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理模块
安全地加载环境变量和API配置
"""

import os
from typing import Optional

def load_env_file(env_file: str = ".env") -> None:
    """
    手动加载 .env 文件
    如果没有安装 python-dotenv，这个函数可以作为替代
    """
    try:
        if os.path.exists(env_file):
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key.strip()] = value.strip()
    except Exception as e:
        print(f"警告: 无法加载 {env_file} 文件: {e}")

def get_openai_config() -> dict:
    """
    获取OpenAI API配置
    优先从环境变量读取，如果没有则使用默认值
    """
    
    # 尝试加载 .env 文件
    load_env_file()
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError(
            "未找到 OPENAI_API_KEY 环境变量！\n"
            "请设置环境变量或创建 .env 文件。\n"
            "参考 .env.example 文件的格式。"
        )
    
    config = {
        "api_key": api_key,
        "base_url": os.getenv("OPENAI_BASE_URL", "https://ai.pumpkinai.online/v1"),
        "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        "temperature": float(os.getenv("OPENAI_TEMPERATURE", "0.7")),
        "max_tokens": int(os.getenv("OPENAI_MAX_TOKENS", "200"))
    }
    
    return config

def get_masked_api_key(api_key: str) -> str:
    """
    返回遮蔽的API密钥用于日志显示
    """
    if not api_key:
        return "未设置"
    return f"{api_key[:10]}...{api_key[-4:]}" if len(api_key) > 14 else f"{api_key[:6]}..."

def validate_config(config: dict) -> bool:
    """
    验证配置是否有效
    """
    required_fields = ["api_key", "base_url", "model"]
    for field in required_fields:
        if not config.get(field):
            print(f"❌ 配置错误: {field} 不能为空")
            return False
    
    if not config["api_key"].startswith("sk-"):
        print("❌ 配置错误: API密钥格式不正确")
        return False
    
    return True

if __name__ == "__main__":
    """测试配置加载"""
    try:
        config = get_openai_config()
        print("✅ 配置加载成功:")
        print(f"  API Key: {get_masked_api_key(config['api_key'])}")
        print(f"  Base URL: {config['base_url']}")
        print(f"  Model: {config['model']}")
        print(f"  Temperature: {config['temperature']}")
        print(f"  Max Tokens: {config['max_tokens']}")
        
        if validate_config(config):
            print("✅ 配置验证通过")
        else:
            print("❌ 配置验证失败")
            
    except Exception as e:
        print(f"❌ 配置加载失败: {e}")