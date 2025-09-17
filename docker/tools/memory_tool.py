#!/usr/bin/env python3
"""
Memory management tools for Lain Main Agent.
Python implementation of the user_memory MCP server.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from claude_code_sdk import tool

# Memory file path (inside container)
CLAUDE_MD_PATH = Path("/home/claude/.claude/CLAUDE.md")


class MemoryManager:
    """Manager for CLAUDE.md memory operations."""
    
    def __init__(self):
        self.file_path = CLAUDE_MD_PATH
        self.ensure_memory_section()
    
    def generate_memory_id(self) -> str:
        """Generate 16-digit string as ID."""
        import time
        import random
        # Node.js: Date.now() returns milliseconds since epoch
        # Python: time.time() returns seconds, so multiply by 1000
        timestamp = str(int(time.time() * 1000))  # Full timestamp in milliseconds
        # Node.js: Math.floor(Math.random() * 1000).toString().padStart(3, '0')
        # Generate random 3-digit number (000-999)
        random_num = str(random.randint(0, 999)).zfill(3)  # Pad with zeros to ensure 3 digits
        return timestamp + random_num
    
    def ensure_memory_section(self):
        """Ensure CLAUDE.md exists with MEMORIES section."""
        # Create .claude directory if it doesn't exist
        claude_dir = self.file_path.parent
        claude_dir.mkdir(parents=True, exist_ok=True)
        
        # Create CLAUDE.md if it doesn't exist
        if not self.file_path.exists():
            initial_content = """Personal configurations and memories for Lain.

## MEMORIES
<!-- Memory section start -->
<!-- Memory section end -->
"""
            self.file_path.write_text(initial_content, encoding='utf-8')
            return
        
        # Add MEMORIES section if it doesn't exist
        content = self.file_path.read_text(encoding='utf-8')
        if '## MEMORIES' not in content:
            content += '\n\n## MEMORIES\n<!-- Memory section start -->\n<!-- Memory section end -->\n'
            self.file_path.write_text(content, encoding='utf-8')
    
    def parse_memories(self) -> List[Dict[str, Any]]:
        """Parse memories from CLAUDE.md."""
        content = self.file_path.read_text(encoding='utf-8')
        memories = []
        
        # Match JSON format memory
        # More flexible regex to handle various JSON formatting
        import re
        # This pattern matches JSON objects with date, memory_id, and memory fields
        # Allows for different spacing and handles escaped quotes in memory content
        pattern = r'\{[^{}]*"date"\s*:\s*"[^"]+"\s*,\s*"memory_id"\s*:\s*"(\d+)"\s*,\s*"memory"\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)"\s*\}'
        
        for match in re.finditer(pattern, content):
            try:
                # Parse the matched JSON string
                memory_obj = json.loads(match.group(0))
                memories.append(memory_obj)
            except json.JSONDecodeError:
                # Skip malformed JSON
                continue
        
        return memories
    
    def insert_memory(self, memory: str) -> Dict[str, Any]:
        """Insert a new memory."""
        content = self.file_path.read_text(encoding='utf-8')
        memory_id = self.generate_memory_id()
        
        # Create standard format memory object
        memory_obj = {
            "date": datetime.now().strftime("%Y-%m-%d"),  # YYYY-MM-DD
            "memory_id": memory_id,
            "memory": memory.strip()
        }
        
        new_memory_line = json.dumps(memory_obj, ensure_ascii=False) + '\n'
        
        # Insert new memory before memory region end marker
        updated_content = content.replace(
            '<!-- Memory section end -->',
            f'{new_memory_line}<!-- Memory section end -->'
        )
        
        self.file_path.write_text(updated_content, encoding='utf-8')
        
        return {
            "success": True,
            "memory_id": memory_id,
            "date": memory_obj["date"],
            "message": f"Memory saved with ID: {memory_id}",
            "content": memory.strip()
        }
    
    def update_memory(self, memory_id: str, memory: str) -> Dict[str, Any]:
        """Update an existing memory."""
        content = self.file_path.read_text(encoding='utf-8')
        memories = self.parse_memories()
        
        # Find target memory
        target_memory = None
        for m in memories:
            if m.get("memory_id") == memory_id:
                target_memory = m
                break
        
        if not target_memory:
            raise ValueError(f"Memory {memory_id} does not exist")
        
        # Create new memory object
        updated_memory_obj = {
            "date": datetime.now().strftime("%Y-%m-%d"),  # Update date
            "memory_id": memory_id,
            "memory": memory.strip()
        }
        
        # Replace old memory
        old_memory_str = json.dumps(target_memory, ensure_ascii=False)
        new_memory_str = json.dumps(updated_memory_obj, ensure_ascii=False)
        updated_content = content.replace(old_memory_str, new_memory_str)
        
        self.file_path.write_text(updated_content, encoding='utf-8')
        
        return {
            "success": True,
            "memory_id": memory_id,
            "date": updated_memory_obj["date"],
            "message": f"Memory {memory_id} has been updated",
            "old_content": target_memory["memory"],
            "new_content": memory.strip()
        }
    
    def delete_memory(self, memory_id: str) -> Dict[str, Any]:
        """Delete a memory."""
        content = self.file_path.read_text(encoding='utf-8')
        memories = self.parse_memories()
        
        # Find target memory
        target_memory = None
        for m in memories:
            if m.get("memory_id") == memory_id:
                target_memory = m
                break
        
        if not target_memory:
            raise ValueError(f"Memory {memory_id} does not exist")
        
        # Delete memory line (including newline)
        memory_str = json.dumps(target_memory, ensure_ascii=False)
        updated_content = content.replace(memory_str + '\n', '')
        
        self.file_path.write_text(updated_content, encoding='utf-8')
        
        return {
            "success": True,
            "memory_id": memory_id,
            "message": f"Memory {memory_id} has been deleted",
            "deleted_content": target_memory["memory"]
        }


# Create global memory manager instance
memory_manager = MemoryManager()


# Define MCP tools using @tool decorator
@tool(
    "insert_memory",
    """Use this tool when the user explicitly expresses the intention to add or insert a new memory,
and it is clear they are consciously invoking Lain's memory capability. 
The 'memory' field represents a valuable piece of information extracted from the user's latest message 
that should be remembered from now on. The content must be:
- semantically complete,
- unambiguous,
- expressed as a declarative statement,
- combined with conversation context if necessary for clarity,
- and must not duplicate existing memory entries.""",
    {"memory": str}
)
async def insert_memory(args: Dict[str, Any]) -> Dict[str, Any]:
    """Insert a new memory."""
    try:
        result = memory_manager.insert_memory(args["memory"])
        return {
            "content": [{
                "type": "text",
                "text": json.dumps(result, ensure_ascii=False, indent=2)
            }]
        }
    except Exception as e:
        return {
            "content": [{
                "type": "text",
                "text": json.dumps({
                    "success": False,
                    "error": str(e),
                    "tool": "insert_memory"
                }, ensure_ascii=False, indent=2)
            }]
        }


@tool(
    "update_memory",
    """Use this tool when the user explicitly requests to change or overwrite an existing memory entry with factual conflict
（e.g. old memory user is a girl, but current conversation context indicates that user is a boy）.
The 'memory_id' identifies the target memory to be updated, and the 'memory' field must replace its content.
The new memory content should be semantically complete, unambiguous, and expressed as a declarative statement.""",
    {"memory_id": str, "memory": str}
)
async def update_memory(args: Dict[str, Any]) -> Dict[str, Any]:
    """Update an existing memory."""
    try:
        result = memory_manager.update_memory(args["memory_id"], args["memory"])
        return {
            "content": [{
                "type": "text",
                "text": json.dumps(result, ensure_ascii=False, indent=2)
            }]
        }
    except Exception as e:
        return {
            "content": [{
                "type": "text",
                "text": json.dumps({
                    "success": False,
                    "error": str(e),
                    "tool": "update_memory"
                }, ensure_ascii=False, indent=2)
            }]
        }


@tool(
    "delete_memory",
    """Use this tool when the user explicitly requests to forget, remove, or erase a specific memory entry. 
The operation is irreversible. The 'memory_id' uniquely identifies which memory to delete.""",
    {"memory_id": str}
)
async def delete_memory(args: Dict[str, Any]) -> Dict[str, Any]:
    """Delete a memory."""
    try:
        result = memory_manager.delete_memory(args["memory_id"])
        return {
            "content": [{
                "type": "text",
                "text": json.dumps(result, ensure_ascii=False, indent=2)
            }]
        }
    except Exception as e:
        return {
            "content": [{
                "type": "text",
                "text": json.dumps({
                    "success": False,
                    "error": str(e),
                    "tool": "delete_memory"
                }, ensure_ascii=False, indent=2)
            }]
        }


# Export the tools for use in envd.py
memory_tools = [insert_memory, update_memory, delete_memory]