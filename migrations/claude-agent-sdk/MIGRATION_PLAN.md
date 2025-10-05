# Claude Agent SDK 迁移计划

> 从 claude-code-sdk 迁移到 claude-agent-sdk v0.1.0
> 
> 迁移日期：2025-10-05
> 负责人：dministrator & Claude

## 📋 目录

1. [迁移概述](#迁移概述)
2. [前置条件](#前置条件)
3. [迁移步骤](#迁移步骤)
4. [风险评估](#风险评估)
5. [回滚方案](#回滚方案)
6. [验证清单](#验证清单)

## 迁移概述

### 目标
将 LainNet 项目从 `claude-code-sdk` 迁移到 `claude-agent-sdk`，同时：
- ✅ 保持免费的 OAuth 认证机制（不购买 API Key）
- ✅ 保持现有的 Docker 容器架构
- ✅ 保持与 claude-code CLI v1.0.109 的兼容性
- ✅ 获得新 SDK 的特性和改进

### 核心挑战
- **版本不兼容**：新 SDK 的 `--setting-sources` 参数不被旧 CLI 识别
- **解决方案**：使用 Monkey Patch 移除不兼容的参数

### 迁移范围
- ✅ Python 依赖更新
- ✅ Docker 镜像更新
- ✅ 代码中的类名和导入更新
- ✅ 添加兼容性补丁

## 前置条件

### 1. 环境检查
```bash
# 检查当前 SDK 版本
~/.local/bin/uv pip list | grep claude

# 检查 CLI 版本
npm list -g @anthropic-ai/claude-code

# 检查 OAuth 认证
ls -la ~/.claude/.credentials.json
```

### 2. 备份
```bash
# 备份当前代码
git checkout -b backup-before-migration
git add -A && git commit -m "Backup before claude-agent-sdk migration"

# 备份 Docker 镜像
docker tag claude-code-sandbox:dev claude-code-sandbox:backup-20251005

# 备份依赖
cp pyproject.toml backup/pyproject.toml.backup
cp uv.lock backup/uv.lock.backup
```

## 迁移步骤

### Phase 1: 准备工作（5分钟）

#### 1.1 创建新分支
```bash
git checkout -b migrate-to-agent-sdk
```

#### 1.2 复制补丁文件
```bash
# 将测试过的补丁复制到正式位置
cp tests/sdk_migration/sdk_compatibility_patch.py migrations/claude-agent-sdk/patches/
```

### Phase 2: 更新依赖（10分钟）

#### 2.1 更新 pyproject.toml
```toml
# 修改 pyproject.toml
dependencies = [
    # "claude-code-sdk>=0.0.20",  # 注释掉旧的
    "claude-agent-sdk>=0.1.0",     # 添加新的
    # ... 其他依赖保持不变
]
```

#### 2.2 更新依赖
```bash
cd ~/LainNet
~/.local/bin/uv sync
```

### Phase 3: 更新代码（15分钟）

#### 3.1 更新 Docker 补丁
创建 `docker/sdk_compatibility_patch.py`：
```python
# 从 migrations/claude-agent-sdk/patches/ 复制
cp migrations/claude-agent-sdk/patches/sdk_compatibility_patch.py docker/
```

#### 3.2 更新 docker/envd.py
```python
# 在文件开头添加
import sys
sys.path.insert(0, '/app')

# 应用补丁（必须在导入 SDK 之前）
try:
    import sdk_compatibility_patch
    print("[ENVD] SDK compatibility patch applied")
except Exception as e:
    print(f"[ENVD] Warning: Could not apply patch: {e}")

# 更新导入
from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient  # 新
# from claude_code_sdk import ClaudeCodeOptions, ClaudeSDKClient  # 旧

# 更新函数签名
def get_claude_options(continue_conversation: bool = True) -> ClaudeAgentOptions:
    """Get Claude SDK options with shared configuration"""
    return ClaudeAgentOptions(  # 类名改变
        mcp_servers=MCP_CONFIG,
        allowed_tools=ALLOWED_TOOLS,
        permission_mode='bypassPermissions',
        continue_conversation=continue_conversation,
        # 注意：append_system_prompt 可能需要改为 system_prompt
        system_prompt=LAIN_SYSTEM_PROMPT  # 参数名可能改变
    )
```

#### 3.3 更新 Dockerfile
```dockerfile
FROM claude-code-sandbox:dev
WORKDIR /app

# 安装新 SDK
RUN pip install claude-agent-sdk fastapi uvicorn

# 复制应用文件
COPY envd.py /app/envd.py
COPY sdk_compatibility_patch.py /app/  # 添加补丁文件
COPY tools /app/tools

EXPOSE 8000
```

### Phase 4: 构建和测试（20分钟）

#### 4.1 构建新镜像
```bash
cd ~/LainNet/docker
docker build -t claude-code-sandbox:agent-sdk .

# 测试构建是否成功
docker run --rm claude-code-sandbox:agent-sdk python3 -c "
import sdk_compatibility_patch
from claude_agent_sdk import ClaudeAgentOptions
print('✅ SDK import successful')
"
```

#### 4.2 更新配置使用新镜像
修改 `claude-sandbox.config.json`:
```json
{
    "dockerImage": "claude-code-sandbox:agent-sdk",
    // ... 其他配置不变
}
```

#### 4.3 本地测试
```bash
# 运行测试脚本
cd ~/LainNet
~/.local/bin/uv run python migrations/claude-agent-sdk/scripts/test_migration.py
```

### Phase 5: 部署（10分钟）

#### 5.1 更新生产镜像
```bash
# 标记新镜像为生产版本
docker tag claude-code-sandbox:agent-sdk claude-code-sandbox:dev

# 保留旧镜像以备回滚
docker tag claude-code-sandbox:backup-20251005 claude-code-sandbox:rollback
```

#### 5.2 重启服务
```bash
# 重启 Lark 服务器
make lark-server
```

#### 5.3 验证服务
- 发送测试消息到飞书机器人
- 检查记忆功能是否正常
- 验证 MCP 工具是否可用

## 风险评估

### 🟢 低风险
- **补丁方案已测试验证**：Monkey Patch 在测试中工作正常
- **OAuth 认证兼容**：认证机制未改变
- **可快速回滚**：保留了备份镜像

### 🟡 中等风险
- **SDK 未来更新**：补丁可能需要调整
- **未知的行为差异**：新 SDK 可能有细微的行为变化
- **性能影响**：需要监控性能指标

### 🔴 高风险
- **生产环境中断**：如果补丁失效可能导致服务中断
- **缓解措施**：保留回滚方案，监控错误日志

## 回滚方案

### 快速回滚步骤（5分钟）

#### 1. 恢复 Docker 镜像
```bash
docker tag claude-code-sandbox:rollback claude-code-sandbox:dev
```

#### 2. 恢复代码
```bash
git checkout backup-before-migration
```

#### 3. 恢复依赖
```bash
cp backup/pyproject.toml.backup pyproject.toml
cp backup/uv.lock.backup uv.lock
~/.local/bin/uv sync
```

#### 4. 重启服务
```bash
make lark-server
```

## 验证清单

### 功能验证
- [ ] 飞书消息接收正常
- [ ] AI 响应生成正常  
- [ ] 记忆功能（增删改）正常
- [ ] MCP 工具调用正常
- [ ] 容器创建和销毁正常
- [ ] 工作空间持久化正常

### 性能验证
- [ ] 首次响应时间 < 45秒
- [ ] 后续响应时间 < 20秒（容器复用）
- [ ] 内存使用正常
- [ ] CPU 使用正常

### 日志检查
- [ ] 无认证错误
- [ ] 无 SDK 相关异常
- [ ] 补丁应用成功日志
- [ ] MCP 工具加载成功

## 时间线

| 阶段 | 预计时间 | 实际时间 | 状态 |
|------|----------|----------|------|
| 准备工作 | 5分钟 | - | ⏳ |
| 更新依赖 | 10分钟 | - | ⏳ |
| 更新代码 | 15分钟 | - | ⏳ |
| 构建测试 | 20分钟 | - | ⏳ |
| 部署验证 | 10分钟 | - | ⏳ |
| **总计** | **60分钟** | - | ⏳ |

## 联系方式

- 负责人：dministrator
- 协助：Claude
- 紧急回滚：执行 `./migrations/claude-agent-sdk/scripts/rollback.sh`

---

最后更新：2025-10-05
状态：待执行