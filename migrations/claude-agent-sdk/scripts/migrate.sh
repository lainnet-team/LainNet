#!/bin/bash

# Claude Agent SDK Migration Script
# Version: 1.0.0
# Date: 2025-10-05

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="/home/dministrator/LainNet"
MIGRATION_DIR="$PROJECT_ROOT/migrations/claude-agent-sdk"
BACKUP_DIR="$MIGRATION_DIR/backup/$(date +%Y%m%d_%H%M%S)"
LOG_FILE="$MIGRATION_DIR/logs/migration_$(date +%Y%m%d_%H%M%S).log"

# Create directories
mkdir -p "$BACKUP_DIR"
mkdir -p "$(dirname "$LOG_FILE")"

# Logging function
log() {
    echo -e "$1" | tee -a "$LOG_FILE"
}

# Header
log "${BLUE}======================================${NC}"
log "${BLUE}Claude Agent SDK Migration Script${NC}"
log "${BLUE}======================================${NC}"
log "Started at: $(date)"
log ""

# Function to check prerequisites
check_prerequisites() {
    log "${YELLOW}[Phase 1] Checking prerequisites...${NC}"
    
    # Check uv
    if ! command -v ~/.local/bin/uv &> /dev/null; then
        log "${RED}✗ uv not found${NC}"
        exit 1
    fi
    log "${GREEN}✓ uv found${NC}"
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log "${RED}✗ Docker not found${NC}"
        exit 1
    fi
    log "${GREEN}✓ Docker found${NC}"
    
    # Check credentials
    if [ ! -f ~/.claude/.credentials.json ]; then
        log "${RED}✗ Claude credentials not found${NC}"
        log "  Please run: claude login"
        exit 1
    fi
    log "${GREEN}✓ Claude credentials found${NC}"
    
    # Check git status
    cd "$PROJECT_ROOT"
    if [ -n "$(git status --porcelain)" ]; then
        log "${YELLOW}⚠ Warning: Uncommitted changes detected${NC}"
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log "${RED}Migration cancelled${NC}"
            exit 1
        fi
    fi
    log "${GREEN}✓ Git status checked${NC}"
    log ""
}

# Function to create backups
create_backups() {
    log "${YELLOW}[Phase 2] Creating backups...${NC}"
    
    # Backup current branch
    CURRENT_BRANCH=$(git branch --show-current)
    log "Current branch: $CURRENT_BRANCH"
    
    # Backup files
    cp "$PROJECT_ROOT/pyproject.toml" "$BACKUP_DIR/pyproject.toml.backup"
    cp "$PROJECT_ROOT/uv.lock" "$BACKUP_DIR/uv.lock.backup"
    
    # Backup Docker image if exists
    if docker images | grep -q "claude-code-sandbox.*dev"; then
        log "Backing up Docker image..."
        docker tag claude-code-sandbox:dev "claude-code-sandbox:backup-$(date +%Y%m%d)"
        log "${GREEN}✓ Docker image backed up${NC}"
    fi
    
    log "${GREEN}✓ Backups created in: $BACKUP_DIR${NC}"
    log ""
}

# Function to update dependencies
update_dependencies() {
    log "${YELLOW}[Phase 3] Updating Python dependencies...${NC}"
    
    cd "$PROJECT_ROOT"
    
    # Update pyproject.toml
    log "Updating pyproject.toml..."
    sed -i.bak 's/"claude-code-sdk[^"]*"/"claude-agent-sdk>=0.1.0"/' pyproject.toml
    
    # Sync dependencies
    log "Running uv sync..."
    ~/.local/bin/uv sync
    
    # Verify installation
    if ~/.local/bin/uv pip list | grep -q claude-agent-sdk; then
        log "${GREEN}✓ claude-agent-sdk installed successfully${NC}"
    else
        log "${RED}✗ Failed to install claude-agent-sdk${NC}"
        exit 1
    fi
    log ""
}

# Function to apply code patches
apply_patches() {
    log "${YELLOW}[Phase 4] Applying code patches...${NC}"
    
    # Copy compatibility patch to Docker directory
    cp "$MIGRATION_DIR/patches/sdk_compatibility_patch.py" "$PROJECT_ROOT/docker/"
    log "${GREEN}✓ Compatibility patch copied${NC}"
    
    # Update docker/envd.py
    log "Updating docker/envd.py..."
    if [ -f "$PROJECT_ROOT/docker/envd.py" ]; then
        # Create backup
        cp "$PROJECT_ROOT/docker/envd.py" "$BACKUP_DIR/envd.py.backup"
        
        # Apply updates (this is simplified - in real scenario, use proper sed or Python script)
        cat > "$PROJECT_ROOT/docker/envd_patch.py" << 'EOF'
import sys
import re

# Read the file
with open('/home/dministrator/LainNet/docker/envd.py', 'r') as f:
    content = f.read()

# Apply patches
patches = [
    # Add import for patch at the beginning
    (r'(import sys\n)', r'\1sys.path.insert(0, "/app")\n\ntry:\n    import sdk_compatibility_patch\n    print("[ENVD] SDK compatibility patch applied")\nexcept Exception as e:\n    print(f"[ENVD] Warning: Could not apply patch: {e}")\n\n'),
    
    # Update imports
    (r'from claude_code_sdk import ClaudeCodeOptions, ClaudeSDKClient',
     r'from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient'),
    
    # Update class names
    (r'ClaudeCodeOptions', r'ClaudeAgentOptions'),
]

for pattern, replacement in patches:
    content = re.sub(pattern, replacement, content)

# Write back
with open('/home/dministrator/LainNet/docker/envd.py', 'w') as f:
    f.write(content)

print("✓ envd.py updated")
EOF
        
        python3 "$PROJECT_ROOT/docker/envd_patch.py"
        rm "$PROJECT_ROOT/docker/envd_patch.py"
        log "${GREEN}✓ envd.py updated${NC}"
    else
        log "${YELLOW}⚠ docker/envd.py not found, skipping${NC}"
    fi
    log ""
}

# Function to build Docker image
build_docker() {
    log "${YELLOW}[Phase 5] Building Docker image...${NC}"
    
    cd "$PROJECT_ROOT/docker"
    
    # Create updated Dockerfile if needed
    if [ ! -f Dockerfile ]; then
        cat > Dockerfile << 'EOF'
FROM claude-code-sandbox:dev
WORKDIR /app

# Install new SDK
RUN pip install claude-agent-sdk fastapi uvicorn

# Copy application files
COPY envd.py /app/envd.py
COPY sdk_compatibility_patch.py /app/
COPY tools /app/tools

EXPOSE 8000
EOF
        log "Created Dockerfile"
    fi
    
    # Build image
    log "Building Docker image..."
    if docker build -t claude-code-sandbox:agent-sdk .; then
        log "${GREEN}✓ Docker image built successfully${NC}"
        
        # Tag as dev
        docker tag claude-code-sandbox:agent-sdk claude-code-sandbox:dev
        log "${GREEN}✓ Image tagged as :dev${NC}"
    else
        log "${RED}✗ Docker build failed${NC}"
        exit 1
    fi
    log ""
}

# Function to run tests
run_tests() {
    log "${YELLOW}[Phase 6] Running verification tests...${NC}"
    
    cd "$PROJECT_ROOT"
    
    # Test Python import
    log "Testing Python SDK import..."
    if python3 -c "import sdk_compatibility_patch; from claude_agent_sdk import ClaudeAgentOptions; print('✓ SDK import test passed')" 2>&1 | tee -a "$LOG_FILE"; then
        log "${GREEN}✓ Python import test passed${NC}"
    else
        log "${RED}✗ Python import test failed${NC}"
        exit 1
    fi
    
    # Test Docker container
    log "Testing Docker container..."
    if docker run --rm claude-code-sandbox:agent-sdk python3 -c "import sdk_compatibility_patch; from claude_agent_sdk import ClaudeAgentOptions; print('✓ Docker test passed')" 2>&1 | tee -a "$LOG_FILE"; then
        log "${GREEN}✓ Docker container test passed${NC}"
    else
        log "${RED}✗ Docker container test failed${NC}"
        exit 1
    fi
    
    # Run migration test if exists
    if [ -f "$MIGRATION_DIR/scripts/test_migration.py" ]; then
        log "Running migration test script..."
        ~/.local/bin/uv run python "$MIGRATION_DIR/scripts/test_migration.py" 2>&1 | tee -a "$LOG_FILE"
    fi
    log ""
}

# Function to update configuration
update_configuration() {
    log "${YELLOW}[Phase 7] Updating configuration...${NC}"
    
    # Update claude-sandbox.config.json if exists
    if [ -f "$PROJECT_ROOT/claude-sandbox.config.json" ]; then
        cp "$PROJECT_ROOT/claude-sandbox.config.json" "$BACKUP_DIR/claude-sandbox.config.json.backup"
        # Update Docker image reference
        sed -i 's/"dockerImage":[^,]*/"dockerImage": "claude-code-sandbox:agent-sdk"/' "$PROJECT_ROOT/claude-sandbox.config.json"
        log "${GREEN}✓ Configuration updated${NC}"
    fi
    log ""
}

# Main migration flow
main() {
    check_prerequisites
    create_backups
    update_dependencies
    apply_patches
    build_docker
    run_tests
    update_configuration
    
    log "${GREEN}======================================${NC}"
    log "${GREEN}Migration completed successfully!${NC}"
    log "${GREEN}======================================${NC}"
    log ""
    log "Next steps:"
    log "1. Restart your services: make lark-server"
    log "2. Test the application thoroughly"
    log "3. Monitor logs for any issues"
    log ""
    log "To rollback if needed, run:"
    log "  $MIGRATION_DIR/scripts/rollback.sh"
    log ""
    log "Backup location: $BACKUP_DIR"
    log "Log file: $LOG_FILE"
}

# Run main function
main "$@"