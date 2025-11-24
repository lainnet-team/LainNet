#!/usr/bin/env python3
"""
MCP Server for User Memory Tools
Implements stdio-based MCP server for memory management
Matches the original Node.js implementation in /tools/user_memory/index.js
"""

import asyncio
import json
import sys
import logging
import os
import re
from typing import Any, Dict, List, Optional
from pathlib import Path
from datetime import datetime

# Configure logging to stderr to avoid polluting stdout
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)


class MemoryManager:
    """Memory manager that uses CLAUDE.md file format matching Node.js implementation"""
    
    def __init__(self):
        # Use the same path as Node.js: ~/.claude/CLAUDE.md
        self.file_path = Path.home() / '.claude' / 'CLAUDE.md'
        self.ensure_memory_section()
    
    def generate_memory_id(self) -> str:
        """Generate 16-digit string as ID (matching Node.js implementation)"""
        timestamp = str(int(datetime.now().timestamp() * 1000))
        random = str(int(os.urandom(2).hex(), 16) % 1000).zfill(3)
        return timestamp + random
    
    def ensure_memory_section(self):
        """Ensure .claude directory and CLAUDE.md file exist with MEMORIES section"""
        # Create .claude directory if it doesn't exist
        claude_dir = self.file_path.parent
        if not claude_dir.exists():
            claude_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created directory: {claude_dir}")
        
        # Create CLAUDE.md if it doesn't exist
        if not self.file_path.exists():
            initial_content = """
Personal configurations and memories for Lain.

## MEMORIES
<!-- Memory section start -->
<!-- Memory section end -->
"""
            self.file_path.write_text(initial_content, encoding='utf-8')
            logger.info(f"Created CLAUDE.md at {self.file_path}")
            return
        
        # Add MEMORIES section if it doesn't exist
        content = self.file_path.read_text(encoding='utf-8')
        if '## MEMORIES' not in content:
            content += '\n\n## MEMORIES\n<!-- Memory section start -->\n<!-- Memory section end -->\n'
            self.file_path.write_text(content, encoding='utf-8')
    
    def parse_memories(self) -> List[Dict[str, Any]]:
        """Parse memories from CLAUDE.md file"""
        content = self.file_path.read_text(encoding='utf-8')
        memories = []
        
        # Match JSON format memory (same regex pattern as Node.js)
        pattern = r'\{"date":\s*"[^"]+",\s*"memory_id":\s*"(\d+)",\s*"memory":\s*"([^"]*)"\}'
        
        for match in re.finditer(pattern, content):
            full_match = match.group(0)
            try:
                memory_obj = json.loads(full_match)
                memories.append(memory_obj)
            except Exception as e:
                logger.error(f'Failed to parse memory: {e}')
        
        return memories
    
    def insert_memory(self, memory: str) -> Dict[str, Any]:
        """Insert a new memory"""
        content = self.file_path.read_text(encoding='utf-8')
        memory_id = self.generate_memory_id()
        
        # Create standard format memory object (matching Node.js)
        memory_obj = {
            "date": datetime.now().strftime("%Y-%m-%d"),  # YYYY-MM-DD format
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
            'success': True,
            'memory_id': memory_id,
            'date': memory_obj['date'],
            'message': f'Memory saved with ID: {memory_id}',
            'content': memory.strip()
        }
    
    def update_memory(self, memory_id: str, memory: str) -> Dict[str, Any]:
        """Update an existing memory"""
        content = self.file_path.read_text(encoding='utf-8')
        memories = self.parse_memories()
        
        # Find target memory
        target_memory = None
        for m in memories:
            if m['memory_id'] == memory_id:
                target_memory = m
                break
        
        if not target_memory:
            raise Exception(f'Memory {memory_id} does not exist')
        
        # Create new memory object with updated date
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
            'success': True,
            'memory_id': memory_id,
            'date': updated_memory_obj['date'],
            'message': f'Memory {memory_id} has been updated',
            'old_content': target_memory['memory'],
            'new_content': memory.strip()
        }
    
    def delete_memory(self, memory_id: str) -> Dict[str, Any]:
        """Delete a memory"""
        content = self.file_path.read_text(encoding='utf-8')
        memories = self.parse_memories()
        
        # Find target memory
        target_memory = None
        for m in memories:
            if m['memory_id'] == memory_id:
                target_memory = m
                break
        
        if not target_memory:
            raise Exception(f'Memory {memory_id} does not exist')
        
        # Delete memory line (including newline)
        memory_str = json.dumps(target_memory, ensure_ascii=False)
        updated_content = content.replace(memory_str + '\n', '')
        
        self.file_path.write_text(updated_content, encoding='utf-8')
        
        return {
            'success': True,
            'memory_id': memory_id,
            'message': f'Memory {memory_id} has been deleted',
            'deleted_content': target_memory['memory']
        }


class MCPServer:
    """MCP Server implementation for stdio transport"""
    
    def __init__(self):
        self.memory_manager = MemoryManager()
        logger.info("MCP Server initialized with memory tools")
    
    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming JSON-RPC request"""
        method = request.get('method')
        params = request.get('params', {})
        request_id = request.get('id')
        
        logger.info(f"Handling request: {method}")
        
        if method == 'initialize':
            # Initialize response
            return {
                'jsonrpc': '2.0',
                'id': request_id,
                'result': {
                    'protocolVersion': '2024-11-05',
                    'capabilities': {
                        'tools': {}
                    },
                    'serverInfo': {
                        'name': 'user-memory',
                        'version': '1.0.0'
                    }
                }
            }
        
        elif method == 'tools/list':
            # List memory tools with mcp__ prefix - matching Node.js tool descriptions
            return {
                'jsonrpc': '2.0',
                'id': request_id,
                'result': {
                    'tools': [
                        {
                            'name': 'insert_memory',
                            'description': """Use this tool when the user explicitly expresses the intention to add or insert a new memory,
and it is clear they are consciously invoking Lain's memory capability. 
The 'memory' field represents a valuable piece of information extracted from the user's latest message 
that should be remembered from now on. The content must be:
- semantically complete,
- unambiguous,
- expressed as a declarative statement,
- combined with conversation context if necessary for clarity,
- and must not duplicate existing memory entries.""",
                            'inputSchema': {
                                'type': 'object',
                                'properties': {
                                    'memory': {
                                        'type': 'string',
                                        'description': 'The declarative memory content to be inserted, derived from user intent. Must be semantically complete, unambiguous, and expressed as a declarative statement. Combined with conversation context if necessary for clarity.'
                                    }
                                },
                                'required': ['memory']
                            }
                        },
                        {
                            'name': 'update_memory',
                            'description': """Use this tool when the user explicitly requests to change or overwrite an existing memory entry with factual conflict（e.g. old memory user is a girl, but current conversation context indicates that user is a boy）.
The 'memory_id' identifies the target memory to be updated, and the 'memory' field must replace its content.
The new memory content should be semantically complete, unambiguous, and expressed as a declarative statement.""",
                            'inputSchema': {
                                'type': 'object',
                                'properties': {
                                    'memory_id': {
                                        'type': 'string',
                                        'description': 'The unique identifier of the memory entry to be updated.'
                                    },
                                    'memory': {
                                        'type': 'string',
                                        'description': 'The revised declarative memory content that replaces the existing entry. Must be semantically complete, unambiguous, and expressed as a declarative statement. Combined with conversation context if necessary for clarity.'
                                    }
                                },
                                'required': ['memory_id', 'memory']
                            }
                        },
                        {
                            'name': 'delete_memory',
                            'description': """Use this tool when the user explicitly requests to forget, remove, or erase a specific memory entry. 
The operation is irreversible. The 'memory_id' uniquely identifies which memory to delete.""",
                            'inputSchema': {
                                'type': 'object',
                                'properties': {
                                    'memory_id': {
                                        'type': 'string',
                                        'description': 'The unique identifier of the memory entry to be deleted.'
                                    }
                                },
                                'required': ['memory_id']
                            }
                        }
                    ]
                }
            }
        
        elif method == 'tools/call':
            # Call a tool
            tool_name = params.get('name')
            tool_args = params.get('arguments', {})
            
            try:
                result = None
                
                if tool_name == 'insert_memory':
                    result = self.memory_manager.insert_memory(
                        tool_args.get('memory')
                    )
                
                elif tool_name == 'update_memory':
                    result = self.memory_manager.update_memory(
                        tool_args.get('memory_id'),
                        tool_args.get('memory')
                    )
                
                elif tool_name == 'delete_memory':
                    result = self.memory_manager.delete_memory(
                        tool_args.get('memory_id')
                    )
                
                else:
                    return {
                        'jsonrpc': '2.0',
                        'id': request_id,
                        'error': {
                            'code': -32601,
                            'message': f'Tool not found: {tool_name}'
                        }
                    }
                
                # Return the result
                return {
                    'jsonrpc': '2.0',
                    'id': request_id,
                    'result': {
                        'content': [
                            {
                                'type': 'text',
                                'text': json.dumps(result, ensure_ascii=False, indent=2)
                            }
                        ]
                    }
                }
                
            except Exception as e:
                logger.error(f"Error calling tool {tool_name}: {e}")
                return {
                    'jsonrpc': '2.0',
                    'id': request_id,
                    'result': {
                        'content': [
                            {
                                'type': 'text',
                                'text': json.dumps({
                                    'success': False,
                                    'error': str(e),
                                    'tool': tool_name
                                }, ensure_ascii=False, indent=2)
                            }
                        ]
                    }
                }
        
        else:
            # Unknown method
            return {
                'jsonrpc': '2.0',
                'id': request_id,
                'error': {
                    'code': -32601,
                    'message': f'Method not found: {method}'
                }
            }
    
    async def run(self):
        """Main server loop - read from stdin, write to stdout"""
        logger.info("MCP Server starting...")
        
        while True:
            try:
                # Read line from stdin
                line = sys.stdin.readline()
                if not line:
                    logger.info("EOF received, shutting down")
                    break
                
                # Parse JSON-RPC request
                try:
                    request = json.loads(line)
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON: {e}")
                    continue
                
                # Handle the request
                response = await self.handle_request(request)
                
                # Write response to stdout
                response_line = json.dumps(response, ensure_ascii=False) + '\n'
                sys.stdout.write(response_line)
                sys.stdout.flush()
                
            except KeyboardInterrupt:
                logger.info("Keyboard interrupt, shutting down")
                break
            except Exception as e:
                logger.error(f"Server error: {e}")
                # Send error response if possible
                error_response = {
                    'jsonrpc': '2.0',
                    'id': None,
                    'error': {
                        'code': -32603,
                        'message': f'Internal error: {str(e)}'
                    }
                }
                sys.stdout.write(json.dumps(error_response) + '\n')
                sys.stdout.flush()


async def main():
    """Main entry point"""
    server = MCPServer()
    await server.run()


if __name__ == '__main__':
    asyncio.run(main())