#!/usr/bin/env python3
"""
最小化测试 - 只测试最基本的功能
不使用任何 v0.1.0 新特性
"""
import asyncio

async def test_minimal():
    print("=" * 50)
    print("最小化兼容性测试")
    print("=" * 50 + "\n")
    
    # 测试导入
    try:
        from claude_agent_sdk import query
        print("✅ 可以导入 claude_agent_sdk.query")
    except ImportError as e:
        print(f"❌ 无法导入: {e}")
        return False
    
    # 测试不带任何选项的查询
    print("\n测试最简单的查询（不带任何选项）...")
    try:
        response_count = 0
        async for message in query(prompt="Say hello"):
            response_count += 1
            print(f"  收到消息 #{response_count}: {type(message).__name__}")
            if response_count >= 1:  # 只要收到任何响应就算成功
                break
        
        if response_count > 0:
            print("\n✅ 基本功能正常！OAuth 认证有效")
            return True
        else:
            print("\n❌ 未收到响应")
            return False
            
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        
        # 分析错误
        error_msg = str(e).lower()
        if 'setting' in error_msg or 'option' in error_msg:
            print("\n问题诊断：")
            print("- Agent SDK 使用了 CLI 不支持的新参数")
            print("- 需要更新 CLI 或降级 SDK")
        elif 'not found' in error_msg:
            print("\n问题诊断：")
            print("- Claude CLI 可能未正确安装")
        
        return False

if __name__ == "__main__":
    result = asyncio.run(test_minimal())
    print("\n" + "=" * 50)
    if result:
        print("结论：可以继续迁移，但需要注意兼容性")
    else:
        print("结论：存在兼容性问题，暂不建议迁移")