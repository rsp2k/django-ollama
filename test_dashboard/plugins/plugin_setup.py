"""
Plugin setup utilities for django-ollama test dashboard integration.

This module provides utilities for setting up and configuring the
pytest plugin integration with the test dashboard.
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional
import shutil


class PluginSetup:
    """
    Utility class for setting up pytest plugin integration.

    Handles plugin registration, configuration file management,
    and integration verification.
    """

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path.cwd()
        self.dashboard_dir = Path(__file__).parent.parent
        self.logger = logging.getLogger(__name__)

    def register_plugin(self) -> bool:
        """
        Register the dashboard plugin with pytest.

        This method updates or creates pytest configuration to include
        the dashboard plugin automatically.
        """
        try:
            # Check if pytest.ini exists
            pytest_ini = self.project_root / "pytest.ini"

            if pytest_ini.exists():
                return self._update_pytest_ini(pytest_ini)
            else:
                return self._create_pytest_ini(pytest_ini)

        except Exception as e:
            self.logger.error(f"Failed to register plugin: {e}")
            return False

    def _update_pytest_ini(self, pytest_ini: Path) -> bool:
        """Update existing pytest.ini to include dashboard plugin."""
        try:
            # Read current configuration
            content = pytest_ini.read_text()
            lines = content.splitlines()

            # Check if addopts section exists
            addopts_section = None
            plugin_already_added = False

            for i, line in enumerate(lines):
                if line.strip().startswith('addopts'):
                    addopts_section = i
                if 'test_dashboard.plugins.pytest_dashboard' in line:
                    plugin_already_added = True
                    break

            if plugin_already_added:
                self.logger.info("Dashboard plugin already registered in pytest.ini")
                return True

            # Find the plugins section or create one
            plugins_section = None
            for i, line in enumerate(lines):
                if line.strip().startswith('pytest_plugins'):
                    plugins_section = i
                    break

            if plugins_section is not None:
                # Update existing plugins line
                plugins_line = lines[plugins_section]
                if 'test_dashboard.plugins.pytest_dashboard' not in plugins_line:
                    # Add our plugin to the existing list
                    if '=' in plugins_line:
                        parts = plugins_line.split('=', 1)
                        existing_plugins = parts[1].strip()
                        if existing_plugins:
                            new_plugins = f"{existing_plugins}, test_dashboard.plugins.pytest_dashboard"
                        else:
                            new_plugins = "test_dashboard.plugins.pytest_dashboard"
                        lines[plugins_section] = f"pytest_plugins = {new_plugins}"
                    else:
                        lines[plugins_section] = "pytest_plugins = test_dashboard.plugins.pytest_dashboard"
            else:
                # Add plugins section
                lines.append("")
                lines.append("# Dashboard plugin integration")
                lines.append("pytest_plugins = test_dashboard.plugins.pytest_dashboard")

            # Write back the configuration
            pytest_ini.write_text("\n".join(lines))
            self.logger.info("Updated pytest.ini with dashboard plugin")
            return True

        except Exception as e:
            self.logger.error(f"Failed to update pytest.ini: {e}")
            return False

    def _create_pytest_ini(self, pytest_ini: Path) -> bool:
        """Create new pytest.ini with dashboard plugin configuration."""
        try:
            content = """[tool:pytest]
python_files = tests.py test_*.py *_tests.py
python_classes = Test*
python_functions = test_*

# Dashboard plugin integration
pytest_plugins = test_dashboard.plugins.pytest_dashboard

addopts =
    --strict-markers
    --strict-config
    --verbose
    --tb=short

markers =
    slow: marks tests as slow
    integration: marks tests as integration tests
    unit: marks tests as unit tests
    dashboard_track: Mark test for special dashboard tracking
    dashboard_ignore: Mark test to ignore in dashboard (still runs)

testpaths = tests
"""
            pytest_ini.write_text(content)
            self.logger.info("Created pytest.ini with dashboard plugin")
            return True

        except Exception as e:
            self.logger.error(f"Failed to create pytest.ini: {e}")
            return False

    def setup_conftest(self) -> bool:
        """
        Setup or update conftest.py in the project root.

        Ensures that the dashboard plugin is properly configured
        for the project.
        """
        try:
            conftest_path = self.project_root / "conftest.py"
            dashboard_conftest = self.dashboard_dir / "plugins" / "conftest.py"

            if not dashboard_conftest.exists():
                self.logger.warning("Dashboard conftest.py not found")
                return False

            dashboard_content = dashboard_conftest.read_text()

            if conftest_path.exists():
                # Merge with existing conftest
                existing_content = conftest_path.read_text()
                if "test_dashboard.plugins.pytest_dashboard" not in existing_content:
                    merged_content = existing_content + "\n\n" + dashboard_content
                    conftest_path.write_text(merged_content)
                    self.logger.info("Updated existing conftest.py with dashboard integration")
                else:
                    self.logger.info("Dashboard integration already present in conftest.py")
            else:
                # Create new conftest with dashboard integration
                conftest_path.write_text(dashboard_content)
                self.logger.info("Created conftest.py with dashboard integration")

            return True

        except Exception as e:
            self.logger.error(f"Failed to setup conftest.py: {e}")
            return False

    def verify_installation(self) -> Dict[str, Any]:
        """
        Verify that the dashboard plugin is properly installed.

        Returns a dictionary with verification results.
        """
        results = {
            'plugin_available': False,
            'database_available': False,
            'websocket_available': False,
            'pytest_integration': False,
            'configuration_files': {},
            'errors': []
        }

        try:
            # Check plugin availability
            try:
                from test_dashboard.plugins.pytest_dashboard import dashboard_plugin
                results['plugin_available'] = True
            except ImportError as e:
                results['errors'].append(f"Plugin import failed: {e}")

            # Check database availability
            try:
                from test_dashboard.database import TestDashboardDB
                results['database_available'] = True
            except ImportError as e:
                results['errors'].append(f"Database module unavailable: {e}")

            # Check WebSocket availability
            try:
                from test_dashboard.plugins.realtime import RealTimeBroadcaster
                results['websocket_available'] = True
            except ImportError as e:
                results['errors'].append(f"WebSocket module unavailable: {e}")

            # Check configuration files
            pytest_ini = self.project_root / "pytest.ini"
            conftest_py = self.project_root / "conftest.py"

            results['configuration_files'] = {
                'pytest.ini': {
                    'exists': pytest_ini.exists(),
                    'has_dashboard_plugin': False
                },
                'conftest.py': {
                    'exists': conftest_py.exists(),
                    'has_dashboard_config': False
                }
            }

            if pytest_ini.exists():
                content = pytest_ini.read_text()
                results['configuration_files']['pytest.ini']['has_dashboard_plugin'] = \
                    'test_dashboard.plugins.pytest_dashboard' in content

            if conftest_py.exists():
                content = conftest_py.read_text()
                results['configuration_files']['conftest.py']['has_dashboard_config'] = \
                    'test_dashboard.plugins.pytest_dashboard' in content

            # Overall pytest integration check
            results['pytest_integration'] = (
                results['plugin_available'] and
                results['database_available'] and
                (results['configuration_files']['pytest.ini']['has_dashboard_plugin'] or
                 results['configuration_files']['conftest.py']['has_dashboard_config'])
            )

        except Exception as e:
            results['errors'].append(f"Verification failed: {e}")

        return results

    def install(self) -> bool:
        """
        Complete installation of the dashboard plugin integration.

        Performs all necessary setup steps for the dashboard plugin.
        """
        success = True
        self.logger.info("Starting dashboard plugin installation...")

        # Step 1: Register plugin
        if not self.register_plugin():
            self.logger.error("Failed to register plugin")
            success = False

        # Step 2: Setup conftest (optional)
        if not self.setup_conftest():
            self.logger.warning("Failed to setup conftest.py (non-critical)")

        # Step 3: Verify installation
        verification = self.verify_installation()
        if not verification['pytest_integration']:
            self.logger.error("Installation verification failed")
            self.logger.error(f"Errors: {verification['errors']}")
            success = False

        if success:
            self.logger.info("Dashboard plugin installation completed successfully!")
            self.logger.info("You can now use: pytest --dashboard")
        else:
            self.logger.error("Dashboard plugin installation failed")

        return success


def setup_dashboard_plugin(project_root: Optional[Path] = None) -> bool:
    """
    Convenience function to set up dashboard plugin integration.

    Args:
        project_root: Path to the project root directory

    Returns:
        True if setup was successful, False otherwise
    """
    setup = PluginSetup(project_root)
    return setup.install()


def verify_dashboard_plugin(project_root: Optional[Path] = None) -> Dict[str, Any]:
    """
    Convenience function to verify dashboard plugin integration.

    Args:
        project_root: Path to the project root directory

    Returns:
        Dictionary with verification results
    """
    setup = PluginSetup(project_root)
    return setup.verify_installation()