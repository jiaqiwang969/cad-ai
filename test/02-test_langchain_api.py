#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LangChain OpenAI API 访问测试脚本
"""

import os
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
from langchain.chains import LLMChain
from langchain.prompts import ChatPromptTemplate, PromptTemplate

def test_basic_langchain():
    """基本的LangChain ChatOpenAI测试"""
    print("=" * 60)
    print("🔗 LangChain ChatOpenAI 基本测试")
    print("=" * 60)
    
    try:
        # 配置OpenAI
        api_key = "sk-YgL2cnnuifh9AloZFa6d63111aC64e4898Ba0769077521Ac"
        base_url = "https://ai.pumpkinai.online/v1"
        model = "gpt-4o-mini"
        
        print(f"🔧 配置信息:")
        print(f"  Base URL: {base_url}")
        print(f"  Model: {model}")
        print(f"  API Key: {api_key[:10]}...")
        print("-" * 60)
        
        # 创建ChatOpenAI实例
        llm = ChatOpenAI(
            model=model,
            openai_api_key=api_key,
            openai_api_base=base_url,
            temperature=0.7,
            max_tokens=200
        )
        
        print("✅ LangChain ChatOpenAI 实例创建成功")
        
        # 测试简单对话
        messages = [
            SystemMessage(content="你是一个友善的AI助手，用中文回答问题。"),
            HumanMessage(content="请简单介绍一下LangChain是什么？")
        ]
        
        print("🚀 发送测试消息...")
        response = llm(messages)
        
        print("✅ API调用成功！")
        print("-" * 60)
        print("💬 AI回复:")
        print(response.content)
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"❌ 错误: {str(e)}")
        print(f"错误类型: {type(e).__name__}")
        print("=" * 60)
        return False

def test_langchain_chain():
    """测试LangChain Chain功能"""
    print("\n" + "=" * 60)
    print("⛓️  LangChain Chain 测试")
    print("=" * 60)
    
    try:
        # 配置
        api_key = "sk-YgL2cnnuifh9AloZFa6d63111aC64e4898Ba0769077521Ac"
        base_url = "https://ai.pumpkinai.online/v1"
        model = "gpt-4o-mini"
        
        # 创建LLM
        llm = ChatOpenAI(
            model=model,
            openai_api_key=api_key,
            openai_api_base=base_url,
            temperature=0.5,
            max_tokens=150
        )
        
        # 创建提示模板
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", "你是一个专业的{domain}专家，请用{language}回答问题。"),
            ("human", "{question}")
        ])
        
        # 创建Chain
        chain = prompt_template | llm
        
        print("✅ LangChain Chain 创建成功")
        
        # 测试Chain
        print("🚀 运行Chain测试...")
        result = chain.invoke({
            "domain": "Python编程",
            "language": "中文",
            "question": "什么是装饰器？请简单解释。"
        })
        
        print("✅ Chain运行成功！")
        print("-" * 60)
        print("💬 Chain回复:")
        print(result.content)
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"❌ Chain测试失败: {str(e)}")
        print(f"错误类型: {type(e).__name__}")
        print("=" * 60)
        return False

def test_environment_variables():
    """使用环境变量测试LangChain"""
    print("\n" + "=" * 60)
    print("🌍 环境变量方式测试 LangChain")
    print("=" * 60)
    
    try:
        # 设置环境变量
        os.environ["OPENAI_API_KEY"] = "sk-YgL2cnnuifh9AloZFa6d63111aC64e4898Ba0769077521Ac"
        os.environ["OPENAI_API_BASE"] = "https://ai.pumpkinai.online/v1"
        
        # 使用环境变量创建LLM（不需要显式传参）
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.3,
            max_tokens=100
        )
        
        print("✅ 环境变量方式创建LLM成功")
        
        # 简单测试
        messages = [HumanMessage(content="用一句话总结人工智能的发展趋势")]
        response = llm(messages)
        
        print("✅ 环境变量方式调用成功！")
        print("-" * 60)
        print("💬 回复:")
        print(response.content)
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"❌ 环境变量测试失败: {str(e)}")
        print("=" * 60)
        return False

def test_streaming():
    """测试流式响应"""
    print("\n" + "=" * 60)
    print("🌊 流式响应测试")
    print("=" * 60)
    
    try:
        api_key = "sk-YgL2cnnuifh9AloZFa6d63111aC64e4898Ba0769077521Ac"
        base_url = "https://ai.pumpkinai.online/v1"
        
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            openai_api_key=api_key,
            openai_api_base=base_url,
            temperature=0.8,
            streaming=True
        )
        
        print("✅ 流式LLM创建成功")
        print("🚀 开始流式响应测试...")
        print("-" * 60)
        print("💬 AI流式回复:")
        
        messages = [HumanMessage(content="请写一首关于春天的短诗")]
        
        # 流式输出
        for chunk in llm.stream(messages):
            print(chunk.content, end="", flush=True)
        
        print("\n" + "=" * 60)
        print("✅ 流式响应测试完成！")
        
        return True
        
    except Exception as e:
        print(f"❌ 流式测试失败: {str(e)}")
        print("=" * 60)
        return False

if __name__ == "__main__":
    print("🎯 开始 LangChain OpenAI API 完整测试")
    
    # 执行各项测试
    test1 = test_basic_langchain()
    test2 = test_langchain_chain()
    test3 = test_environment_variables()
    test4 = test_streaming()
    
    # 测试总结
    print("\n" + "=" * 60)
    print("📊 测试总结")
    print("=" * 60)
    print(f"基本ChatOpenAI测试: {'✅ 成功' if test1 else '❌ 失败'}")
    print(f"Chain功能测试: {'✅ 成功' if test2 else '❌ 失败'}")
    print(f"环境变量测试: {'✅ 成功' if test3 else '❌ 失败'}")
    print(f"流式响应测试: {'✅ 成功' if test4 else '❌ 失败'}")
    print("-" * 60)
    
    successful_tests = sum([test1, test2, test3, test4])
    print(f"成功测试: {successful_tests}/4")
    
    if successful_tests >= 3:
        print("🎊 LangChain配置成功！可以正常使用OpenAI API")
    elif successful_tests >= 1:
        print("⚠️  部分功能正常，建议检查失败的测试")
    else:
        print("😞 所有测试都失败了，请检查配置")
    
    print("=" * 60) 