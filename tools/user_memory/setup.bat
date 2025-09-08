@echo off
echo Setting up User Memory MCP Server...

REM 使用相对路径
set USER_CLAUDE_DIR=%USERPROFILE%\.claude\tools\user_memory

REM 切换到服务器目录
cd /d "%USER_CLAUDE_DIR%"

REM 安装依赖
echo Installing dependencies...
npm install

REM 添加到Claude Code MCP配置（使用相对路径）
echo.
echo Adding to Claude Code MCP configuration...
echo Run the following command to add this server to Claude Code:
echo.
echo claude mcp add user-memory -- node "%USER_CLAUDE_DIR%\index.js"
echo.
echo Or use the relative path:
echo claude mcp add user-memory -- node "%USERPROFILE%\.claude\tools\user_memory\index.js"
echo.

pause