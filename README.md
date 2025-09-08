# LainNet

## Quick Start
### 1. Copy `.env` file
```sh
cp .env.example .env
```
### 2. Edit `.env` file
https://open.feishu.cn/document/develop-an-echo-bot/introduction
```properties
APP_ID=<YOUR-LARK_BOT-APP-ID>
APP_SECRET=<YOUR_-LARK_BOT-APP-SECRET>
```
### 3. Install dependencies
Make sure `npm`, `uv` and `claude-code` already in your enviroments
```sh
make install
```
or
```sh
uv sync
uv run python3 -m scripts.install
```
### 4. Run lark bot
```sh
make lark-server
```
or
```
uv run python3 -m src.packages.lark.server
```