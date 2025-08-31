.PHONY: ruff
ruff: ruff-format ruff-fix ## 运行所有 Ruff 检查和格式化

.PHONY: ruff-check
ruff-check: ## 运行 Ruff 代码检查
	uv tool run ruff check

.PHONY: ruff-fix
ruff-fix: ## 运行 Ruff 自动修复
	uv tool run ruff check --fix

.PHONY: ruff-format
ruff-format: ## 运行 Ruff 代码格式化
	uv tool run ruff format