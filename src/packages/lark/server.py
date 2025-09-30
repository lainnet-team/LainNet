import asyncio
import json

import lark_oapi as lark
from lark_oapi.api.im.v1 import (
    CreateMessageRequest,
    CreateMessageRequestBody,
    P2ImMessageReceiveV1,
    ReplyMessageRequest,
    ReplyMessageRequestBody,
    ReplyMessageResponse,
    PatchMessageRequest,
    PatchMessageRequestBody,
)
from loguru import logger

from src.packages.sandbox.cc import claude_sandbox_session
from src.packages.sandbox.container_manager import get_container_manager, cleanup_task
from src.packages.utils.network import available_port
from src.packages.utils.settings import Settings

settings = Settings()

# Global container manager
container_manager = get_container_manager(ttl=600)  # 10 minutes TTL

# Start cleanup task
cleanup_task_handle = None


async def send_initial_message(chat_id: str, chat_type: str, message_id: str = None, text: str = "🤖 Lain 正在开机...") -> str:
    """Send initial message and return message ID."""
    content = json.dumps({"text": text})
    
    if chat_type == "p2p":
        request = (
            CreateMessageRequest.builder()
            .receive_id_type("chat_id")
            .request_body(
                CreateMessageRequestBody.builder()
                .receive_id(chat_id)
                .msg_type("text")
                .content(content)
                .build()
            )
            .build()
        )
        response = client.im.v1.message.create(request)
        if response.success():
            return response.data.message_id
    else:
        # For group messages, reply to the original message
        request = (
            ReplyMessageRequest.builder()
            .message_id(message_id)
            .request_body(
                ReplyMessageRequestBody.builder()
                .content(content)
                .msg_type("text")
                .build()
            )
            .build()
        )
        response = client.im.v1.message.reply(request)
        if response.success():
            return response.data.message_id
    return None


async def send_follow_up_message(chat_id: str, text: str):
    """Send a follow-up message instead of updating."""
    content = json.dumps({"text": text})
    request = (
        CreateMessageRequest.builder()
        .receive_id_type("chat_id")
        .request_body(
            CreateMessageRequestBody.builder()
            .receive_id(chat_id)
            .msg_type("text")
            .content(content)
            .build()
        )
        .build()
    )
    response = client.im.v1.message.create(request)
    if not response.success():
        logger.error(f"Failed to send message: {response.msg}")


# 异步处理消息的函数
async def handle_message_async(data: P2ImMessageReceiveV1) -> None:
    user_id = data.event.sender.sender_id.open_id
    chat_id = data.event.message.chat_id
    chat_type = data.event.message.chat_type
    message_id = data.event.message.message_id
    
    # Parse message content
    res_content = ""
    if data.event.message.message_type == "text":
        res_content = json.loads(data.event.message.content)["text"]
    else:
        res_content = "解析消息失败，请发送文本消息\nparse message failed, please send text message"
    
    logger.info(f"res_content: {res_content}")
    
    # Flag to track if we're creating a new container
    creating_new = False
    initial_msg_sent = False
    
    async def on_creating():
        nonlocal creating_new, initial_msg_sent
        creating_new = True
        # Send initial message when creating new container
        await send_initial_message(chat_id, chat_type, message_id, "🤖 Lain 正在开机...")
        initial_msg_sent = True
    
    try:
        # Get or create session using container manager
        session = await container_manager.get_or_create_session(
            user_id=user_id,
            envd_port=available_port(),
            on_creating=on_creating
        )
        
        # If we reused a container, send thinking message
        if not creating_new and not initial_msg_sent:
            await send_initial_message(chat_id, chat_type, message_id, "💭 正在思考...")
            initial_msg_sent = True
        
        # Query the AI
        resp = await session.query(res_content)
        
        logger.info(f"query resp: {resp}")
        resp_text = (
            resp.get("response", "error: query failed")
            if isinstance(resp, dict)
            else str(resp)
        )
        
        # Send final response
        content = json.dumps({"text": resp_text})
        if chat_type == "p2p":
            request = (
                CreateMessageRequest.builder()
                .receive_id_type("chat_id")
                .request_body(
                    CreateMessageRequestBody.builder()
                    .receive_id(chat_id)
                    .msg_type("text")
                    .content(content)
                    .build()
                )
                .build()
            )
            response = client.im.v1.message.create(request)
            if not response.success():
                logger.error(f"Failed to send response: {response.msg}")
        else:
            request = (
                ReplyMessageRequest.builder()
                .message_id(message_id)
                .request_body(
                    ReplyMessageRequestBody.builder()
                    .content(content)
                    .msg_type("text")
                    .build()
                )
                .build()
            )
            response = client.im.v1.message.reply(request)
            if not response.success():
                logger.error(f"Failed to send response: {response.msg}")
        
    except Exception as e:
        logger.error(f"Error handling message: {e}")
        await send_follow_up_message(chat_id, f"❌ 处理消息时出错: {str(e)}")

    # Message sending/updating is now handled inside the handle_message_async function


# 注册接收消息事件，处理接收到的消息。
# Register event handler to handle received messages.
# https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/reference/im-v1/message/events/receive
def do_p2_im_message_receive_v1(data: P2ImMessageReceiveV1) -> None:
    # 创建异步任务来处理消息
    asyncio.create_task(handle_message_async(data))


# 注册事件回调
# Register event handler.
event_handler = (
    lark.EventDispatcherHandler.builder("", "")
    .register_p2_im_message_receive_v1(do_p2_im_message_receive_v1)
    .build()
)


# 创建 LarkClient 对象，用于请求OpenAPI, 并创建 LarkWSClient 对象，用于使用长连接接收事件。
# Create LarkClient object for requesting OpenAPI, and create LarkWSClient object for receiving events using long connection.
client = (
    lark.Client.builder()
    .app_id(settings.app_id)
    .app_secret(settings.app_secret)
    .build()
)
wsClient = lark.ws.Client(
    settings.app_id,
    settings.app_secret,
    event_handler=event_handler,
    log_level=lark.LogLevel.DEBUG,
)


def main():
    #  启动长连接，并注册事件处理器。
    #  Start long connection and register event handler.
    global cleanup_task_handle
    
    # Start cleanup task in background
    loop = asyncio.new_event_loop()
    cleanup_task_handle = loop.create_task(cleanup_task(interval=60))
    
    # Run cleanup task in a separate thread
    import threading
    def run_cleanup():
        asyncio.set_event_loop(loop)
        try:
            loop.run_forever()
        except KeyboardInterrupt:
            pass
    
    cleanup_thread = threading.Thread(target=run_cleanup, daemon=True)
    cleanup_thread.start()
    
    # Start WebSocket client (it has its own event loop)
    try:
        wsClient.start()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        loop.call_soon_threadsafe(loop.stop)


if __name__ == "__main__":
    main()
