# Claude Agent SDK 迁移

本目录包含从 `claude-code-sdk` 迁移到 `claude-agent-sdk` 的完整方案和实现。

## 📁 目录结构

```
claude-agent-sdk/
├── README.md              # 本文档
├── MIGRATION_PLAN.md      # 详细迁移计划
├── docs/
│   └── RISK_ASSESSMENT.md # 风险评估文档
├── scripts/
│   ├── migrate.sh         # 一键迁移脚本
│   ├── rollback.sh        # 回滚脚本
│   └── test_migration.py  # 迁移测试脚本
├── patches/
│   └── sdk_compatibility_patch.py  # 兼容性补丁
├── backup/                # 自动备份目录
└── logs/                  # 日志目录
```

## 🚀 快速开始

### 1. 测试环境就绪性

```bash
# 运行测试脚本，检查环境是否准备就绪
~/.local/bin/uv run python migrations/claude-agent-sdk/scripts/test_migration.py
```

### 2. 执行迁移

```bash
# 一键执行迁移（包含备份）
./migrations/claude-agent-sdk/scripts/migrate.sh
```

### 3. 验证迁移

迁移脚本会自动运行验证，也可手动验证：

```bash
# 测试 Python 环境
python -c "import sdk_compatibility_patch; from claude_agent_sdk import ClaudeAgentOptions; print('✓ SDK working')"

# 测试 Docker 容器
docker run --rm claude-code-sandbox:agent-sdk python3 -c "import sdk_compatibility_patch; print('✓ Container working')"
```

### 4. 启动服务

```bash
# 重启 Lark 服务器
make lark-server
```

## 🔄 回滚方案

如果迁移出现问题，可以快速回滚：

```bash
# 执行回滚脚本
./migrations/claude-agent-sdk/scripts/rollback.sh
```

## 📝 核心改动

### 依赖更新
- `claude-code-sdk` → `claude-agent-sdk>=0.1.0`

### 代码更新
- `ClaudeCodeOptions` → `ClaudeAgentOptions`
- 导入路径更新
- 添加兼容性补丁

### Docker 更新
- 新镜像：`claude-code-sandbox:agent-sdk`
- 包含兼容性补丁
- 保持 OAuth 认证机制

## ⚠️ 重要说明

1. **认证方式**：继续使用 OAuth (`~/.claude/.credentials.json`)，无需 API Key
2. **兼容性补丁**：通过 Monkey Patch 解决 `--setting-sources` 参数不兼容问题
3. **影响范围**：详见 [RISK_ASSESSMENT.md](docs/RISK_ASSESSMENT.md)

## 📊 监控

迁移后需要监控：

```bash
# 查看服务日志
tail -f logs/lainnet.log | grep -E "(SDK|patch|error)"

# 检查补丁状态
python -c "import sdk_compatibility_patch; print('Patch active')"

# 健康检查
curl -X POST http://localhost:8000/health
```

## 🆘 故障排查

### 问题：`--setting-sources` 错误仍然出现
- 确认补丁已应用：检查日志中的 "SDK compatibility patch applied"
- 验证补丁文件存在：`ls docker/sdk_compatibility_patch.py`

### 问题：Docker 构建失败
- 检查基础镜像：`docker images | grep claude-code-sandbox`
- 查看构建日志：`docker build --no-cache -t test .`

### 问题：认证失败
- 确认凭证文件：`ls -la ~/.claude/.credentials.json`
- 重新登录：`claude login`

## 📚 相关文档

- [完整迁移计划](MIGRATION_PLAN.md)
- [风险评估](docs/RISK_ASSESSMENT.md)
- [项目文档](../../docs/current_things.md)

## 👥 联系

- 负责人：dministrator
- 协助：Claude
- 创建日期：2025-10-05

---

💡 **提示**：在生产环境执行迁移前，请先在测试环境验证。