#!/usr/bin/env python3
"""
Command-line setup utility for django-ollama test dashboard pytest integration.

This script helps developers set up the pytest plugin integration with minimal effort.

Usage:
    python setup_cli.py --install                # Install plugin integration
    python setup_cli.py --verify                 # Verify installation
    python setup_cli.py --test                   # Run integration tests
    python setup_cli.py --uninstall             # Remove plugin integration
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Dict, Any

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[SETUP] %(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


def setup_python_path():
    """Add test_dashboard to Python path for imports."""
    dashboard_dir = Path(__file__).parent.parent
    if str(dashboard_dir) not in sys.path:
        sys.path.insert(0, str(dashboard_dir))


def install_integration(project_root: Path = None) -> bool:
    """Install the pytest plugin integration."""
    try:
        setup_python_path()
        from plugin_setup import setup_dashboard_plugin

        logger.info("Installing django-ollama test dashboard pytest integration...")
        success = setup_dashboard_plugin(project_root)

        if success:
            logger.info("✅ Installation completed successfully!")
            print_usage_instructions()
        else:
            logger.error("❌ Installation failed. Check logs for details.")

        return success

    except ImportError as e:
        logger.error(f"❌ Failed to import setup modules: {e}")
        logger.error("Make sure you're running this from the correct directory")
        return False
    except Exception as e:
        logger.error(f"❌ Installation failed: {e}")
        return False


def verify_installation(project_root: Path = None) -> bool:
    """Verify the pytest plugin installation."""
    try:
        setup_python_path()
        from plugin_setup import verify_dashboard_plugin

        logger.info("Verifying django-ollama test dashboard integration...")
        results = verify_dashboard_plugin(project_root)

        print("\n=== Installation Verification Results ===")
        print(f"Plugin Available: {'✅' if results['plugin_available'] else '❌'}")
        print(f"Database Available: {'✅' if results['database_available'] else '❌'}")
        print(f"WebSocket Available: {'✅' if results['websocket_available'] else '❌'}")
        print(f"Pytest Integration: {'✅' if results['pytest_integration'] else '❌'}")

        print("\n=== Configuration Files ===")
        for filename, info in results['configuration_files'].items():
            exists_icon = "✅" if info['exists'] else "❌"
            if filename == 'pytest.ini':
                config_icon = "✅" if info.get('has_dashboard_plugin', False) else "❌"
                print(f"{filename}: {exists_icon} exists, {config_icon} configured")
            elif filename == 'conftest.py':
                config_icon = "✅" if info.get('has_dashboard_config', False) else "❌"
                print(f"{filename}: {exists_icon} exists, {config_icon} configured")

        if results['errors']:
            print("\n=== Errors ===")
            for error in results['errors']:
                print(f"❌ {error}")

        success = results['pytest_integration']
        if success:
            logger.info("✅ Verification successful - integration is ready!")
        else:
            logger.error("❌ Verification failed - installation may be incomplete")

        return success

    except ImportError as e:
        logger.error(f"❌ Failed to import verification modules: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Verification failed: {e}")
        return False


def run_integration_tests() -> bool:
    """Run the integration tests to verify functionality."""
    try:
        import subprocess
        import os

        logger.info("Running integration tests...")

        # Setup environment
        env = os.environ.copy()
        dashboard_path = str(Path(__file__).parent.parent.parent)
        if 'PYTHONPATH' in env:
            env['PYTHONPATH'] = f"{dashboard_path}:{env['PYTHONPATH']}"
        else:
            env['PYTHONPATH'] = dashboard_path

        # Run tests
        test_file = Path(__file__).parent / "test_integration.py"
        cmd = [sys.executable, "-m", "pytest", str(test_file), "-v"]

        result = subprocess.run(cmd, env=env, capture_output=True, text=True)

        if result.returncode == 0:
            logger.info("✅ Integration tests passed!")
            print(result.stdout)
            return True
        else:
            logger.error("❌ Integration tests failed!")
            print(result.stdout)
            print(result.stderr)
            return False

    except Exception as e:
        logger.error(f"❌ Failed to run integration tests: {e}")
        return False


def uninstall_integration(project_root: Path = None) -> bool:
    """Remove the pytest plugin integration."""
    try:
        if project_root is None:
            project_root = Path.cwd()

        logger.info("Removing django-ollama test dashboard pytest integration...")

        # Remove from pytest.ini
        pytest_ini = project_root / "pytest.ini"
        if pytest_ini.exists():
            content = pytest_ini.read_text()
            lines = content.splitlines()
            new_lines = []

            for line in lines:
                if "test_dashboard.plugins.pytest_dashboard" not in line:
                    new_lines.append(line)
                elif line.strip().startswith('pytest_plugins'):
                    # Remove our plugin from the plugins line
                    plugins_part = line.split('=', 1)[1].strip() if '=' in line else ""
                    plugins = [p.strip() for p in plugins_part.split(',')]
                    plugins = [p for p in plugins if p != "test_dashboard.plugins.pytest_dashboard"]

                    if plugins:
                        new_lines.append(f"pytest_plugins = {', '.join(plugins)}")

            pytest_ini.write_text('\n'.join(new_lines))
            logger.info("Updated pytest.ini")

        # Remove from conftest.py (more complex, just warn user)
        conftest_py = project_root / "conftest.py"
        if conftest_py.exists():
            content = conftest_py.read_text()
            if "test_dashboard.plugins.pytest_dashboard" in content:
                logger.warning("⚠️  Please manually remove dashboard integration from conftest.py")

        logger.info("✅ Uninstallation completed!")
        return True

    except Exception as e:
        logger.error(f"❌ Uninstallation failed: {e}")
        return False


def print_usage_instructions():
    """Print usage instructions for the developer."""
    print("\n" + "="*60)
    print("🎉 Django-Ollama Test Dashboard Integration Ready!")
    print("="*60)
    print("\nBasic Usage:")
    print("  pytest --dashboard                    # Enable dashboard")
    print("  pytest --dashboard-name=\"My Tests\"    # Custom run name")
    print("  pytest --dashboard-websocket         # Enable real-time updates")
    print("\nAdvanced Usage:")
    print("  pytest --dashboard \\")
    print("         --dashboard-db=custom.db \\")
    print("         --dashboard-websocket \\")
    print("         --dashboard-websocket-port=8765")
    print("\nDashboard Access:")
    print("  1. Run tests with --dashboard")
    print("  2. Open test_dashboard/launch_dashboard.py")
    print("  3. Access dashboard at http://localhost:8000")
    print("\nReal-time Updates:")
    print("  - Use --dashboard-websocket flag")
    print("  - Dashboard updates live during test execution")
    print("  - WebSocket server runs on port 8765 by default")
    print("\n" + "="*60)


def create_example_usage():
    """Create example usage files for the project."""
    try:
        project_root = Path.cwd()
        examples_dir = project_root / "test_dashboard_examples"
        examples_dir.mkdir(exist_ok=True)

        # Create example test file
        example_test = examples_dir / "test_dashboard_example.py"
        example_test.write_text('''"""
Example test file demonstrating dashboard integration.

Run with: pytest --dashboard test_dashboard_examples/test_dashboard_example.py
"""

import pytest
import time
import random


class TestDashboardDemo:
    """Demonstration tests for dashboard integration."""

    def test_fast_passing_test(self):
        """A fast test that always passes."""
        assert 1 + 1 == 2

    def test_slow_passing_test(self):
        """A slower test that always passes."""
        time.sleep(0.5)  # Simulate some work
        result = sum(range(100))
        assert result == 4950

    @pytest.mark.integration
    def test_integration_example(self):
        """Example integration test."""
        # Simulate integration test work
        time.sleep(0.2)
        assert "hello".upper() == "HELLO"

    def test_with_assertion_error(self):
        """Test that demonstrates assertion failure."""
        x = random.random()
        if x > 0.7:  # Sometimes fail
            assert False, f"Random failure with value {x}"
        else:
            assert True

    @pytest.mark.skip(reason="Demonstration of skipped test")
    def test_skipped_example(self):
        """This test will be skipped."""
        assert False

    @pytest.mark.slow
    def test_marked_as_slow(self):
        """Test marked as slow for dashboard filtering."""
        time.sleep(1.0)
        assert True

    def test_with_multiple_assertions(self):
        """Test with multiple assertions for assertion counting."""
        assert 1 < 2
        assert "hello" != "world"
        assert len([1, 2, 3]) == 3
        assert max([1, 5, 3]) == 5

    def test_error_handling_example(self):
        """Test that might raise an exception."""
        data = {"key": "value"}
        assert data["key"] == "value"
        # This might raise KeyError sometimes
        if random.random() > 0.8:
            return data["nonexistent_key"]
''')

        # Create Makefile for easy usage
        makefile = project_root / "Makefile.dashboard"
        makefile.write_text('''# Django-Ollama Test Dashboard Makefile
# Quick commands for dashboard integration

.PHONY: test-dashboard test-dashboard-live verify-dashboard clean-dashboard

# Run tests with dashboard integration
test-dashboard:
	pytest --dashboard --dashboard-name="Development Tests" -v

# Run tests with live WebSocket updates
test-dashboard-live:
	pytest --dashboard --dashboard-websocket --dashboard-name="Live Tests" -v

# Run example tests to populate dashboard
test-dashboard-demo:
	pytest --dashboard test_dashboard_examples/ --dashboard-name="Demo Tests" -v

# Verify dashboard integration
verify-dashboard:
	python test_dashboard/plugins/setup_cli.py --verify

# Launch dashboard web interface
launch-dashboard:
	python test_dashboard/launch_dashboard.py

# Clean dashboard database
clean-dashboard:
	rm -f test_dashboard.db

# Install dashboard integration
install-dashboard:
	python test_dashboard/plugins/setup_cli.py --install

# Run integration tests
test-integration:
	python test_dashboard/plugins/setup_cli.py --test

help:
	@echo "Available targets:"
	@echo "  test-dashboard      - Run tests with dashboard integration"
	@echo "  test-dashboard-live - Run tests with live WebSocket updates"
	@echo "  test-dashboard-demo - Run demo tests to populate dashboard"
	@echo "  verify-dashboard    - Verify dashboard integration setup"
	@echo "  launch-dashboard    - Launch dashboard web interface"
	@echo "  clean-dashboard     - Clean dashboard database"
	@echo "  install-dashboard   - Install dashboard integration"
	@echo "  test-integration    - Run integration tests"
''')

        logger.info(f"✅ Created example files in {examples_dir}")
        logger.info(f"✅ Created Makefile.dashboard with common commands")

        return True

    except Exception as e:
        logger.error(f"❌ Failed to create example files: {e}")
        return False


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Django-Ollama Test Dashboard Pytest Integration Setup",
        epilog="For more information, visit: https://github.com/django-ollama/test-dashboard"
    )

    parser.add_argument(
        "--install",
        action="store_true",
        help="Install pytest plugin integration"
    )

    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify installation status"
    )

    parser.add_argument(
        "--test",
        action="store_true",
        help="Run integration tests"
    )

    parser.add_argument(
        "--uninstall",
        action="store_true",
        help="Remove pytest plugin integration"
    )

    parser.add_argument(
        "--examples",
        action="store_true",
        help="Create example usage files"
    )

    parser.add_argument(
        "--project-root",
        type=Path,
        default=None,
        help="Project root directory (default: current directory)"
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output"
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    project_root = args.project_root or Path.cwd()

    # Execute requested actions
    success = True

    if args.install:
        success &= install_integration(project_root)

    if args.verify:
        success &= verify_installation(project_root)

    if args.test:
        success &= run_integration_tests()

    if args.uninstall:
        success &= uninstall_integration(project_root)

    if args.examples:
        success &= create_example_usage()

    # If no actions specified, show help and verify
    if not any([args.install, args.verify, args.test, args.uninstall, args.examples]):
        parser.print_help()
        print("\nCurrent installation status:")
        verify_installation(project_root)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()