from src.packages.sandbox.cc import claude_sandbox_session

class Lain:
    def __init__(self, sandbox_id: str, envd_port: int):
        self.sandbox_id = sandbox_id
        self.envd_port = envd_port

    async def query(self, query: str):
        async with claude_sandbox_session(self.sandbox_id, self.envd_port) as session:
            return await session.query(query)