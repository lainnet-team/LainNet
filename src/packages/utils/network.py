import asyncio
import socket
import time

from loguru import logger


async def async_check_ports_ready(host: str, *ports: int) -> bool:
    """
    检查指定 IP 地址的指定端口是否已经全部可以接受连接

    Args:
        host: 实例主机地址
        ports: 端口列表

    Returns:
        bool: 指定 IP 地址的指定端口是否已经全部可以接受连接
    """
    for port in ports:
        try:
            reader, writer = await asyncio.open_connection(host, port)
            writer.close()
            await writer.wait_closed()
        except Exception as e:
            logger.debug(f"检查 {host}:{port} 失败: {e.__class__.__name__} {e}")
            return False
    return True


async def wait_ports_ready(
    host: str, *ports: int, timeout: float = 120, check_interval: float = 1
) -> bool:
    """
    等待端口就绪
    """
    logger.info(
        f"等待 {host} 端口就绪，超时 {timeout} 秒，检查间隔 {check_interval} 秒"
    )
    ports_ready_deadline = time.time() + timeout
    while time.time() < ports_ready_deadline:
        if await async_check_ports_ready(host, *ports):
            logger.info(f"{host} 端口已就绪")
            break
        logger.debug(
            f"等待 {host} 端口就绪，剩余 {int(ports_ready_deadline - time.time())} 秒..."
        )
        await asyncio.sleep(check_interval)
    else:
        logger.warning(f"等待 {host} 端口就绪超时")
        return False
    return True


def available_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("0.0.0.0", 0))
        return s.getsockname()[1]
