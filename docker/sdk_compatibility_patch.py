#!/usr/bin/env python3
"""
Monkey Patch for Claude Agent SDK compatibility with older CLI
Removes --setting-sources parameter that causes issues with claude-code CLI v1.0.109

This patch solves the incompatibility between:
- claude-agent-sdk v0.1.0 (which sends --setting-sources)
- @anthropic-ai/claude-code CLI v1.0.109 (which doesn't recognize it)

Author: Claude & dministrator
Date: 2024-10-05
"""

import logging

logger = logging.getLogger(__name__)


def apply_patch():
    """
    Apply monkey patch to remove --setting-sources parameter from CLI commands
    This allows claude-agent-sdk to work with older claude-code CLI
    """
    try:
        import claude_agent_sdk._internal.transport.subprocess_cli as cli_module
        
        # Save the original method
        _original_build_command = cli_module.SubprocessCLITransport._build_command
        
        def patched_build_command(self):
            """
            Patched version of _build_command that removes --setting-sources parameter
            """
            # Call the original method to get the command
            cmd = _original_build_command(self)
            
            # Remove --setting-sources and its value if present
            # We need to be careful because the parameter might appear multiple times
            while '--setting-sources' in cmd:
                try:
                    idx = cmd.index('--setting-sources')
                    # Remove the flag
                    cmd.pop(idx)
                    # Remove the value (if there's a next element and it's not another flag)
                    if idx < len(cmd) and not cmd[idx].startswith('--'):
                        cmd.pop(idx)
                except (ValueError, IndexError):
                    break
            
            # Log the patched command for debugging
            logger.debug(f"Patched command: {' '.join(cmd)}")
            
            return cmd
        
        # Apply the monkey patch
        cli_module.SubprocessCLITransport._build_command = patched_build_command
        
        print("✅ SDK compatibility patch applied successfully")
        print("   - Removed --setting-sources parameter from CLI commands")
        print("   - claude-agent-sdk should now work with claude-code CLI v1.0.109")
        
        return True
        
    except ImportError as e:
        print(f"❌ Failed to apply patch: {e}")
        print("   Make sure claude-agent-sdk is installed")
        return False
    except Exception as e:
        print(f"❌ Unexpected error while applying patch: {e}")
        return False


def remove_patch():
    """
    Remove the monkey patch and restore original behavior
    (Useful for testing or if you want to revert)
    """
    try:
        import claude_agent_sdk._internal.transport.subprocess_cli as cli_module
        
        # Check if we have the original method stored
        if hasattr(cli_module.SubprocessCLITransport, '_original_build_command'):
            cli_module.SubprocessCLITransport._build_command = \
                cli_module.SubprocessCLITransport._original_build_command
            print("✅ Patch removed, original behavior restored")
            return True
        else:
            print("⚠️  No patch to remove")
            return False
            
    except ImportError:
        print("❌ Cannot remove patch: claude-agent-sdk not found")
        return False


# Auto-apply the patch when this module is imported
if __name__ != "__main__":
    apply_patch()
else:
    # If run directly, show patch status
    print("SDK Compatibility Patch Module")
    print("=" * 40)
    print("This module patches claude-agent-sdk to work with older Claude Code CLI")
    print("\nUsage:")
    print("  import sdk_compatibility_patch  # Auto-applies patch")
    print("  from claude_agent_sdk import query, ClaudeAgentOptions")
    print("  # Now use the SDK normally")
    print("\nTesting patch application...")
    if apply_patch():
        print("\n✅ Test successful - patch can be applied")