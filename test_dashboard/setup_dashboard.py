#!/usr/bin/env python3
"""
Django-Ollama Test Dashboard Setup Automation Script

Comprehensive setup and validation script that:
- Validates system requirements
- Sets up database and schema
- Installs dependencies
- Configures environment
- Validates installation
- Provides helpful troubleshooting

Usage:
    python setup_dashboard.py
    python setup_dashboard.py --dev
    python setup_dashboard.py --production
    python setup_dashboard.py --validate-only
    python setup_dashboard.py --reset
"""

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import urllib.request


class Colors:
    """ANSI color codes for terminal output."""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_colored(message: str, color: str = Colors.ENDC):
    """Print colored message to terminal."""
    print(f"{color}{message}{Colors.ENDC}")


def print_success(message: str):
    """Print success message."""
    print_colored(f"✅ {message}", Colors.OKGREEN)


def print_warning(message: str):
    """Print warning message."""
    print_colored(f"⚠️  {message}", Colors.WARNING)


def print_error(message: str):
    """Print error message."""
    print_colored(f"❌ {message}", Colors.FAIL)


def print_info(message: str):
    """Print info message."""
    print_colored(f"ℹ️  {message}", Colors.OKBLUE)


def print_header(message: str):
    """Print section header."""
    print_colored(f"\n{'=' * 60}", Colors.HEADER)
    print_colored(f"{message.upper()}", Colors.HEADER + Colors.BOLD)
    print_colored(f"{'=' * 60}", Colors.HEADER)


class SystemValidator:
    """Validate system requirements and environment."""

    def __init__(self):
        self.issues = []
        self.warnings = []

    def check_python_version(self) -> bool:
        """Check Python version requirements."""
        print_info("Checking Python version...")

        version = sys.version_info
        required_version = (3, 9)

        if version >= required_version:
            print_success(f"Python {version.major}.{version.minor}.{version.micro} is supported")
            return True
        else:
            self.issues.append(f"Python {version.major}.{version.minor} is too old. Minimum required: {required_version[0]}.{required_version[1]}")
            print_error(f"Python {version.major}.{version.minor} is too old")
            return False

    def check_system_dependencies(self) -> bool:
        """Check system-level dependencies."""
        print_info("Checking system dependencies...")

        dependencies = {
            'git': 'Git version control',
            'curl': 'HTTP client for testing',
        }

        missing = []
        for cmd, description in dependencies.items():
            if shutil.which(cmd):
                print_success(f"{cmd} found ({description})")
            else:
                missing.append(cmd)
                self.warnings.append(f"{cmd} not found - {description}")

        if missing:
            print_warning(f"Optional dependencies missing: {', '.join(missing)}")

        return True  # These are optional

    def check_python_packages(self) -> bool:
        """Check required Python packages."""
        print_info("Checking Python packages...")

        required_packages = [
            ('fastapi', 'Web framework'),
            ('uvicorn', 'ASGI server'),
            ('websockets', 'WebSocket support'),
            ('requests', 'HTTP client'),
        ]

        missing = []
        for package, description in required_packages:
            try:
                __import__(package)
                print_success(f"{package} is available ({description})")
            except ImportError:
                missing.append(package)
                self.issues.append(f"Missing required package: {package}")

        if missing:
            print_error(f"Missing required packages: {', '.join(missing)}")
            return False

        return True

    def check_disk_space(self) -> bool:
        """Check available disk space."""
        print_info("Checking disk space...")

        try:
            statvfs = os.statvfs('.')
            available_bytes = statvfs.f_bavail * statvfs.f_frsize
            available_mb = available_bytes / (1024 * 1024)

            required_mb = 100  # Minimum 100MB

            if available_mb >= required_mb:
                print_success(f"{available_mb:.1f}MB available (required: {required_mb}MB)")
                return True
            else:
                self.issues.append(f"Insufficient disk space: {available_mb:.1f}MB available, {required_mb}MB required")
                print_error(f"Insufficient disk space")
                return False

        except Exception as e:
            self.warnings.append(f"Could not check disk space: {e}")
            print_warning("Could not check disk space")
            return True

    def check_network_connectivity(self) -> bool:
        """Check network connectivity for downloads."""
        print_info("Checking network connectivity...")

        try:
            urllib.request.urlopen('https://pypi.org/', timeout=10)
            print_success("Network connectivity OK")
            return True
        except Exception as e:
            self.warnings.append(f"Network connectivity issue: {e}")
            print_warning("Network connectivity may be limited")
            return True

    def validate_all(self) -> bool:
        """Run all validation checks."""
        print_header("System Requirements Validation")

        checks = [
            self.check_python_version(),
            self.check_system_dependencies(),
            self.check_python_packages(),
            self.check_disk_space(),
            self.check_network_connectivity(),
        ]

        # Print summary
        print_info(f"\nValidation Summary:")
        print(f"  Issues: {len(self.issues)}")
        print(f"  Warnings: {len(self.warnings)}")

        if self.issues:
            print_error("\nCritical Issues:")
            for issue in self.issues:
                print(f"  • {issue}")

        if self.warnings:
            print_warning("\nWarnings:")
            for warning in self.warnings:
                print(f"  • {warning}")

        return len(self.issues) == 0


class DashboardSetup:
    """Main setup and configuration class."""

    def __init__(self, mode: str = "development"):
        self.mode = mode
        self.project_root = Path(__file__).parent
        self.setup_log = []

    def log_step(self, step: str, success: bool = True, details: str = ""):
        """Log setup step."""
        self.setup_log.append({
            'step': step,
            'success': success,
            'details': details,
            'timestamp': time.time()
        })

    def install_dependencies(self) -> bool:
        """Install required Python dependencies."""
        print_header("Installing Dependencies")

        requirements_file = self.project_root / "requirements.txt"

        if not requirements_file.exists():
            print_warning("requirements.txt not found, creating minimal requirements...")
            minimal_requirements = [
                "fastapi>=0.104.0",
                "uvicorn[standard]>=0.24.0",
                "websockets>=12.0",
                "requests>=2.31.0",
                "tabulate>=0.9.0",
            ]

            if self.mode == "development":
                minimal_requirements.extend([
                    "pytest>=7.4.0",
                    "pytest-asyncio>=0.21.0",
                    "psutil>=5.9.0",
                ])

            with open(requirements_file, 'w') as f:
                f.write('\n'.join(minimal_requirements))

        print_info(f"Installing dependencies from {requirements_file}...")

        try:
            result = subprocess.run([
                sys.executable, "-m", "pip", "install", "-r", str(requirements_file)
            ], capture_output=True, text=True, timeout=300)

            if result.returncode == 0:
                print_success("Dependencies installed successfully")
                self.log_step("install_dependencies", True)
                return True
            else:
                print_error(f"Failed to install dependencies: {result.stderr}")
                self.log_step("install_dependencies", False, result.stderr)
                return False

        except Exception as e:
            print_error(f"Exception during dependency installation: {e}")
            self.log_step("install_dependencies", False, str(e))
            return False

    def setup_database(self) -> bool:
        """Set up the database and schema."""
        print_header("Setting up Database")

        try:
            # Import after dependencies are installed
            from database import TestDashboardDB
            from migrations.migration_manager import MigrationManager

            db_path = self.project_root / "test_dashboard.db"

            # Remove existing database in reset mode
            if db_path.exists() and getattr(self, 'reset_mode', False):
                print_info("Removing existing database...")
                db_path.unlink()

            print_info(f"Creating database at {db_path}...")

            # Initialize database
            db = TestDashboardDB(str(db_path))

            # Verify database structure
            conn = db._get_connection()
            cursor = conn.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
            """)
            tables = [row[0] for row in cursor.fetchall()]

            expected_tables = ['test_runs', 'test_results', 'coverage_data', 'test_metrics']
            missing_tables = set(expected_tables) - set(tables)

            if missing_tables:
                print_error(f"Missing database tables: {missing_tables}")
                self.log_step("setup_database", False, f"Missing tables: {missing_tables}")
                db.close()
                return False

            print_success(f"Database created with tables: {', '.join(tables)}")

            # Test basic database operations
            print_info("Testing database operations...")

            test_run_id = db.create_test_run("setup_validation_test")

            if test_run_id:
                print_success("Database operations test passed")
                # Clean up test data
                db.update_test_run(test_run_id, status='PASSED')
            else:
                print_error("Database operations test failed")
                self.log_step("setup_database", False, "Database operations test failed")
                db.close()
                return False

            db.close()
            self.log_step("setup_database", True)
            return True

        except Exception as e:
            print_error(f"Database setup failed: {e}")
            self.log_step("setup_database", False, str(e))
            return False

    def create_configuration_files(self) -> bool:
        """Create configuration files."""
        print_header("Creating Configuration Files")

        try:
            # Create .env file
            env_file = self.project_root / ".env"

            if not env_file.exists() or getattr(self, 'reset_mode', False):
                print_info("Creating .env configuration file...")

                env_config = {
                    'DASHBOARD_HOST': '0.0.0.0',
                    'DASHBOARD_PORT': '8080',
                    'DASHBOARD_DB_PATH': 'test_dashboard.db',
                    'WEBSOCKET_ENABLED': 'true',
                    'WEBSOCKET_PORT': '8765',
                    'LOG_LEVEL': 'info' if self.mode == 'production' else 'debug',
                    'CORS_ORIGINS': '*' if self.mode == 'development' else 'https://dashboard.company.com',
                    'AUTH_REQUIRED': 'false' if self.mode == 'development' else 'true',
                    'DASHBOARD_RETENTION_DAYS': '30',
                    'DB_BACKUP_ENABLED': 'true' if self.mode == 'production' else 'false',
                }

                with open(env_file, 'w') as f:
                    f.write("# Django-Ollama Test Dashboard Configuration\n")
                    f.write(f"# Generated for {self.mode} mode\n\n")

                    for key, value in env_config.items():
                        f.write(f"{key}={value}\n")

                print_success(f".env file created for {self.mode} mode")

            # Create systemd service file for production
            if self.mode == 'production':
                self.create_systemd_service()

            # Create docker-compose.yml
            self.create_docker_compose()

            self.log_step("create_configuration_files", True)
            return True

        except Exception as e:
            print_error(f"Configuration file creation failed: {e}")
            self.log_step("create_configuration_files", False, str(e))
            return False

    def create_systemd_service(self):
        """Create systemd service file for production deployment."""
        print_info("Creating systemd service file...")

        service_file = self.project_root / "dashboard.service"
        current_user = os.getenv('USER', 'dashboard')
        current_path = self.project_root.absolute()

        service_content = f"""[Unit]
Description=Django-Ollama Test Dashboard
After=network.target

[Service]
Type=simple
User={current_user}
WorkingDirectory={current_path}
Environment=PATH={current_path}
ExecStart={sys.executable} server.py --host 0.0.0.0 --port 8080
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
"""

        with open(service_file, 'w') as f:
            f.write(service_content)

        print_success(f"Systemd service file created: {service_file}")
        print_info(f"To install: sudo cp {service_file} /etc/systemd/system/")
        print_info("To enable: sudo systemctl enable dashboard.service")
        print_info("To start: sudo systemctl start dashboard.service")

    def create_docker_compose(self):
        """Create docker-compose.yml file."""
        print_info("Creating docker-compose.yml...")

        if self.mode == 'development':
            compose_content = """version: '3.8'

services:
  dashboard:
    build:
      context: .
      dockerfile: Dockerfile.dev
    ports:
      - "8080:8080"
      - "8765:8765"  # WebSocket port
    volumes:
      - .:/app
      - dashboard_data:/app/data
    environment:
      - DASHBOARD_DB_PATH=/app/data/dashboard.db
      - LOG_LEVEL=debug
      - WEBSOCKET_ENABLED=true
    command: python server.py --reload --log-level debug

volumes:
  dashboard_data:
"""
        else:  # production
            compose_content = """version: '3.8'

services:
  dashboard:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8080:8080"
    volumes:
      - dashboard_data:/app/data
      - ./backups:/app/backups
    environment:
      - DASHBOARD_DB_PATH=/app/data/dashboard.db
      - LOG_LEVEL=info
      - DB_RETENTION_DAYS=90
      - BACKUP_ENABLED=true
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - dashboard
    restart: unless-stopped

volumes:
  dashboard_data:
"""

        compose_file = self.project_root / "docker-compose.yml"
        with open(compose_file, 'w') as f:
            f.write(compose_content)

        print_success("docker-compose.yml created")

    def create_dockerfiles(self):
        """Create Dockerfiles for containerization."""
        print_info("Creating Dockerfiles...")

        # Development Dockerfile
        dev_dockerfile = self.project_root / "Dockerfile.dev"
        dev_content = """FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    curl \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directory
RUN mkdir -p /app/data

# Expose ports
EXPOSE 8080 8765

# Run server with development settings
CMD ["python", "server.py", "--host", "0.0.0.0", "--port", "8080", "--reload"]
"""

        with open(dev_dockerfile, 'w') as f:
            f.write(dev_content)

        # Production Dockerfile
        prod_dockerfile = self.project_root / "Dockerfile"
        prod_content = """FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    curl \\
    sqlite3 \\
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r dashboard && useradd -r -g dashboard dashboard

WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directory and set permissions
RUN mkdir -p /app/data && chown -R dashboard:dashboard /app

USER dashboard

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost:8080/api/health || exit 1

# Run server
CMD ["python", "server.py", "--host", "0.0.0.0", "--port", "8080"]
"""

        with open(prod_dockerfile, 'w') as f:
            f.write(prod_content)

        print_success("Dockerfiles created (Dockerfile and Dockerfile.dev)")

    def validate_installation(self) -> bool:
        """Validate the installation by running basic tests."""
        print_header("Validating Installation")

        try:
            # Test database functionality
            print_info("Testing database functionality...")

            from database import TestDashboardDB

            db_path = self.project_root / "test_dashboard.db"
            db = TestDashboardDB(str(db_path))

            # Test creating a run
            test_run_id = db.create_test_run("validation_test")

            # Test querying
            run = db.get_test_run(test_run_id)
            if not run:
                raise Exception("Failed to retrieve created test run")

            # Test dashboard summary
            summary = db.get_dashboard_summary()
            if not isinstance(summary, dict):
                raise Exception("Dashboard summary query failed")

            db.close()
            print_success("Database functionality validated")

            # Test server startup (quick test)
            print_info("Testing server startup...")

            try:
                result = subprocess.run([
                    sys.executable, "server.py", "--help"
                ], capture_output=True, text=True, timeout=10, cwd=self.project_root)

                if result.returncode == 0 and "Django-Ollama Test Dashboard Server" in result.stdout:
                    print_success("Server startup validated")
                else:
                    print_warning("Server startup test inconclusive")

            except Exception as e:
                print_warning(f"Server startup test failed: {e}")

            # Test import of key modules
            print_info("Testing module imports...")

            modules_to_test = [
                'database',
                'models',
                'server',
                'plugins.pytest_dashboard',
            ]

            for module in modules_to_test:
                try:
                    __import__(module)
                    print_success(f"Module {module} imports successfully")
                except ImportError as e:
                    print_error(f"Module {module} import failed: {e}")
                    return False

            self.log_step("validate_installation", True)
            return True

        except Exception as e:
            print_error(f"Installation validation failed: {e}")
            self.log_step("validate_installation", False, str(e))
            return False

    def create_launch_scripts(self):
        """Create convenient launch scripts."""
        print_info("Creating launch scripts...")

        # Shell script for Unix systems
        if platform.system() != 'Windows':
            launch_script = self.project_root / "launch.sh"
            script_content = f"""#!/bin/bash
# Django-Ollama Test Dashboard Launch Script

# Set working directory to script location
cd "$(dirname "$0")"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Launch dashboard with appropriate settings for {self.mode}
if [ "{self.mode}" = "development" ]; then
    echo "🧪 Launching Test Dashboard (Development Mode)"
    python server.py --host 127.0.0.1 --port 8080 --reload --log-level debug
else
    echo "🧪 Launching Test Dashboard (Production Mode)"
    python server.py --host 0.0.0.0 --port 8080 --log-level info
fi
"""

            with open(launch_script, 'w') as f:
                f.write(script_content)

            # Make executable
            os.chmod(launch_script, 0o755)
            print_success(f"Launch script created: {launch_script}")

        # Batch script for Windows
        bat_script = self.project_root / "launch.bat"
        bat_content = f"""@echo off
REM Django-Ollama Test Dashboard Launch Script

REM Set working directory to script location
cd /d "%~dp0"

REM Activate virtual environment if it exists
if exist "venv\\Scripts\\activate.bat" (
    call venv\\Scripts\\activate.bat
)

REM Launch dashboard
echo 🧪 Launching Test Dashboard ({self.mode.title()} Mode)
if "{self.mode}" == "development" (
    python server.py --host 127.0.0.1 --port 8080 --reload --log-level debug
) else (
    python server.py --host 0.0.0.0 --port 8080 --log-level info
)

pause
"""

        with open(bat_script, 'w') as f:
            f.write(bat_content)

        print_success(f"Windows batch script created: {bat_script}")

    def print_completion_summary(self):
        """Print setup completion summary and next steps."""
        print_header("Setup Complete!")

        print_success("Django-Ollama Test Dashboard has been set up successfully!")

        print_info("\n📁 Files Created:")
        created_files = [
            "test_dashboard.db (SQLite database)",
            ".env (configuration file)",
            "docker-compose.yml (Docker deployment)",
            "Dockerfile & Dockerfile.dev (containerization)",
            "launch.sh / launch.bat (launch scripts)",
        ]

        if self.mode == 'production':
            created_files.append("dashboard.service (systemd service)")

        for file in created_files:
            print(f"  ✓ {file}")

        print_info("\n🚀 Next Steps:")

        if self.mode == 'development':
            print("  1. Start the dashboard server:")
            print("     python server.py --reload")
            print("  2. Open your browser to http://localhost:8080")
            print("  3. Run tests with dashboard integration:")
            print("     pytest --dashboard --dashboard-websocket tests/")
        else:
            print("  1. Review the configuration in .env")
            print("  2. Set up SSL certificates (for HTTPS)")
            print("  3. Configure nginx reverse proxy")
            print("  4. Install systemd service:")
            print("     sudo cp dashboard.service /etc/systemd/system/")
            print("     sudo systemctl enable dashboard.service")
            print("     sudo systemctl start dashboard.service")

        print_info("\n📚 Documentation:")
        print("  • Installation Guide: docs/INSTALLATION.md")
        print("  • API Reference: docs/API_REFERENCE.md")
        print("  • User Guide: docs/DASHBOARD_GUIDE.md")

        print_info("\n🧪 Test Your Installation:")
        print("  • Run validation tests: python test_integration_comprehensive.py")
        print("  • Run benchmarks: python benchmark_dashboard.py --quick")
        print("  • Check health: curl http://localhost:8080/api/health")

        # Print any issues from setup log
        failed_steps = [log for log in self.setup_log if not log['success']]
        if failed_steps:
            print_warning("\n⚠️  Issues During Setup:")
            for step in failed_steps:
                print(f"  • {step['step']}: {step['details']}")

    def reset_installation(self) -> bool:
        """Reset/clean installation."""
        print_header("Resetting Installation")

        files_to_remove = [
            'test_dashboard.db',
            '.env',
            'docker-compose.yml',
            'Dockerfile',
            'Dockerfile.dev',
            'dashboard.service',
            'launch.sh',
            'launch.bat',
        ]

        removed_count = 0

        for filename in files_to_remove:
            file_path = self.project_root / filename

            if file_path.exists():
                try:
                    file_path.unlink()
                    print_info(f"Removed: {filename}")
                    removed_count += 1
                except Exception as e:
                    print_warning(f"Could not remove {filename}: {e}")

        if removed_count > 0:
            print_success(f"Reset complete. Removed {removed_count} files.")
        else:
            print_info("No files to remove.")

        return True

    def run_setup(self, reset: bool = False) -> bool:
        """Run the complete setup process."""
        print_colored("🧪 Django-Ollama Test Dashboard Setup", Colors.HEADER + Colors.BOLD)
        print_colored(f"Mode: {self.mode.upper()}", Colors.OKCYAN)
        print_colored(f"Python: {sys.version}", Colors.OKCYAN)
        print_colored(f"Platform: {platform.platform()}", Colors.OKCYAN)

        self.reset_mode = reset

        if reset:
            self.reset_installation()

        steps = [
            ("Installing Dependencies", self.install_dependencies),
            ("Setting up Database", self.setup_database),
            ("Creating Configuration Files", self.create_configuration_files),
            ("Creating Docker Files", self.create_dockerfiles),
            ("Creating Launch Scripts", self.create_launch_scripts),
            ("Validating Installation", self.validate_installation),
        ]

        for step_name, step_func in steps:
            print_info(f"\nRunning: {step_name}...")

            if not step_func():
                print_error(f"Setup failed at step: {step_name}")
                return False

        self.print_completion_summary()
        return True


def main():
    """Main setup function."""
    parser = argparse.ArgumentParser(description="Django-Ollama Test Dashboard Setup")
    parser.add_argument("--dev", action="store_true", help="Setup for development mode")
    parser.add_argument("--production", action="store_true", help="Setup for production mode")
    parser.add_argument("--validate-only", action="store_true", help="Only run system validation")
    parser.add_argument("--reset", action="store_true", help="Reset/clean existing installation")
    parser.add_argument("--mode", choices=['development', 'production'], help="Explicit mode selection")

    args = parser.parse_args()

    # Determine setup mode
    if args.mode:
        mode = args.mode
    elif args.production:
        mode = 'production'
    else:
        mode = 'development'  # Default to development

    # Run system validation first
    validator = SystemValidator()
    validation_passed = validator.validate_all()

    if args.validate_only:
        sys.exit(0 if validation_passed else 1)

    if not validation_passed:
        print_error("\nSystem validation failed. Please fix the issues above before proceeding.")
        sys.exit(1)

    # Run setup
    setup = DashboardSetup(mode)
    success = setup.run_setup(reset=args.reset)

    if success:
        print_colored("\n🎉 Setup completed successfully!", Colors.OKGREEN + Colors.BOLD)
        sys.exit(0)
    else:
        print_error("\n❌ Setup failed. Check the output above for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()