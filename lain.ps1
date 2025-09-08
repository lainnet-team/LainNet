# Lain System Launcher for Claude Code

Write-Host "===================================" -ForegroundColor Cyan
Write-Host "   Lain System Initializing...     " -ForegroundColor Cyan
Write-Host "===================================" -ForegroundColor Cyan

# sets env
$claudeDir = "$env:USERPROFILE\.claude"
$toolsDir = "$claudeDir\tools"

Write-Host "User directory: $env:USERPROFILE" -ForegroundColor Gray
Write-Host "Claude directory: $claudeDir" -ForegroundColor Gray

# Define MCP servers
$mcpServers = @(
    @{
        Name = "user-memory"
        Path = "$toolsDir\user_memory\index.js"
        Description = "Global memory management"
    }
    # Add more servers here
    # @{
    #     Name = "web-search"
    #     Path = "$toolsDir\web_search\index.js"
    #     Description = "Web search capabilities"
    # }
)

# Check if Node.js is installed
Write-Host "`nChecking prerequisites..." -ForegroundColor Yellow
try {
    $nodeVersion = node --version
    Write-Host "✓ Node.js $nodeVersion installed" -ForegroundColor Green
} catch {
    Write-Host "✗ Node.js not found. Please install Node.js first." -ForegroundColor Red
    exit 1
}

# Check if Claude CLI is installed
try {
    $claudeVersion = claude --version
    Write-Host "✓ Claude Code CLI installed" -ForegroundColor Green
} catch {
    Write-Host "✗ Claude Code CLI not found. Installing..." -ForegroundColor Yellow
    npm install -g @anthropic-ai/claude-code
}

# Install and configure MCP servers
Write-Host "`nConfiguring MCP servers..." -ForegroundColor Yellow

foreach ($server in $mcpServers) {
    $serverDir = Split-Path $server.Path -Parent
    $serverName = $server.Name
    
    if (Test-Path $serverDir) {
        Write-Host "`nProcessing $serverName..." -ForegroundColor Cyan
        
        # Check and install dependencies
        Push-Location $serverDir
        if (-not (Test-Path "node_modules")) {
            Write-Host "  Installing dependencies..." -ForegroundColor Gray
            npm install --silent
        }
        Pop-Location
        
        # Add to Claude MCP configuration
        $output = claude mcp add $serverName --scope user -- node $server.Path 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  ✓ $serverName server added - $($server.Description)" -ForegroundColor Green
        } else {
            Write-Host "  • $serverName server already configured" -ForegroundColor Gray
        }
    } else {
        Write-Host "  ⚠ $serverName server not found at $serverDir" -ForegroundColor Yellow
    }
}

# Show all configured servers
Write-Host "`nConfigured MCP servers:" -ForegroundColor Yellow
claude mcp list

# Show memory statistics (if any)
$claudeMdPath = "$claudeDir\CLAUDE.md"
if (Test-Path $claudeMdPath) {
    $content = Get-Content $claudeMdPath -Raw
    $memoryCount = ([regex]::Matches($content, '"memory_id":')).Count
    if ($memoryCount -gt 0) {
        Write-Host "`nMemory statistics:" -ForegroundColor Yellow
        Write-Host "  Total memories: $memoryCount" -ForegroundColor Gray
    }
}

# Start Claude Code
Write-Host "`n===================================" -ForegroundColor Cyan
Write-Host "   Starting Claude Code...         " -ForegroundColor Cyan
Write-Host "===================================" -ForegroundColor Cyan
Write-Host ""

# Start Claude and wait
claude

# Exit information
Write-Host "`n===================================" -ForegroundColor Cyan
Write-Host "   Claude Code session ended       " -ForegroundColor Cyan
Write-Host "===================================" -ForegroundColor Cyan
Write-Host "Run '.\lain.ps1' to start again" -ForegroundColor Gray
Write-Host ""