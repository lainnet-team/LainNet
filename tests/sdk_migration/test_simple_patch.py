#!/usr/bin/env python3
"""
Simple test for Claude Agent SDK with compatibility patch
"""

import asyncio
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Apply patch before importing SDK
import sdk_compatibility_patch
from claude_agent_sdk import query, ClaudeAgentOptions


async def test_simple():
    """Simple test to verify the patch works"""
    
    print("=" * 60)
    print("Testing Claude Agent SDK with Compatibility Patch")
    print("=" * 60 + "\n")
    
    # Check credentials
    cred_file = Path.home() / ".claude" / ".credentials.json"
    if not cred_file.exists():
        print("❌ No credentials file found")
        return False
    
    print(f"✅ Credentials found: {cred_file}")
    
    # Simple test - just see if we can connect without error
    print("\nTesting connection with patched SDK...")
    
    try:
        messages_received = 0
        async for message in query(
            prompt="Reply with exactly: 'PATCH_SUCCESS'",
            options=ClaudeAgentOptions(permission_mode='bypassPermissions')
        ):
            messages_received += 1
            print(f"✅ Message {messages_received}: {type(message).__name__}")
            
            # Check for response content
            if hasattr(message, 'content'):
                for block in message.content:
                    if hasattr(block, 'text') and 'PATCH_SUCCESS' in block.text:
                        print(f"✅ Got expected response: {block.text}")
            
            # Don't break early to avoid asyncio issues
        
        if messages_received > 0:
            print(f"\n✅ SUCCESS! Received {messages_received} messages")
            print("🎉 The patch works - claude-agent-sdk is now compatible with claude-code CLI")
            return True
        else:
            print("\n❌ No messages received")
            return False
            
    except Exception as e:
        error_str = str(e).lower()
        if 'setting-sources' in error_str or 'unknown option' in error_str:
            print(f"\n❌ Patch failed - still getting setting-sources error: {e}")
        else:
            print(f"\n⚠️  Different error (may be unrelated to patch): {e}")
        return False


def main():
    """Run the test"""
    success = asyncio.run(test_simple())
    
    print("\n" + "=" * 60)
    if success:
        print("✅ Test PASSED - You can now use claude-agent-sdk!")
        print("\nNext steps:")
        print("1. Add 'import sdk_compatibility_patch' to your code")
        print("2. Use claude_agent_sdk instead of claude_code_sdk")
        print("3. Update your Docker container to include the patch")
        return 0
    else:
        print("❌ Test FAILED - Check the errors above")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)