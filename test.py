from src.packages.sandbox.cc import ClaudeSandbox


async def main():
    async with ClaudeSandbox() as sandbox:
        exit_code, output = await sandbox.exec(["ps", "aux"])
        print(exit_code)
        print(output)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
