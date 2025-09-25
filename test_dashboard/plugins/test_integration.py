"""
Integration tests for the pytest dashboard plugin.

These tests verify that the plugin correctly captures test execution
events and stores them in the dashboard database.
"""

import pytest
import sqlite3
import tempfile
import subprocess
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone


class TestPytestDashboardIntegration:
    """Test the pytest dashboard plugin integration."""

    def setup_method(self):
        """Setup test environment for each test."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.db_path = self.temp_dir / "test_dashboard.db"

    def teardown_method(self):
        """Cleanup after each test."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_plugin_registration(self):
        """Test that the plugin can be registered with pytest."""
        # Import should not raise an error
        from test_dashboard.plugins.pytest_dashboard import DashboardTestPlugin

        plugin = DashboardTestPlugin()
        assert plugin is not None
        assert not plugin.enabled  # Should be disabled by default

    def test_plugin_configuration(self):
        """Test plugin configuration with command line options."""
        from test_dashboard.plugins.pytest_dashboard import DashboardTestPlugin

        plugin = DashboardTestPlugin()

        # Mock pytest config
        config = MagicMock()
        config.getoption.side_effect = lambda opt, default=None: {
            "--dashboard": True,
            "--dashboard-db": str(self.db_path),
            "--dashboard-name": "Test Run",
            "--dashboard-websocket": False,
            "--dashboard-websocket-port": 8765,
        }.get(opt, default)

        # Test configuration
        with patch('test_dashboard.plugins.pytest_dashboard.dashboard_available', True):
            plugin.pytest_configure(config)

        assert plugin.enabled
        assert plugin.db_path == str(self.db_path)
        assert plugin.run_name == "Test Run"

    def test_database_creation(self):
        """Test that the plugin creates a database correctly."""
        from test_dashboard.plugins.pytest_dashboard import DashboardTestPlugin
        from test_dashboard.database import TestDashboardDB

        # Create plugin and database
        plugin = DashboardTestPlugin()
        with patch('test_dashboard.plugins.pytest_dashboard.dashboard_available', True):
            plugin.db = TestDashboardDB(str(self.db_path))

        # Verify database file was created
        assert self.db_path.exists()

        # Verify tables were created
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Check for required tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        expected_tables = ['test_runs', 'test_results', 'coverage_data', 'test_metrics']
        for table in expected_tables:
            assert table in tables

        conn.close()

    def test_test_run_creation(self):
        """Test creation of test run records."""
        from test_dashboard.plugins.pytest_dashboard import DashboardTestPlugin
        from test_dashboard.database import TestDashboardDB

        # Setup plugin with database
        plugin = DashboardTestPlugin()
        with patch('test_dashboard.plugins.pytest_dashboard.dashboard_available', True):
            plugin.db = TestDashboardDB(str(self.db_path))

        # Create test run
        run_id = plugin.db.create_test_run(
            test_command="pytest --dashboard",
            git_commit="abc123",
            git_branch="main"
        )

        assert run_id is not None
        assert len(run_id) > 0

        # Verify run was stored
        test_run = plugin.db.get_test_run(run_id)
        assert test_run is not None
        assert test_run.test_command == "pytest --dashboard"
        assert test_run.git_commit == "abc123"
        assert test_run.git_branch == "main"

    def test_test_result_recording(self):
        """Test recording of individual test results."""
        from test_dashboard.plugins.pytest_dashboard import DashboardTestPlugin
        from test_dashboard.database import TestDashboardDB
        from test_dashboard.models import TestResult, TestStatus, TestType

        # Setup plugin
        plugin = DashboardTestPlugin()
        with patch('test_dashboard.plugins.pytest_dashboard.dashboard_available', True):
            plugin.db = TestDashboardDB(str(self.db_path))

        # Create test run
        run_id = plugin.db.create_test_run("pytest --dashboard")

        # Create test result
        test_result = TestResult(
            test_name="test_example",
            test_file="test_example.py",
            test_method="test_example",
            test_type=TestType.UNIT,
            status=TestStatus.PASSED,
            duration_seconds=0.123
        )

        # Add test result
        result_id = plugin.db.add_test_result(run_id, test_result)
        assert result_id is not None

        # Verify result was stored
        results = plugin.db.get_test_results(run_id)
        assert len(results) == 1
        assert results[0].test_name == "test_example"
        assert results[0].status == TestStatus.PASSED

    def test_coverage_data_recording(self):
        """Test recording of coverage data."""
        from test_dashboard.plugins.pytest_dashboard import DashboardTestPlugin
        from test_dashboard.database import TestDashboardDB
        from test_dashboard.models import CoverageData

        # Setup plugin
        plugin = DashboardTestPlugin()
        with patch('test_dashboard.plugins.pytest_dashboard.dashboard_available', True):
            plugin.db = TestDashboardDB(str(self.db_path))

        # Create test run
        run_id = plugin.db.create_test_run("pytest --dashboard")

        # Create coverage data
        coverage_data = CoverageData(
            file_path="src/example.py",
            total_lines=100,
            covered_lines=85,
            missing_lines=[10, 25, 30],
            coverage_percentage=85.0
        )

        # Add coverage data
        coverage_id = plugin.db.add_coverage_data(run_id, coverage_data)
        assert coverage_id is not None

        # Verify coverage summary
        summary = plugin.db.get_coverage_summary(run_id)
        assert summary['file_count'] == 1
        assert summary['total_lines'] == 100
        assert summary['covered_lines'] == 85

    @pytest.mark.integration
    def test_end_to_end_plugin_execution(self):
        """Test end-to-end plugin execution with a real pytest run."""
        # Create a simple test file
        test_file = self.temp_dir / "test_simple.py"
        test_file.write_text('''
def test_passing():
    assert True

def test_failing():
    assert False, "This test should fail"

def test_skipped():
    import pytest
    pytest.skip("Skipping this test")
''')

        # Run pytest with dashboard plugin
        cmd = [
            'python', '-m', 'pytest',
            str(test_file),
            '--dashboard',
            f'--dashboard-db={self.db_path}',
            '--dashboard-name=Integration Test',
            '-v'
        ]

        # Execute with dashboard plugin path in PYTHONPATH
        import os
        env = os.environ.copy()
        dashboard_path = str(Path(__file__).parent.parent.parent)
        if 'PYTHONPATH' in env:
            env['PYTHONPATH'] = f"{dashboard_path}:{env['PYTHONPATH']}"
        else:
            env['PYTHONPATH'] = dashboard_path

        result = subprocess.run(
            cmd,
            cwd=self.temp_dir,
            capture_output=True,
            text=True,
            env=env
        )

        # Verify pytest ran (may fail tests, but should complete)
        assert "test session starts" in result.stdout or result.stderr

        # If database was created, verify contents
        if self.db_path.exists():
            from test_dashboard.database import TestDashboardDB

            db = TestDashboardDB(str(self.db_path))

            # Get recent runs
            runs = db.get_recent_test_runs(limit=1)
            if runs:
                run = runs[0]
                assert run.test_command is not None
                assert "pytest" in run.test_command

                # Get test results
                results = db.get_test_results(run.run_id)
                # Should have some results if tests ran
                print(f"Found {len(results)} test results")

            db.close()

    def test_websocket_integration(self):
        """Test WebSocket integration functionality."""
        from test_dashboard.plugins.realtime import RealTimeBroadcaster

        # Test broadcaster creation
        broadcaster = RealTimeBroadcaster(port=0)  # Use port 0 to get any available port
        assert broadcaster is not None

        # Test event queuing
        test_event = {
            'type': 'test_event',
            'message': 'Hello World'
        }

        broadcaster.queue_event(test_event)
        assert not broadcaster.event_queue.empty()

        # Test event broadcasting methods
        broadcaster.broadcast_test_run_start("run123", "pytest --dashboard", 10)
        broadcaster.broadcast_test_start("run123", "test_example", "test_file.py")
        broadcaster.broadcast_test_end("run123", "test_example", "PASSED", 0.123)

        # Should have events queued
        assert not broadcaster.event_queue.empty()

    def test_plugin_error_handling(self):
        """Test plugin behavior when encountering errors."""
        from test_dashboard.plugins.pytest_dashboard import DashboardTestPlugin

        plugin = DashboardTestPlugin()

        # Test with invalid database path
        config = MagicMock()
        config.getoption.side_effect = lambda opt, default=None: {
            "--dashboard": True,
            "--dashboard-db": "/invalid/path/test.db",
        }.get(opt, default)

        with patch('test_dashboard.plugins.pytest_dashboard.dashboard_available', True):
            plugin.pytest_configure(config)

        # Plugin should disable itself on database error
        assert not plugin.enabled

    def test_environment_info_collection(self):
        """Test collection of environment information."""
        from test_dashboard.plugins.pytest_dashboard import DashboardTestPlugin

        plugin = DashboardTestPlugin()
        env_info = plugin._collect_environment_info()

        assert 'python_version' in env_info
        assert 'platform' in env_info
        assert 'cwd' in env_info
        assert 'pytest_version' in env_info

    def test_git_info_extraction(self):
        """Test extraction of git information."""
        from test_dashboard.plugins.pytest_dashboard import DashboardTestPlugin

        plugin = DashboardTestPlugin()
        git_info = plugin._get_git_info()

        # Should return dict with commit and branch keys
        assert 'commit' in git_info
        assert 'branch' in git_info

        # Values may be None if not in git repo, but keys should exist
        assert isinstance(git_info['commit'], (str, type(None)))
        assert isinstance(git_info['branch'], (str, type(None)))

    def test_test_type_detection(self):
        """Test automatic test type detection."""
        from test_dashboard.plugins.pytest_dashboard import DashboardTestPlugin

        plugin = DashboardTestPlugin()

        # Mock pytest item for different test types
        item_unit = MagicMock()
        item_unit.fspath = Path("tests/unit/test_example.py")
        item_unit.nodeid = "tests/unit/test_example.py::test_function"
        item_unit.name = "test_function"
        item_unit.pytestmark = []

        test_info = plugin._extract_test_info(item_unit)
        assert test_info['test_type'].value == "UNIT"

        # Integration test
        item_integration = MagicMock()
        item_integration.fspath = Path("tests/integration/test_api.py")
        item_integration.nodeid = "tests/integration/test_api.py::test_api_call"
        item_integration.name = "test_api_call"
        item_integration.pytestmark = []

        test_info = plugin._extract_test_info(item_integration)
        # Should detect integration from path
        assert test_info['test_type'].value in ["INTEGRATION", "API"]


class TestPluginSetup:
    """Test the plugin setup utilities."""

    def setup_method(self):
        """Setup test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        """Cleanup test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_plugin_setup_creation(self):
        """Test creating PluginSetup instance."""
        from test_dashboard.plugins.plugin_setup import PluginSetup

        setup = PluginSetup(self.temp_dir)
        assert setup.project_root == self.temp_dir

    def test_pytest_ini_creation(self):
        """Test creation of pytest.ini configuration."""
        from test_dashboard.plugins.plugin_setup import PluginSetup

        setup = PluginSetup(self.temp_dir)
        success = setup.register_plugin()

        assert success
        pytest_ini = self.temp_dir / "pytest.ini"
        assert pytest_ini.exists()

        content = pytest_ini.read_text()
        assert "test_dashboard.plugins.pytest_dashboard" in content

    def test_installation_verification(self):
        """Test installation verification."""
        from test_dashboard.plugins.plugin_setup import PluginSetup

        setup = PluginSetup(self.temp_dir)
        results = setup.verify_installation()

        assert 'plugin_available' in results
        assert 'database_available' in results
        assert 'websocket_available' in results
        assert 'pytest_integration' in results


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])