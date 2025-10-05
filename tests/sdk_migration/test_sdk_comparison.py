#!/usr/bin/env python3
"""
对比测试 claude-code-sdk 和 claude-agent-sdk 的行为
验证两者是否使用相同的认证机制
"""
import asyncio
import sys
from pathlib import Path

async def test_both_sdks():
    print("=" * 60)
    print("Claude SDK 兼容性对比测试")
    print("=" * 60 + "\n")
    
    results = {
        'old_sdk': {'installed': False, 'auth_works': False, 'error': None},
        'new_sdk': {'installed': False, 'auth_works': False, 'error': None}
    }
    
    # 测试旧 SDK (claude-code-sdk)
    print("📦 1. 测试 claude-code-sdk")
    print("-" * 40)
    try:
        from claude_code_sdk import ClaudeCodeOptions, ClaudeSDKClient
        results['old_sdk']['installed'] = True
        print("✅ claude-code-sdk 已安装")
        
        # 测试认证
        print("   测试认证和 API 调用...")
        async with ClaudeSDKClient(ClaudeCodeOptions(
            permission_mode='bypassPermissions'
        )) as client:
            await client.query("echo 'Testing old SDK'")
            response_received = False
            async for msg in client.receive_response():
                response_received = True
                break
            
            if response_received:
                results['old_sdk']['auth_works'] = True
                print("   ✅ 认证成功，API 调用正常")
            else:
                print("   ❌ 未收到响应")
                
    except ImportError as e:
        print(f"❌ claude-code-sdk 未安装: {e}")
        results['old_sdk']['error'] = f"Import error: {e}"
    except Exception as e:
        print(f"❌ claude-code-sdk 运行错误: {e}")
        results['old_sdk']['error'] = str(e)
    
    print()
    
    # 测试新 SDK (claude-agent-sdk)
    print("📦 2. 测试 claude-agent-sdk")
    print("-" * 40)
    try:
        # 注意: ClaudeSDKClient 在新版本中仍然叫这个名字
        from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient
        results['new_sdk']['installed'] = True
        print("✅ claude-agent-sdk 已安装")
        
        # 测试认证
        print("   测试认证和 API 调用...")
        async with ClaudeSDKClient(ClaudeAgentOptions(
            permission_mode='bypassPermissions'
        )) as client:
            await client.query("echo 'Testing new SDK'")
            response_received = False
            async for msg in client.receive_response():
                response_received = True
                break
            
            if response_received:
                results['new_sdk']['auth_works'] = True
                print("   ✅ 认证成功，API 调用正常")
            else:
                print("   ❌ 未收到响应")
                
    except ImportError as e:
        print(f"❌ claude-agent-sdk 未安装: {e}")
        results['new_sdk']['error'] = f"Import error: {e}"
    except Exception as e:
        print(f"❌ claude-agent-sdk 运行错误: {e}")
        results['new_sdk']['error'] = str(e)
    
    # 分析结果
    print("\n" + "=" * 60)
    print("📊 测试结果分析")
    print("=" * 60)
    
    print(f"\n旧 SDK (claude-code-sdk):")
    print(f"  - 已安装: {'✅' if results['old_sdk']['installed'] else '❌'}")
    print(f"  - OAuth 认证: {'✅ 工作正常' if results['old_sdk']['auth_works'] else '❌ 失败'}")
    if results['old_sdk']['error']:
        print(f"  - 错误: {results['old_sdk']['error']}")
    
    print(f"\n新 SDK (claude-agent-sdk):")
    print(f"  - 已安装: {'✅' if results['new_sdk']['installed'] else '❌'}")
    print(f"  - OAuth 认证: {'✅ 工作正常' if results['new_sdk']['auth_works'] else '❌ 失败'}")
    if results['new_sdk']['error']:
        print(f"  - 错误: {results['new_sdk']['error']}")
    
    # 结论
    print("\n" + "=" * 60)
    print("🎯 结论")
    print("=" * 60)
    
    if results['old_sdk']['auth_works'] and results['new_sdk']['auth_works']:
        print("\n✅ 两个 SDK 都能使用相同的 OAuth 认证机制")
        print("   可以安全地从 claude-code-sdk 迁移到 claude-agent-sdk")
        print("   认证文件 (~/.claude/.credentials.json) 完全兼容")
        return True
    elif results['old_sdk']['auth_works'] and not results['new_sdk']['auth_works']:
        print("\n⚠️  新 SDK 无法使用现有的 OAuth 认证")
        print("   建议保持使用 claude-code-sdk")
        print("   或等待 claude-agent-sdk 更新")
        return False
    elif not results['old_sdk']['auth_works'] and results['new_sdk']['auth_works']:
        print("\n🔄 只有新 SDK 工作正常")
        print("   可能是 claude-code-sdk 版本问题")
        print("   建议直接迁移到 claude-agent-sdk")
        return True
    else:
        print("\n❌ 两个 SDK 都无法正常工作")
        print("   可能的原因:")
        print("   1. Claude Code CLI 未安装或未登录")
        print("   2. 网络连接问题")
        print("   3. 认证文件损坏")
        return False

async def test_detailed_comparison():
    """更详细的对比测试"""
    print("\n" + "=" * 60)
    print("详细特性对比测试")
    print("=" * 60 + "\n")
    
    # 检查认证文件路径
    cred_file = Path.home() / ".claude" / ".credentials.json"
    print(f"认证文件路径: {cred_file}")
    print(f"文件存在: {'✅' if cred_file.exists() else '❌'}")
    
    if cred_file.exists():
        import json
        with open(cred_file, 'r') as f:
            creds = json.load(f)
            print(f"认证类型: {'OAuth' if 'claudeAiOauth' in creds else 'Unknown'}")
    
    # 检查 Claude Code CLI
    import subprocess
    try:
        result = subprocess.run(['which', 'claude-sandbox'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"\nClaude CLI 位置: {result.stdout.strip()}")
        else:
            print("\n❌ Claude CLI (claude-sandbox) 未找到")
    except:
        pass

def main():
    """主函数"""
    # 运行主要对比测试
    result = asyncio.run(test_both_sdks())
    
    # 运行详细对比
    asyncio.run(test_detailed_comparison())
    
    sys.exit(0 if result else 1)

if __name__ == "__main__":
    main()