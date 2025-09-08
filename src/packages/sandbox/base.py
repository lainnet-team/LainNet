import uuid
from abc import ABC, abstractmethod

from aiohttp import ClientSession
from pydantic import BaseModel, Field


class Sandbox(ABC, BaseModel):
    envd_port: int
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    @abstractmethod
    def start(self):
        pass

    @abstractmethod
    def stop(self):
        pass


class SandboxSession[TSandbox: Sandbox](ABC, BaseModel):
    sandbox: TSandbox

    @property
    def base_url(self) -> str:
        return f"http://localhost:{self.sandbox.envd_port}"

    async def send_request(self, method: str, path: str, **kwargs) -> dict:
        async with ClientSession(base_url=self.base_url) as session:
            response = await session.request(method, path, **kwargs)
            return await response.json()

    async def __aenter__(self):
        await self.sandbox.start()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.sandbox.stop()
