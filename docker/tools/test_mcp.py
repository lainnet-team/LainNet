#!/usr/bin/env python3
"""
Test script for MCP server
Run this to test basic MCP server functionality
"""

import json
import subprocess
import sys

def test_mcp_server():
    """Test MCP server basic operations"""
    
    # Test messages
    messages = [
        # Initialize
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {}
        },
        # List tools
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        },
        # Test insert memory
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "insert_memory",
                "arguments": {
                    "memory": "This is a test memory from MCP test script"
                }
            }
        }
    ]
    
    # Start the MCP server
    proc = subprocess.Popen(
        ["python3", "run_mcp.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )
    
    try:
        for msg in messages:
            # Send message
            request = json.dumps(msg) + "\n"
            print(f"Sending: {request.strip()}")
            proc.stdin.write(request)
            proc.stdin.flush()
            
            # Read response
            response_line = proc.stdout.readline()
            if response_line:
                response = json.loads(response_line)
                print(f"Response: {json.dumps(response, indent=2)}")
                print("-" * 50)
            else:
                print("No response received")
                break
                
    finally:
        proc.terminate()
        proc.wait()
        
        # Print any stderr output
        stderr_output = proc.stderr.read()
        if stderr_output:
            print("Server logs:")
            print(stderr_output)

if __name__ == "__main__":
    test_mcp_server()