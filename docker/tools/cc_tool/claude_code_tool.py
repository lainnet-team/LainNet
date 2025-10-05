#!/usr/bin/env python3
"""
Claude Code Tool - Execute complex tasks using dedicated Claude instances
"""

import json
import uuid
import asyncio
import sys
from pathlib import Path
from typing import Any, Optional

# Apply SDK compatibility patch
sys.path.insert(0, '/app')
try:
    import sdk_compatibility_patch
except Exception:
    pass  # Patch may not be needed in some environments

from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, TextBlock, ToolUseBlock, SystemMessage
from cc_tool_sp import cc_tool_sp

# Tool implementation using @tool decorator
async def claude_code_tool_handler(args: dict[str, Any]) -> dict[str, Any]:
    """
    Execute tasks using a dedicated Claude Code instance
    
    Args:
        instruction: Task to execute
        session_id: Optional session ID to resume
        custom_system_prompt: Optional additional system prompt
        workspace: Optional workspace directory
        permission_mode: Optional permission mode (default: bypassPermissions)
    
    Returns:
        Dictionary with execution result and session_id
    """
    
    # Extract parameters
    instruction = args.get("instruction", "")
    session_id = args.get("session_id")
    custom_system_prompt = args.get("custom_system_prompt", "")
    workspace = args.get("workspace")
    permission_mode = args.get("permission_mode", "bypassPermissions")
    
    # Generate session ID if not provided
    if not session_id:
        session_id = f"cc-{uuid.uuid4().hex[:8]}"
    
    # Setup workspace
    if not workspace:
        workspace = f"/tmp/cc-workspace/{session_id}"
    
    # Ensure workspace exists
    workspace_path = Path(workspace)
    workspace_path.mkdir(parents=True, exist_ok=True)
    
    # Build system prompt
    system_prompt = cc_tool_sp  # Start with the eight principles
    
    # Add expert notice
    system_prompt += "\n\nYou are an expert code executor with excellent development practices."
    system_prompt += f"\nWork within your designated workspace: {workspace}"
    system_prompt += "\nComplete tasks efficiently without unnecessary explanations."
    
    # Append custom prompt if provided
    if custom_system_prompt:
        system_prompt += f"\n\n{custom_system_prompt}"
    
    # Configure Claude Agent options
    options = ClaudeAgentOptions(
        resume=session_id if args.get("session_id") else None,  # Only resume if session_id was provided
        system_prompt=system_prompt,
        permission_mode=permission_mode,
        cwd=workspace,
        allowed_tools=[
            # All standard tools except memory tools
            "Read", "Write", "Edit", "MultiEdit",
            "Bash", "BashOutput", "KillBash",
            "Grep", "Glob",
            "WebSearch", "WebFetch",
            "NotebookEdit",
            "TodoWrite",
            "Task",
            "ExitPlanMode"
        ],
        max_turns=20  # Reasonable limit for task completion
    )
    
    # Execute the task
    result_text = ""
    captured_session_id = session_id
    tool_uses = []
    files_created = []
    files_modified = []
    
    try:
        async for message in query(prompt=instruction, options=options):
            # Capture session ID from init message
            if isinstance(message, SystemMessage):
                if hasattr(message, 'subtype') and message.subtype == 'init':
                    if hasattr(message, 'data') and message.data:
                        captured_session_id = message.data.get('session_id', session_id)
            
            # Collect response text
            elif isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        result_text += block.text + "\n"
                    elif isinstance(block, ToolUseBlock):
                        # Track tool usage
                        tool_uses.append(block.name)
                        
                        # Track file operations
                        if block.name == "Write":
                            file_path = block.input.get("file_path", "")
                            if file_path:
                                files_created.append(file_path)
                        elif block.name in ["Edit", "MultiEdit"]:
                            file_path = block.input.get("file_path", "")
                            if file_path:
                                files_modified.append(file_path)
        
        # Build result summary
        result_summary = {
            "status": "success",
            "session_id": captured_session_id,
            "workspace": workspace,
            "output": result_text.strip(),
            "tools_used": list(set(tool_uses)),
            "files_created": list(set(files_created)),
            "files_modified": list(set(files_modified))
        }
        
    except Exception as e:
        result_summary = {
            "status": "error",
            "session_id": captured_session_id,
            "workspace": workspace,
            "error": str(e),
            "output": result_text.strip() if result_text else "Task failed"
        }
    
    # Return formatted result
    return {
        "content": [{
            "type": "text",
            "text": f"Session: {captured_session_id}\nWorkspace: {workspace}\n\n{result_text.strip()}"
        }],
        "metadata": result_summary
    }


# Export the tool definition for use with create_sdk_mcp_server
claude_code_tool = {
    "name": "claude_code",
    "description": "Execute complex coding tasks using a dedicated Claude instance",
    "schema": {
        "instruction": str,
        "session_id": Optional[str],
        "custom_system_prompt": Optional[str],
        "workspace": Optional[str],
        "permission_mode": Optional[str]
    },
    "handler": claude_code_tool_handler
}