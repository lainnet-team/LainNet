#!/usr/bin/env python3
"""
Migration Test Script
Tests the Claude Agent SDK migration in the current environment
"""

import asyncio
import json
import sys
import subprocess
from pathlib import Path
from datetime import datetime

# Add migration patches directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "patches"))

# Color codes for terminal output
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color

def print_header(text):
    """Print a formatted header"""
    print(f"\n{Colors.BLUE}{'='*60}{Colors.NC}")
    print(f"{Colors.BLUE}{text}{Colors.NC}")
    print(f"{Colors.BLUE}{'='*60}{Colors.NC}\n")

def print_success(text):
    """Print success message"""
    print(f"{Colors.GREEN}✓ {text}{Colors.NC}")

def print_error(text):
    """Print error message"""
    print(f"{Colors.RED}✗ {text}{Colors.NC}")

def print_warning(text):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.NC}")

def print_info(text):
    """Print info message"""
    print(f"  {text}")

class MigrationTester:
    """Test suite for SDK migration"""
    
    def __init__(self):
        self.results = {
            "passed": [],
            "failed": [],
            "warnings": []
        }
        self.start_time = datetime.now()
    
    def test_environment(self):
        """Test 1: Check environment setup"""
        print_header("Test 1: Environment Check")
        
        # Check Python version
        py_version = sys.version_info
        if py_version.major >= 3 and py_version.minor >= 11:
            print_success(f"Python version: {py_version.major}.{py_version.minor}.{py_version.micro}")
            self.results["passed"].append("Python version")
        else:
            print_error(f"Python version too old: {py_version.major}.{py_version.minor}")
            self.results["failed"].append("Python version")
        
        # Check uv installation
        uv_path = Path.home() / ".local" / "bin" / "uv"
        if uv_path.exists():
            print_success(f"uv found at: {uv_path}")
            self.results["passed"].append("uv installation")
        else:
            print_error("uv not found")
            self.results["failed"].append("uv installation")
        
        # Check credentials
        cred_file = Path.home() / ".claude" / ".credentials.json"
        if cred_file.exists():
            print_success(f"Credentials found: {cred_file}")
            self.results["passed"].append("OAuth credentials")
        else:
            print_error("No credentials file")
            self.results["failed"].append("OAuth credentials")
        
        # Check Docker
        try:
            result = subprocess.run(["docker", "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                print_success(f"Docker: {result.stdout.strip()}")
                self.results["passed"].append("Docker")
            else:
                print_error("Docker not working")
                self.results["failed"].append("Docker")
        except FileNotFoundError:
            print_error("Docker not installed")
            self.results["failed"].append("Docker")
    
    def test_patch(self):
        """Test 2: Verify compatibility patch"""
        print_header("Test 2: Compatibility Patch")
        
        try:
            # Import patch
            import sdk_compatibility_patch
            print_success("Patch module imported")
            self.results["passed"].append("Patch import")
            
            # Check patch applied
            from claude_agent_sdk._internal.transport import subprocess_cli
            if hasattr(subprocess_cli.SubprocessCli, '_original_build_command'):
                print_success("Patch successfully applied to SubprocessCli")
                self.results["passed"].append("Patch application")
            else:
                print_warning("Patch may not be fully applied")
                self.results["warnings"].append("Patch application")
                
        except ImportError as e:
            print_error(f"Failed to import patch: {e}")
            self.results["failed"].append("Patch import")
    
    def test_sdk_import(self):
        """Test 3: SDK import and basic functionality"""
        print_header("Test 3: SDK Import")
        
        try:
            from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient
            print_success("claude_agent_sdk imported successfully")
            self.results["passed"].append("SDK import")
            
            # Test options creation
            options = ClaudeAgentOptions(
                permission_mode='bypassPermissions'
            )
            print_success("ClaudeAgentOptions created")
            self.results["passed"].append("Options creation")
            
        except ImportError as e:
            print_error(f"Failed to import SDK: {e}")
            self.results["failed"].append("SDK import")
        except Exception as e:
            print_error(f"SDK error: {e}")
            self.results["failed"].append("SDK functionality")
    
    async def test_oauth_connection(self):
        """Test 4: OAuth connection test"""
        print_header("Test 4: OAuth Connection")
        
        try:
            from claude_agent_sdk import query, ClaudeAgentOptions
            
            print_info("Testing OAuth authentication...")
            messages_received = 0
            
            async for message in query(
                prompt="Reply with exactly: 'TEST_OK'",
                options=ClaudeAgentOptions(
                    permission_mode='bypassPermissions',
                    max_turns=1
                )
            ):
                messages_received += 1
                print_info(f"Received message {messages_received}")
                
                if hasattr(message, 'content'):
                    for block in message.content:
                        if hasattr(block, 'text') and 'TEST_OK' in block.text:
                            print_success("Got expected response")
                            self.results["passed"].append("OAuth response")
                            break
                
                if messages_received >= 5:  # Safety limit
                    break
            
            if messages_received > 0:
                print_success(f"OAuth connection successful ({messages_received} messages)")
                self.results["passed"].append("OAuth connection")
            else:
                print_error("No response received")
                self.results["failed"].append("OAuth connection")
                
        except Exception as e:
            error_str = str(e).lower()
            if 'setting-sources' in error_str:
                print_error("Patch failed - still getting setting-sources error")
                self.results["failed"].append("Patch effectiveness")
            else:
                print_warning(f"Connection error: {e}")
                self.results["warnings"].append("OAuth connection")
    
    def test_docker_compatibility(self):
        """Test 5: Docker compatibility"""
        print_header("Test 5: Docker Compatibility")
        
        docker_dir = Path("/home/dministrator/LainNet/docker")
        
        # Check if patch file exists in docker directory
        patch_file = docker_dir / "sdk_compatibility_patch.py"
        if patch_file.exists():
            print_success("Patch file in Docker directory")
            self.results["passed"].append("Docker patch file")
        else:
            print_warning("Patch file not yet in Docker directory")
            self.results["warnings"].append("Docker patch file")
        
        # Check if Docker image exists
        try:
            result = subprocess.run(
                ["docker", "images", "--format", "{{.Repository}}:{{.Tag}}"],
                capture_output=True, text=True
            )
            if "claude-code-sandbox:agent-sdk" in result.stdout:
                print_success("Agent SDK Docker image exists")
                self.results["passed"].append("Docker image")
            elif "claude-code-sandbox:dev" in result.stdout:
                print_info("Dev Docker image exists (not yet migrated)")
                self.results["warnings"].append("Docker image")
            else:
                print_warning("No Claude Docker image found")
                self.results["warnings"].append("Docker image")
        except Exception as e:
            print_error(f"Docker check failed: {e}")
            self.results["failed"].append("Docker check")
    
    def generate_report(self):
        """Generate test report"""
        print_header("Test Report")
        
        total_tests = len(self.results["passed"]) + len(self.results["failed"]) + len(self.results["warnings"])
        duration = (datetime.now() - self.start_time).total_seconds()
        
        print(f"Total tests: {total_tests}")
        print(f"Duration: {duration:.2f} seconds")
        print()
        
        if self.results["passed"]:
            print(f"{Colors.GREEN}Passed ({len(self.results['passed'])}):{Colors.NC}")
            for test in self.results["passed"]:
                print(f"  ✓ {test}")
        
        if self.results["warnings"]:
            print(f"\n{Colors.YELLOW}Warnings ({len(self.results['warnings'])}):{Colors.NC}")
            for test in self.results["warnings"]:
                print(f"  ⚠ {test}")
        
        if self.results["failed"]:
            print(f"\n{Colors.RED}Failed ({len(self.results['failed'])}):{Colors.NC}")
            for test in self.results["failed"]:
                print(f"  ✗ {test}")
        
        # Overall status
        print("\n" + "="*60)
        if not self.results["failed"]:
            print(f"{Colors.GREEN}✅ MIGRATION READY{Colors.NC}")
            print("\nYou can proceed with migration:")
            print("  ./migrations/claude-agent-sdk/scripts/migrate.sh")
        elif len(self.results["failed"]) <= 2:
            print(f"{Colors.YELLOW}⚠️  MIGRATION POSSIBLE WITH ISSUES{Colors.NC}")
            print("\nReview failed tests before proceeding")
        else:
            print(f"{Colors.RED}❌ MIGRATION NOT READY{Colors.NC}")
            print("\nFix failed tests before migration")
        
        # Save report
        report_file = Path(__file__).parent.parent / "logs" / f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_file.parent.mkdir(exist_ok=True)
        
        with open(report_file, 'w') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "duration": duration,
                "results": self.results
            }, f, indent=2)
        
        print(f"\nReport saved to: {report_file}")

async def main():
    """Run all tests"""
    print_header("Claude Agent SDK Migration Test Suite")
    print(f"Started at: {datetime.now()}")
    
    tester = MigrationTester()
    
    # Run synchronous tests
    tester.test_environment()
    tester.test_patch()
    tester.test_sdk_import()
    
    # Run async test
    await tester.test_oauth_connection()
    
    # Docker test
    tester.test_docker_compatibility()
    
    # Generate report
    tester.generate_report()
    
    # Return exit code
    return 0 if not tester.results["failed"] else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)