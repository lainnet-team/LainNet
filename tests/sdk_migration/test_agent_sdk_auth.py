#!/usr/bin/env python3
"""
测试 Claude Agent SDK 的 OAuth 认证兼容性
验证是否能够使用现有的 ~/.claude/.credentials.json 文件
"""
import asyncio
import sys
import json
from pathlib import Path

async def test_oauth_compatibility():
    print("=" * 50)
    print("Claude Agent SDK OAuth 认证兼容性测试")
    print("=" * 50 + "\n")
    
    # 1. 检查认证文件
    cred_file = Path.home() / ".claude" / ".credentials.json"
    if not cred_file.exists():
        print("❌ 未找到认证文件: ~/.claude/.credentials.json")
        print("请先运行: claude login")
        return False
    
    print(f"✅ 发现认证文件: {cred_file}")
    
    # 检查认证文件内容
    try:
        with open(cred_file, 'r') as f:
            creds = json.load(f)
            if 'claudeAiOauth' in creds:
                oauth = creds['claudeAiOauth']
                print(f"✅ OAuth 认证类型确认")
                print(f"   - 包含 accessToken: {'accessToken' in oauth}")
                print(f"   - 包含 refreshToken: {'refreshToken' in oauth}")
                print(f"   - 订阅类型: {oauth.get('subscriptionType', 'unknown')}")
    except Exception as e:
        print(f"⚠️  无法读取认证文件详情: {e}")
    
    print("\n" + "-" * 50)
    
    # 2. 尝试导入新 SDK
    print("\n测试 claude-agent-sdk 导入...")
    try:
        from claude_agent_sdk import query, ClaudeAgentOptions
        print("✅ 成功导入 claude_agent_sdk")
    except ImportError as e:
        print(f"❌ 无法导入 claude_agent_sdk: {e}")
        print("\n请先安装: pip install claude-agent-sdk")
        return False
    
    # 3. 测试简单查询（使用 OAuth）
    print("\n" + "-" * 50)
    print("\n测试 SDK 使用 OAuth 认证进行 API 调用...")
    print("发送测试消息: 'Say Hello from Agent SDK in exactly 5 words'")
    
    try:
        response_received = False
        response_text = ""
        
        async for message in query(
            prompt="Say 'Hello from Agent SDK' in exactly 5 words",
            options=ClaudeAgentOptions(
                # 不设置任何 API key，完全依赖 OAuth 文件认证
                permission_mode='bypassPermissions'
                # 注意：setting_sources 参数可能不兼容旧版 CLI
            )
        ):
            response_received = True
            # 尝试提取响应文本
            if hasattr(message, 'content'):
                for block in message.content:
                    if hasattr(block, 'text'):
                        response_text += block.text
            
            print(f"✅ 收到响应类型: {type(message).__name__}")
            
        if response_received:
            print(f"\n✅ OAuth 认证成功！")
            print(f"   响应内容: {response_text[:100] if response_text else '(no text content)'}")
            print("\n" + "🎉 " * 10)
            print("结论: Claude Agent SDK 完全兼容现有的 OAuth 认证机制")
            print("可以安全地进行迁移，无需修改认证方式")
            print("🎉 " * 10)
            return True
        else:
            print("❌ 未收到任何响应")
            return False
            
    except Exception as e:
        print(f"\n❌ 认证或 API 调用失败")
        print(f"   错误类型: {type(e).__name__}")
        print(f"   错误信息: {str(e)}")
        
        # 分析错误原因
        error_msg = str(e).lower()
        if 'not found' in error_msg:
            print("\n可能原因: Claude Code CLI 未安装")
            print("解决方案: npm install -g @anthropic-ai/claude-code")
        elif 'auth' in error_msg or 'credential' in error_msg:
            print("\n可能原因: OAuth 认证格式不兼容")
            print("这表明 Agent SDK 可能使用不同的认证机制")
        elif 'connection' in error_msg:
            print("\n可能原因: 网络连接问题")
        
        return False

def main():
    """主函数"""
    print("\n开始测试...\n")
    result = asyncio.run(test_oauth_compatibility())
    
    print("\n" + "=" * 50)
    if result:
        print("✅ 测试通过 - OAuth 认证兼容")
        sys.exit(0)
    else:
        print("❌ 测试失败 - 需要进一步调查")
        sys.exit(1)

if __name__ == "__main__":
    main()