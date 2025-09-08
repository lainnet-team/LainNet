@echo off
echo Starting User Memory MCP Server...

REM 使用相对路径定位到用户目录
set USER_CLAUDE_DIR=%USERPROFILE%\.claude\tools\user_memory

REM 切换到服务器目录
cd /d "%USER_CLAUDE_DIR%"

REM 检查是否已安装依赖
if not exist "node_modules" (
    echo Installing dependencies...
    npm install
)

REM 启动MCP服务器
echo Starting MCP server...
node index.js

pause