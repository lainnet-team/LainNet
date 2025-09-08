import subprocess
from pathlib import Path

from git import Repo
from loguru import logger


def install_claude_code_sandbox(repo_path: Path | None = None):
    if repo_path is None:
        repo_path = Path.home() / "claude-code-sandbox"
    else:
        repo_path = Path(repo_path)
    if repo_path.exists():
        logger.info(f"Claude code sandbox already installed at {repo_path}")
        logger.info(f"Updating to latest version at {repo_path} ...")
        Repo(repo_path).remotes.origin.pull()
        return
    logger.info(f"Installing Claude code sandbox at {repo_path} ...")
    Repo.clone_from("https://github.com/mob999/claude-code-sandbox.git", repo_path)

    logger.info(f"Installing dependencies at {repo_path} ...")
    result = subprocess.run(["npm", "install"], cwd=repo_path)
    if result.returncode != 0:
        logger.error(f"Failed to install dependencies at {repo_path}: {result.stderr}")
        return
    logger.info(f"Building at {repo_path} ...")
    result = subprocess.run(["npm", "run", "build"], cwd=repo_path)
    if result.returncode != 0:
        logger.error(f"Failed to build at {repo_path}: {result.stderr}")
        return
    logger.info(f"Linking at {repo_path} ...")
    result = subprocess.run(["npm", "link"], cwd=repo_path)
    if result.returncode != 0:
        logger.error(f"Failed to link at {repo_path}: {result.stderr}")
        return
    logger.info(f"Successfully installed Claude code sandbox at {repo_path}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-path", type=str, default=None)
    args = parser.parse_args()
    install_claude_code_sandbox(args.repo_path)
