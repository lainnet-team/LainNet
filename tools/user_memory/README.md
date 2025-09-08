# User Memory MCP Server

用于管理Claude Code全局记忆的MCP服务器，记忆存储在 `~/.claude/CLAUDE.md` 文件中。

## 功能

提供三个记忆管理工具：
- **insert_memory(memory)** - 新增记忆，自动生成16位数字ID
- **update_memory(memory_id, memory)** - 更新指定ID的记忆
- **delete_memory(memory_id)** - 删除指定ID的记忆

## 安装

```bash
# 进入目录
cd %USERPROFILE%\.claude\tools\user_memory

# 安装依赖
npm install
```

## 配置Claude Code

```bash
# 使用相对路径添加MCP服务器
claude mcp add user-memory -- node %USERPROFILE%\.claude\tools\user_memory\index.js
```

## 使用示例

在Claude Code中使用：

```
# 新增记忆
使用insert_memory工具记住："项目使用Python 3.11作为主要开发语言"

# 返回示例：
{
  "success": true,
  "memory_id": "1735123456789012",
  "message": "记忆已保存，ID: 1735123456789012"
}

# 更新记忆
使用update_memory工具更新记忆1735123456789012："项目升级到Python 3.12"

# 删除记忆
使用delete_memory工具删除记忆1735123456789012
```

## 记忆存储格式

记忆以JSON格式存储在 `CLAUDE.md` 文件的 `## MEMORIES` 部分：

```markdown
## MEMORIES
<!-- 记忆区域开始 -->
{"date": "2025-01-07", "memory_id": "1735123456789012", "memory": "项目使用Python 3.11作为主要开发语言"}
{"date": "2025-01-07", "memory_id": "1735123456789013", "memory": "用户偏好使用中文交流"}
<!-- 记忆区域结束 -->
```

每条记忆包含：
- **date**: 记忆创建/更新日期 (YYYY-MM-DD格式)
- **memory_id**: 16位数字唯一ID
- **memory**: 记忆内容文本

## 文件结构

```
~/.claude/tools/user_memory/
├── index.js        # MCP服务器主文件
├── package.json    # 依赖配置
├── start.bat      # Windows启动脚本
├── setup.bat      # 安装配置脚本
└── README.md      # 本文档
```

## 特点

- 使用相对路径，跨平台兼容
- 记忆直接存储在CLAUDE.md，Claude Code启动时自动加载
- 16位数字ID确保唯一性
- 简单的文本格式，易于手动编辑和备份

## 故障排除

1. **找不到CLAUDE.md文件**
   - 确保文件存在于 `%USERPROFILE%\.claude\CLAUDE.md`
   - 服务器会自动创建MEMORIES部分

2. **依赖安装失败**
   - 确保Node.js版本 >= 18.0.0
   - 检查npm网络连接

3. **MCP连接失败**
   - 重启Claude Code
   - 检查服务器是否正常运行
   - 查看控制台错误信息