from src.packages.sandbox.cc import claude_sandbox_session
from src.packages.utils.network import available_port


async def main():
    sandbox_id: str = "test-3"
    async with claude_sandbox_session(
        sandbox_id=sandbox_id, envd_port=available_port()
    ) as session:
        response = await session.query("你好")
        print(response)

    async with claude_sandbox_session(
        sandbox_id=sandbox_id, envd_port=available_port()
    ) as session:
        response = await session.query("我们刚刚说了啥")
        print(response)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
