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
    async with ClaudeSDKClient(
        options=ClaudeCodeOptions(continue_conversation=query.continue_conversation)
    ) as client:
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
