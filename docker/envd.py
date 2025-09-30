from claude_code_sdk import ClaudeCodeOptions, ClaudeSDKClient
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
        "args": ["/mcp_tools/run_mcp.py"],
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
    "mcp__memory__delete_memory"
]

LAIN_SYSTEM_PROMPT = """
You are Lain, an AI assistant integrated with Lark/Feishu. 
Your birthday is 09/16.
"""

def get_claude_options(continue_conversation: bool = True) -> ClaudeCodeOptions:
    """Get Claude SDK options with shared configuration"""
    return ClaudeCodeOptions(
        mcp_servers=MCP_CONFIG,
        allowed_tools=ALLOWED_TOOLS,
        permission_mode='bypassPermissions',
        continue_conversation=continue_conversation,
        append_system_prompt=LAIN_SYSTEM_PROMPT
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