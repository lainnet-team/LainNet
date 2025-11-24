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
from src.packages.lark.card_builder import CardBuilder, CardStatus

settings = Settings()

# Global container manager
container_manager = get_container_manager(ttl=600)  # 10 minutes TTL

# Start cleanup task
cleanup_task_handle = None


async def send_initial_card(chat_id: str, chat_type: str, message_id: str = None, status: CardStatus = CardStatus.BOOTING) -> str:
    """Send initial card message and return message ID."""
    card = CardBuilder.create_initial_card(status)
    content = CardBuilder.to_json_string(card)
    
    if chat_type == "p2p":
        request = (
            CreateMessageRequest.builder()
            .receive_id_type("chat_id")
            .request_body(
                CreateMessageRequestBody.builder()
                .receive_id(chat_id)
                .msg_type("interactive")
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
                .msg_type("interactive")
                .build()
            )
            .build()
        )
        response = client.im.v1.message.reply(request)
        if response.success():
            return response.data.message_id
    return None


async def update_card(message_id: str, card: dict):
    """Update an existing card message."""
    content = CardBuilder.to_json_string(card)
    request = (
        PatchMessageRequest.builder()
        .message_id(message_id)
        .request_body(
            PatchMessageRequestBody.builder()
            .content(content)
            .build()
        )
        .build()
    )
    response = client.im.v1.message.patch(request)
    if not response.success():
        logger.error(f"Failed to update card: {response.msg}")
    return response.success()


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
    card_msg_id = None
    
    async def on_creating():
        nonlocal creating_new, card_msg_id
        creating_new = True
        # Send initial card when creating new container
        card_msg_id = await send_initial_card(chat_id, chat_type, message_id, CardStatus.BOOTING)
    
    try:
        # Get or create session using container manager
        session = await container_manager.get_or_create_session(
            user_id=user_id,
            envd_port=available_port(),
            on_creating=on_creating
        )
        
        # If we reused a container, send thinking card
        if not creating_new:
            card_msg_id = await send_initial_card(chat_id, chat_type, message_id, CardStatus.THINKING)
        
        # Update card to show generating status
        if card_msg_id:
            generating_card = CardBuilder.create_status_card(CardStatus.GENERATING)
            await update_card(card_msg_id, generating_card)
        
        # Stream the AI response
        resp_text = ""
        update_counter = 0
        streaming_success = False
        try:
            async for data in session.query_stream(res_content):
                if data.get("content"):
                    resp_text = data["content"]
                    update_counter += 1
                    
                    # Update card every 5 chunks or when done
                    if update_counter % 5 == 0 or data.get("done", False):
                        if card_msg_id:
                            status = CardStatus.COMPLETED if data.get("done") else CardStatus.GENERATING
                            streaming_card = CardBuilder.create_response_card(resp_text, status)
                            await update_card(card_msg_id, streaming_card)
                    
                    if data.get("done"):
                        streaming_success = True
                        break
        except Exception as e:
            # Fallback to non-streaming mode
            logger.warning(f"Streaming failed, falling back to non-streaming: {e}")
            resp = await session.query(res_content)
            logger.info(f"query resp: {resp}")
            resp_text = (
                resp.get("response", "error: query failed")
                if isinstance(resp, dict)
                else str(resp)
            )
            
            # Update card with final response
            if card_msg_id:
                final_card = CardBuilder.create_response_card(resp_text, CardStatus.COMPLETED)
                await update_card(card_msg_id, final_card)
        
        # Only send new card if we don't have a card_msg_id and didn't stream successfully
        if not card_msg_id and not streaming_success:
            # Fallback: send as new card if we don't have message ID
            final_card = CardBuilder.create_response_card(resp_text, CardStatus.COMPLETED)
            content = CardBuilder.to_json_string(final_card)
            
            if chat_type == "p2p":
                request = (
                    CreateMessageRequest.builder()
                    .receive_id_type("chat_id")
                    .request_body(
                        CreateMessageRequestBody.builder()
                        .receive_id(chat_id)
                        .msg_type("interactive")
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
                        .msg_type("interactive")
                        .build()
                    )
                    .build()
                )
                response = client.im.v1.message.reply(request)
                if not response.success():
                    logger.error(f"Failed to send response: {response.msg}")
        
    except Exception as e:
        logger.error(f"Error handling message: {e}")
        # Send or update error card
        if card_msg_id:
            error_card = CardBuilder.create_error_card(str(e))
            await update_card(card_msg_id, error_card)
        else:
            # Send new error card
            error_card = CardBuilder.create_error_card(str(e))
            content = CardBuilder.to_json_string(error_card)
            if chat_type == "p2p":
                request = (
                    CreateMessageRequest.builder()
                    .receive_id_type("chat_id")
                    .request_body(
                        CreateMessageRequestBody.builder()
                        .receive_id(chat_id)
                        .msg_type("interactive")
                        .content(content)
                        .build()
                    )
                    .build()
                )
                client.im.v1.message.create(request)
            else:
                request = (
                    ReplyMessageRequest.builder()
                    .message_id(message_id)
                    .request_body(
                        ReplyMessageRequestBody.builder()
                        .content(content)
                        .msg_type("interactive")
                        .build()
                    )
                    .build()
                )
                client.im.v1.message.reply(request)

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
