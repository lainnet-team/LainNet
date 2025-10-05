#!/usr/bin/env python3
"""
MCP server for Claude Code Tool
Implements stdio-based MCP server for Claude Code delegation
"""

import sys
import os
import json
import asyncio
import logging
from typing import Any, Dict

# Configure logging to stderr to avoid polluting stdout
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from claude_code_tool import claude_code_tool_handler


class CCToolMCPServer:
    """MCP server for Claude Code Tool"""
    
    def __init__(self):
        logger.info("CC Tool MCP Server initialized")
    
    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming JSON-RPC request"""
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")
        
        logger.info(f"Handling request: {method}")
        
        if method == "initialize":
            # Initialize response - matching memory tool format
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": "claude_code",
                        "version": "1.0.0"
                    }
                }
            }
        
        elif method == "tools/list":
            # List tools - the tool name here doesn't need mcp__ prefix
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "tools": [{
                        "name": "claude_code",
                        "description": "Execute complex coding tasks using a dedicated Claude instance with all standard Claude Code tools",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "instruction": {
                                    "type": "string",
                                    "description": "The coding task or instruction to execute"
                                },
                                "session_id": {
                                    "type": "string",
                                    "description": "Optional session ID to resume a previous session"
                                },
                                "custom_system_prompt": {
                                    "type": "string",
                                    "description": "Optional additional system prompt to append to the base prompt"
                                },
                                "workspace": {
                                    "type": "string",
                                    "description": "Optional workspace directory path"
                                },
                                "permission_mode": {
                                    "type": "string",
                                    "description": "Permission mode (default: bypassPermissions)"
                                }
                            },
                            "required": ["instruction"]
                        }
                    }]
                }
            }
        
        elif method == "tools/call":
            # Call a tool
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})
            
            logger.info(f"Calling tool: {tool_name} with args: {tool_args}")
            
            try:
                if tool_name == "claude_code":
                    # Call our existing handler
                    result = await claude_code_tool_handler(tool_args)
                    
                    # Return in MCP format
                    return {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {
                            "content": [
                                {
                                    "type": "text",
                                    "text": json.dumps(result, ensure_ascii=False, indent=2)
                                }
                            ]
                        }
                    }
                else:
                    return {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": -32601,
                            "message": f"Tool not found: {tool_name}"
                        }
                    }
                    
            except Exception as e:
                logger.error(f"Error calling tool {tool_name}: {e}")
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps({
                                    "success": False,
                                    "error": str(e),
                                    "tool": tool_name
                                }, ensure_ascii=False, indent=2)
                            }
                        ]
                    }
                }
        
        else:
            # Unknown method
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            }
    
    async def run(self):
        """Main server loop - read from stdin, write to stdout"""
        logger.info("CC Tool MCP Server starting...")
        
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
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32603,
                        "message": f"Internal error: {str(e)}"
                    }
                }
                sys.stdout.write(json.dumps(error_response) + '\n')
                sys.stdout.flush()


async def main():
    """Main entry point"""
    server = CCToolMCPServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())