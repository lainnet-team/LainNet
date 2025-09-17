from claude_code_sdk import ClaudeCodeOptions, ClaudeSDKClient
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


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
    # Configure MCP servers
    mcp_config = {
        "memory": {
            "type": "stdio",
            "command": "python3",
            "args": ["/mcp_tools/run_mcp.py"],
            "env": {}
        }
    }
    
    # Configure options with MCP servers and allowed tools
    options = ClaudeCodeOptions(
        mcp_servers=mcp_config,
        allowed_tools=[
            "mcp__memory__insert_memory",
            "mcp__memory__update_memory",
            "mcp__memory__delete_memory"
        ],
        permission_mode='bypassPermissions',
        continue_conversation=query.continue_conversation,
        # You can customize Lain's System Prompt here
        append_system_prompt="""
You are Lain, an AI assistant integrated with Lark/Feishu. 
Your birthday is 09/16.
"""
    )
    
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