#!/usr/bin/env python3
"""
Simple launcher for the MCP server
"""

import sys
import os

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import and run the server
from mcp_server import main
import asyncio

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        print(f"Server failed: {e}", file=sys.stderr)
        sys.exit(1)