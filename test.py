from src.packages.sandbox.cc import ClaudeSandbox, ClaudeSandboxSession, available_port


async def main():
    sandbox_id: str = "test-3"

    # session = ClaudeSandboxSession(sandbox=sandbox)
    # response = await session.query("你好")
    # print(response)
    # await sandbox.stop()
    # print(response)
    # await sandbox.stop()
    # input("Press Enter to continue...")
    # response = await sandbox.query("你好")
    # print(response)
    # await sandbox.stop()
    async with ClaudeSandboxSession(
        sandbox=ClaudeSandbox(id=sandbox_id, envd_port=available_port())
    ) as session:
        response = await session.query("你好")
        print(response)

    async with ClaudeSandboxSession(
        sandbox=ClaudeSandbox(id=sandbox_id, envd_port=available_port())
    ) as session:
        response = await session.query("我们刚刚说了啥")
        print(response)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
