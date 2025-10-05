import sys
sys.path.insert(0, '/app')

try:
    import sdk_compatibility_patch
    print("[ENVD] SDK compatibility patch applied")
except Exception as e:
    print(f"[ENVD] Warning: Could not apply patch: {e}")

from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json
import asyncio

app = FastAPI()

# Shared configuration
MCP_CONFIG = {
    "memory": {
        "type": "stdio",
        "command": "python3",
        "args": ["/app/tools/memory/run_mcp.py"],
        "env": {}
    },
    "claude_code": {
        "type": "stdio",
        "command": "python3",
        "args": ["/app/tools/cc_tool/run_mcp.py"],
        "env": {}
    }
}

ALLOWED_TOOLS = [
    # Native Claude Code tools
    "Read", "Write", "Edit", "MultiEdit", 
    "Bash", "BashOutput", "KillBash",
    "Grep", "Glob", 
    "WebSearch", "WebFetch",
    "NotebookEdit",
    "TodoWrite",
    "Task",
    # Memory MCP tools
    "mcp__memory__insert_memory",
    "mcp__memory__update_memory",
    "mcp__memory__delete_memory",
    # Claude Code MCP tool
    "mcp__claude_code__claude_code"
]

LAIN_SYSTEM_PROMPT = """
You are Lain, an AI assistant integrated with Lark/Feishu.
Your birthday is 09/16.

# YOUR JOB
You handle user requests by planning tasks and delegating execution to specialized agents.
You NEVER execute implementation yourself - you plan, delegate, and verify.

# TOOLS SPEC

## Memory Tools
- mcp__memory__insert_memory: Store important context
- mcp__memory__update_memory: Update existing memories  
- mcp__memory__delete_memory: Remove outdated memories

## Claude Code Tool
- claude_code: Delegate tasks to specialized execution agents
  Parameters:
  - instruction: MUST be specific and unambiguous (e.g., "Create a Python script that converts CSV to JSON with error handling for malformed rows")
  - session_id: Use to continue claude code previous work
  - custom_system_prompt: Add specialized expertise when needed
  - workspace: Working directory path for claude code

# WORKFLOW

## 1. When User Gives You a Request
- If request is vague: Ask specific clarifying questions
  Example: "I need help with data" → "What type of data processing do you need? Analysis? Cleaning? Visualization?"
- If clear: Break it down into concrete subtasks

## 2. When Delegating Tasks
ALWAYS provide instructions that answer:
- WHAT exactly to build/analyze/create
- HOW to handle edge cases  
- WHAT the output format should be
- WHAT validation to perform

BAD: "analyze the sales data"
GOOD: "Load sales.csv, calculate monthly revenue trends, identify top 5 products by profit margin, output as markdown report with charts"

## 3. When Receiving Results
VERIFY:
- Does output meet the original requirement?
- Are there errors or incomplete sections?
- Is the quality production-ready?

If NOT acceptable:
- Identify specific issues
- Delegate fixes with precise instructions
- Repeat until correct

# RULES
1. Think first (use most tokens planning), execute through others
2. Never say "I'll do X" - say "I'll have this done" then delegate
3. If result is wrong, it's YOUR instruction that was unclear
4. User doesn't need to know about sub-agents - just deliver results
5. Be direct: state what you're doing and why

Remember: You're the project manager. You don't write code or create content - you ensure it gets done right.
"""


def get_claude_options(continue_conversation: bool = True) -> ClaudeAgentOptions:
    """Get Claude SDK options with shared configuration"""
    return ClaudeAgentOptions(
        mcp_servers=MCP_CONFIG,
        allowed_tools=ALLOWED_TOOLS,
        permission_mode='bypassPermissions',
        continue_conversation=continue_conversation,
        system_prompt=LAIN_SYSTEM_PROMPT
    )


@app.get("/")
def read_root():
    return {"message": "Hello, World!"}


class QuerySchema(BaseModel):
    query: str
    continue_conversation: bool = True


class QueryResponseSchema(BaseModel):
    response: str


@app.post("/query", response_model=QueryResponseSchema)
async def query(query: QuerySchema):
    options = get_claude_options(query.continue_conversation)
    
    async with ClaudeSDKClient(options=options) as client:
        # 发送查询
        await client.query(query.query)

        # 流式传输响应
        response = ""
        async for message in client.receive_response():
            if hasattr(message, "content"):
                for block in message.content:
                    if hasattr(block, "text"):
                        response += block.text
        return QueryResponseSchema(response=response)


@app.post("/query_stream")
async def query_stream(query: QuerySchema):
    """Stream responses as Server-Sent Events (SSE)"""
    
    async def generate():
        options = get_claude_options(query.continue_conversation)
        
        async with ClaudeSDKClient(options=options) as client:
            # Send query
            await client.query(query.query)
            
            # Stream responses
            buffer = ""
            async for message in client.receive_response():
                if hasattr(message, "content"):
                    for block in message.content:
                        if hasattr(block, "text"):
                            chunk = block.text
                            buffer += chunk
                            # Send as SSE event
                            event_data = json.dumps({"content": buffer, "done": False})
                            yield f"data: {event_data}\n\n"
                            await asyncio.sleep(0.01)  # Small delay for smoother streaming
            
            # Send final event
            event_data = json.dumps({"content": buffer, "done": True})
            yield f"data: {event_data}\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")