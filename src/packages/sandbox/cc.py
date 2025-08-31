import asyncio
import json
import pathlib
import socket
import subprocess
from typing import override

from git import Repo
from loguru import logger

from docker import DockerClient
from docker.models.containers import Container

from ..utils.network import wait_ports_ready
from .base import Sandbox

CLAUDE_SANDBOX_CONFIG = json.load(open("claude-sandbox.config.json"))


class ClaudeSandboxError(Exception): ...


class ClaudeSandbox(Sandbox):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._client: DockerClient = DockerClient()
        self._container: Container = None
        self._processx = None

    @property
    def name(self):
        return f"lainnet-cc-{self.id}"

    def _init_workspace(self) -> tuple[bool, pathlib.Path]:
        workspace = pathlib.Path("./workspaces").absolute() / self.name
        if workspace.exists():
            return True, workspace
        repo = Repo.init(workspace)
        with open(workspace / "claude-sandbox.config.json", "w") as f:
            f.write(json.dumps(CLAUDE_SANDBOX_CONFIG, indent=4))
        repo.index.add(["claude-sandbox.config.json"])
        repo.index.commit("Initial commit")
        return False, workspace

    async def _get_container(self, timeout: int = 60) -> Container:
        for _ in range(timeout):
            containers = self._client.containers.list(filters={"name": self.name})
            if containers:
                logger.info(f"Container {self.name} found, starting...")
                return containers[0]
            else:
                logger.info(f"Container {self.name} not found, waiting for 1 second...")
                await asyncio.sleep(1)

        raise ClaudeSandboxError("Container not found after timeout")

    async def _start_envd(self, port: int, timeout: int = 60):
        cmd = [
            "python3",
            "-m",
            "uvicorn",
            "envd:app",
            "--host",
            "0.0.0.0",
            "--port",
            "8000",
            "--app-dir",
            "/app",
        ]
        self._container.exec_run(cmd, stdout=False, stderr=False)

        ok = await wait_ports_ready("localhost", port, timeout=timeout)
        if not ok:
            raise ClaudeSandboxError("Envd not started after timeout")

    def _available_port(self) -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("0.0.0.0", 0))
            return s.getsockname()[1]

    @override
    async def start(self, timeout: int = 60):
        cmd: list[str]
        existed, workspace = self._init_workspace()
        if existed:
            self._container = await self._get_container(timeout)
            cmd = [
                "claude-sandbox",
                "attach",
                self._container.id,
                "--no-web",
            ]
            self._process = subprocess.Popen(
                cmd, cwd=workspace, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
        else:
            port = self._available_port()
            cmd = [
                "claude-sandbox",
                "start",
                "--name",
                self.name,
                "--no-web",
                "--envd-port",
                str(port),
            ]
            self._process = subprocess.Popen(
                cmd, cwd=workspace, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )

            self._container = await self._get_container(timeout)

            await self._start_envd(port)

    @override
    async def stop(self):
        if self._process is None or self._container is None:
            raise ClaudeSandboxError("Stop Failed: Sandbox not found")
        self._process.terminate()

    async def __aenter__(self, timeout: int = 60):
        await self.start(timeout)
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.stop()

    async def exec(self, cmd: list[str]) -> str:
        if self._container is None:
            raise ClaudeSandboxError("Exec Failed: Sandbox not found")
        result = self._container.exec_run(cmd)
        return result.exit_code, result.output
