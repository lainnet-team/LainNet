#!/usr/bin/env python3
"""
Test Claude Agent SDK with compatibility patch
This script tests if the monkey patch successfully fixes the --setting-sources issue
"""

import asyncio
import sys
from pathlib import Path

# Add current directory to path so we can import the patch
sys.path.insert(0, str(Path(__file__).parent))

print("=" * 60)
print("Claude Agent SDK with Compatibility Patch Test")
print("=" * 60 + "\n")

# Step 1: Apply the patch BEFORE importing claude_agent_sdk
print("Step 1: Applying compatibility patch...")
try:
    import sdk_compatibility_patch
    print("✅ Patch module imported and applied\n")
except Exception as e:
    print(f"❌ Failed to import patch: {e}")
    sys.exit(1)

# Step 2: Now import claude_agent_sdk
print("Step 2: Importing claude_agent_sdk...")
try:
    from claude_agent_sdk import query, ClaudeAgentOptions
    print("✅ Successfully imported claude_agent_sdk\n")
except ImportError as e:
    print(f"❌ Failed to import claude_agent_sdk: {e}")
    sys.exit(1)


async def test_patched_sdk():
    """Test the patched SDK with a simple query"""
    
    print("Step 3: Testing OAuth authentication with patched SDK...")
    print("-" * 40)
    
    # Check for credentials file
    cred_file = Path.home() / ".claude" / ".credentials.json"
    if not cred_file.exists():
        print("❌ No credentials file found at ~/.claude/.credentials.json")
        print("   Please run 'claude login' first")
        return False
    
    print(f"✅ Found credentials: {cred_file}")
    
    # Test with various options to ensure patch works
    test_cases = [
        {
            "name": "Test 1: No options",
            "options": None,
            "prompt": "Say 'Hello from patched SDK' in 5 words"
        },
        {
            "name": "Test 2: With permission_mode",
            "options": ClaudeAgentOptions(permission_mode='bypassPermissions'),
            "prompt": "Say 'Patch works' in exactly 2 words"
        },
        {
            "name": "Test 3: With multiple options",
            "options": ClaudeAgentOptions(
                permission_mode='bypassPermissions',
                max_turns=1
            ),
            "prompt": "Say 'Success' in 1 word"
        }
    ]
    
    all_passed = True
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n{test['name']}...")
        print(f"  Prompt: {test['prompt']}")
        
        try:
            response_received = False
            error_message = None
            
            # Create async iterator
            message_iterator = query(
                prompt=test['prompt'],
                options=test['options']
            )
            
            # Try to get at least one message
            async for message in message_iterator:
                response_received = True
                print(f"  ✅ Received response: {type(message).__name__}")
                break  # Just need to confirm it works
            
            if response_received:
                print(f"  ✅ Test {i} PASSED")
            else:
                print(f"  ❌ Test {i} FAILED: No response received")
                all_passed = False
                
        except Exception as e:
            print(f"  ❌ Test {i} FAILED: {e}")
            error_str = str(e).lower()
            
            # Check if it's the setting-sources error
            if 'setting-sources' in error_str or 'unknown option' in error_str:
                print("  ⚠️  PATCH DID NOT WORK - still getting setting-sources error")
            else:
                print(f"  ℹ️  Different error (might be network/auth related)")
            
            all_passed = False
    
    return all_passed


async def main():
    """Main test function"""
    print("\n" + "=" * 60)
    print("Starting Tests")
    print("=" * 60)
    
    success = await test_patched_sdk()
    
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    if success:
        print("\n🎉 SUCCESS! The patch works!")
        print("✅ claude-agent-sdk can now be used with claude-code CLI v1.0.109")
        print("✅ OAuth authentication is working")
        print("\nYou can now:")
        print("1. Use this patch in your project")
        print("2. Migrate from claude-code-sdk to claude-agent-sdk")
        print("3. Keep using your existing OAuth credentials")
        return 0
    else:
        print("\n❌ TESTS FAILED")
        print("The patch might not be working correctly, or there might be other issues")
        print("\nTroubleshooting:")
        print("1. Check if claude-code CLI is installed: npm list -g @anthropic-ai/claude-code")
        print("2. Check if you're logged in: claude login")
        print("3. Check the error messages above for more details")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)