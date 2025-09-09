import asyncio
import json
import pathlib
import subprocess
import os
from datetime import datetime
from typing import override

from git import Repo
from loguru import logger

from docker import DockerClient
from docker.models.containers import Container
from src.packages.utils.settings import Settings

from .base import Sandbox, SandboxSession

CLAUDE_SANDBOX_CONFIG = json.load(open("claude-sandbox.config.json"))


class ClaudeSandboxError(Exception): ...


class ClaudeSandbox(Sandbox):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._client: DockerClient = DockerClient()
        self._container: Container = None
        self._process = None

    @property
    def name(self):
        return f"lainnet-cc-{self.id}"

    def _init_workspace(self) -> tuple[bool, pathlib.Path]:
        tmp_dir = pathlib.Path(Settings().tmp_dir).absolute()
        workspace = tmp_dir / "workspaces" / self.name
        claude = tmp_dir / "claude" / self.name
        logs = tmp_dir / "logs" / self.name
        claude.mkdir(parents=True, exist_ok=True)
        logs.mkdir(parents=True, exist_ok=True)
        if workspace.exists():
            return True, workspace, logs, claude

        # Create a copy of the config to avoid mutating the global
        config = CLAUDE_SANDBOX_CONFIG.copy()
        config["mounts"] = config.get("mounts", []).copy()
        config["mounts"].extend(
            [
                {
                    "type": "bind",
                    "source": workspace.as_posix(),
                    "target": "/workspace",
                    "readonly": False,
                },
                {
                    "type": "bind",
                    "source": claude.as_posix(),
                    "target": "/home/claude/.claude",
                    "readonly": False,
                },
            ]
        )

        repo = Repo.init(workspace)
        with open(workspace / "claude-sandbox.config.json", "w") as f:
            f.write(json.dumps(config, indent=4))
        repo.index.add(["claude-sandbox.config.json"])
        repo.index.commit("Initial commit")
        return False, workspace, logs, claude

    async def _get_container(
        self, stdout_path: pathlib.Path, timeout: int = 60
    ) -> Container:
        for _ in range(timeout):
            if stdout_path.exists():
                logger.info(
                    f"Container {self.name} stdout file {stdout_path} found, starting..."
                )
                with open(stdout_path) as f:
                    for line in f:
                        if "Started container:" in line:
                            logger.info(f"Container {self.name} found, starting...")
                            container_id = line.split(" ")[-1].strip()
                            logger.info(f"Container {self.name} id: {container_id}")
                            return self._client.containers.get(container_id)
            else:
                logger.info(
                    f"Container {self.name} stdout file {stdout_path} not found, waiting for 1 second..."
                )
                await asyncio.sleep(1)

            logger.info(f"Container {self.name} not found, waiting for 1 second...")
            await asyncio.sleep(1)

        raise ClaudeSandboxError("Container not found after timeout")

    async def _wait_envd_ready(
        self, host: str, port: int, health_endpoint: str = "", timeout: int = 60
    ) -> bool:
        """Wait for envd service to be ready by checking health endpoint"""
        import time

        import aiohttp

        start_time = time.time()
        url = f"http://{host}:{port}/{health_endpoint}"

        async with aiohttp.ClientSession() as session:
            while time.time() - start_time < timeout:
                try:
                    async with session.get(
                        url, timeout=aiohttp.ClientTimeout(total=2)
                    ) as resp:
                        if resp.status == 200:
                            logger.info(f"Envd health check passed at {url}")
                            return True
                except (TimeoutError, aiohttp.ClientError) as e:
                    logger.debug(f"Health check failed: {e}")
                    await asyncio.sleep(1)

        return False

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
        # Run in detached mode to avoid blocking
        # When detach=True, exec_run returns immediately without exit_code
        self._container.exec_run(cmd, detach=True, workdir="/app")

        # Wait for service to be ready using health endpoint
        ok = await self._wait_envd_ready("localhost", port, timeout=timeout)
        if not ok:
            raise ClaudeSandboxError("Envd not started after timeout")

    @override
    async def start(self, timeout: int = 60):
        existed, workspace, logs, claude = self._init_workspace()
        logger.info(f"workspace status: {'existed' if existed else 'new'}")
        cmd = [
            "claude-sandbox",
            "start",
            "--name",
            self.name,
            "--no-web",
            "--envd-port",
            str(self.envd_port),
        ]

        timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")

        self._process = subprocess.Popen(
            cmd,
            cwd=workspace,
            stdout=open(logs / f"stdout-{timestamp}.txt", "w"),
            stderr=open(logs / f"stderr-{timestamp}.txt", "w"),
        )

        self._container = await self._get_container(
            logs / f"stdout-{timestamp}.txt", timeout
        )

        logger.info(f"Container {self._container.id} started")

        await self._start_envd(self.envd_port)
    

    @override
    async def stop(self):
        if self._process is None or self._container is None:
            raise ClaudeSandboxError("Stop Failed: Sandbox not found")
        self._process.terminate()
        self._container.stop()
        self._container.remove()

    async def __aenter__(self, timeout: int = 60):
        logger.info(f"Starting sandbox {self.name}...")
        await self.start(timeout)
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        logger.info(f"Stopping sandbox {self.name}...")
        await self.stop()

    async def exec(self, cmd: list[str]) -> str:
        if self._container is None:
            raise ClaudeSandboxError("Exec Failed: Sandbox not found")
        result = self._container.exec_run(cmd)
        return result.exit_code, result.output


class ClaudeSandboxSession(SandboxSession[ClaudeSandbox]):
    async def query(self, query: str, continue_conversation: bool = True):
        return await self.send_request(
            "POST",
            "/query",
            json={
                "query": query,
                "continue_conversation": continue_conversation,
            },
        )


def claude_sandbox_session(sandbox_id: str, envd_port: int):
    return ClaudeSandboxSession(
        sandbox=ClaudeSandbox(id=sandbox_id, envd_port=envd_port)
    )
