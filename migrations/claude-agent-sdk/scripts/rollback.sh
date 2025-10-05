#!/bin/bash

# Claude Agent SDK Rollback Script
# Version: 1.0.0
# Date: 2025-10-05

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
PROJECT_ROOT="/home/dministrator/LainNet"
MIGRATION_DIR="$PROJECT_ROOT/migrations/claude-agent-sdk"
LOG_FILE="$MIGRATION_DIR/logs/rollback_$(date +%Y%m%d_%H%M%S).log"

mkdir -p "$(dirname "$LOG_FILE")"

# Logging function
log() {
    echo -e "$1" | tee -a "$LOG_FILE"
}

# Header
log "${RED}======================================${NC}"
log "${RED}Claude Agent SDK Rollback Script${NC}"
log "${RED}======================================${NC}"
log "Started at: $(date)"
log ""

# Find latest backup
find_latest_backup() {
    LATEST_BACKUP=$(ls -dt "$MIGRATION_DIR/backup"/*/ 2>/dev/null | head -1)
    if [ -z "$LATEST_BACKUP" ]; then
        log "${RED}✗ No backup found${NC}"
        exit 1
    fi
    log "${YELLOW}Using backup: $LATEST_BACKUP${NC}"
}

# Rollback dependencies
rollback_dependencies() {
    log "${YELLOW}[Step 1] Rolling back Python dependencies...${NC}"
    
    cd "$PROJECT_ROOT"
    
    if [ -f "$LATEST_BACKUP/pyproject.toml.backup" ]; then
        cp "$LATEST_BACKUP/pyproject.toml.backup" "$PROJECT_ROOT/pyproject.toml"
        log "${GREEN}✓ pyproject.toml restored${NC}"
    fi
    
    if [ -f "$LATEST_BACKUP/uv.lock.backup" ]; then
        cp "$LATEST_BACKUP/uv.lock.backup" "$PROJECT_ROOT/uv.lock"
        log "${GREEN}✓ uv.lock restored${NC}"
    fi
    
    # Reinstall dependencies
    log "Reinstalling dependencies..."
    ~/.local/bin/uv sync
    log "${GREEN}✓ Dependencies rolled back${NC}"
    log ""
}

# Rollback Docker
rollback_docker() {
    log "${YELLOW}[Step 2] Rolling back Docker images...${NC}"
    
    # Find backup image
    BACKUP_IMAGE=$(docker images --format "{{.Repository}}:{{.Tag}}" | grep "claude-code-sandbox:backup" | head -1)
    
    if [ -n "$BACKUP_IMAGE" ]; then
        docker tag "$BACKUP_IMAGE" claude-code-sandbox:dev
        log "${GREEN}✓ Docker image rolled back to: $BACKUP_IMAGE${NC}"
    else
        log "${YELLOW}⚠ No Docker backup found, skipping${NC}"
    fi
    log ""
}

# Rollback code
rollback_code() {
    log "${YELLOW}[Step 3] Rolling back code changes...${NC}"
    
    # Restore envd.py
    if [ -f "$LATEST_BACKUP/envd.py.backup" ]; then
        cp "$LATEST_BACKUP/envd.py.backup" "$PROJECT_ROOT/docker/envd.py"
        log "${GREEN}✓ envd.py restored${NC}"
    fi
    
    # Remove patch file
    rm -f "$PROJECT_ROOT/docker/sdk_compatibility_patch.py"
    log "${GREEN}✓ Patch file removed${NC}"
    
    # Restore configuration
    if [ -f "$LATEST_BACKUP/claude-sandbox.config.json.backup" ]; then
        cp "$LATEST_BACKUP/claude-sandbox.config.json.backup" "$PROJECT_ROOT/claude-sandbox.config.json"
        log "${GREEN}✓ Configuration restored${NC}"
    fi
    log ""
}

# Verify rollback
verify_rollback() {
    log "${YELLOW}[Step 4] Verifying rollback...${NC}"
    
    # Check SDK version
    if ~/.local/bin/uv pip list | grep -q claude-code-sdk; then
        log "${GREEN}✓ claude-code-sdk restored${NC}"
    else
        log "${YELLOW}⚠ claude-code-sdk not found${NC}"
    fi
    
    # Test import
    if python3 -c "from claude_code_sdk import ClaudeCodeOptions" 2>/dev/null; then
        log "${GREEN}✓ Python imports working${NC}"
    else
        log "${YELLOW}⚠ Import test failed${NC}"
    fi
    log ""
}

# Main rollback
main() {
    find_latest_backup
    
    log "${YELLOW}This will rollback the Claude Agent SDK migration.${NC}"
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log "${RED}Rollback cancelled${NC}"
        exit 1
    fi
    
    rollback_dependencies
    rollback_docker
    rollback_code
    verify_rollback
    
    log "${GREEN}======================================${NC}"
    log "${GREEN}Rollback completed successfully!${NC}"
    log "${GREEN}======================================${NC}"
    log ""
    log "Next steps:"
    log "1. Restart services: make lark-server"
    log "2. Verify application functionality"
    log ""
    log "Log file: $LOG_FILE"
}

main "$@"