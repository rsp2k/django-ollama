"""
Pytest plugin for django-ollama test dashboard integration.

This plugin automatically captures pytest execution events and feeds them
to the test dashboard database for real-time monitoring and historical analysis.

Usage:
    pytest --dashboard                    # Enable dashboard integration
    pytest --dashboard-db=custom.db       # Use custom database file
    pytest --dashboard-name="Custom Run"  # Set custom run name
"""

import os
import sys
import time
import traceback
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List
import pytest
import logging

# Add test_dashboard to Python path for imports
dashboard_dir = Path(__file__).parent.parent
if str(dashboard_dir) not in sys.path:
    sys.path.insert(0, str(dashboard_dir))

try:
    from database import TestDashboardDB, DatabaseError
    from models import TestResult, TestStatus, TestType, CoverageData
    from plugins.realtime import DashboardWebSocketMixin, setup_global_broadcaster, cleanup_global_broadcaster
    dashboard_available = True
    websocket_available = True
except ImportError as e:
    logging.warning(f"Dashboard integration not available: {e}")
    dashboard_available = False
    websocket_available = False

    # Create stub classes if imports fail
    class DashboardWebSocketMixin:
        def setup_realtime_broadcasting(self, *args, **kwargs): pass
        def cleanup_realtime_broadcasting(self): pass
        def _broadcast_if_enabled(self, *args, **kwargs): pass


class DashboardTestPlugin(DashboardWebSocketMixin):
    """
    Main pytest plugin class for dashboard integration.

    Captures test execution events and stores them in the dashboard database
    for real-time monitoring and historical analysis.
    """

    def __init__(self):
        super().__init__()
        self.db: Optional[TestDashboardDB] = None
        self.run_id: Optional[str] = None
        self.test_results: Dict[str, Dict] = {}
        self.start_time = time.time()
        self.enabled = False
        self.db_path = "test_dashboard.db"
        self.run_name = ""
        self.websocket_port = 8765

        # Test execution tracking
        self.current_test_start = None
        self.session_stats = {
            'total': 0,
            'passed': 0,
            'failed': 0,
            'skipped': 0,
            'error': 0
        }

    def pytest_addoption(self, parser):
        """Add command-line options for dashboard integration."""
        group = parser.getgroup("dashboard", "Test Dashboard Integration")

        group.addoption(
            "--dashboard",
            action="store_true",
            default=False,
            help="Enable test dashboard integration for real-time monitoring"
        )

        group.addoption(
            "--dashboard-db",
            type=str,
            default="test_dashboard.db",
            help="Database file path for dashboard data (default: test_dashboard.db)"
        )

        group.addoption(
            "--dashboard-name",
            type=str,
            default="",
            help="Custom name for this test run (default: auto-generated)"
        )

        group.addoption(
            "--dashboard-websocket",
            action="store_true",
            default=False,
            help="Enable real-time WebSocket broadcasting for live dashboard updates"
        )

        group.addoption(
            "--dashboard-websocket-port",
            type=int,
            default=8765,
            help="WebSocket server port for real-time updates (default: 8765)"
        )

    def pytest_configure(self, config):
        """Configure the plugin based on command-line options."""
        self.enabled = config.getoption("--dashboard", default=False)

        if not self.enabled:
            return

        if not dashboard_available:
            logging.error("Dashboard integration requested but dependencies not available")
            self.enabled = False
            return

        self.db_path = config.getoption("--dashboard-db", default="test_dashboard.db")
        self.run_name = config.getoption("--dashboard-name", default="")
        websocket_enabled = config.getoption("--dashboard-websocket", default=False)
        self.websocket_port = config.getoption("--dashboard-websocket-port", default=8765)

        try:
            self.db = TestDashboardDB(self.db_path)
            logging.info(f"Dashboard integration enabled with database: {self.db_path}")

            # Setup WebSocket broadcasting if requested
            if websocket_enabled and websocket_available:
                self.setup_realtime_broadcasting(self.websocket_port)

        except Exception as e:
            logging.error(f"Failed to initialize dashboard database: {e}")
            self.enabled = False

    def pytest_sessionstart(self, session):
        """Called at the start of the test session."""
        if not self.enabled or not self.db:
            return

        try:
            # Gather environment information
            env_info = self._collect_environment_info()

            # Get git information
            git_info = self._get_git_info()

            # Create test run record
            test_command = " ".join(sys.argv)
            if not self.run_name:
                self.run_name = f"Test Run {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

            self.run_id = self.db.create_test_run(
                test_command=test_command,
                git_commit=git_info.get('commit'),
                git_branch=git_info.get('branch'),
                environment_info=env_info
            )

            logging.info(f"Started test dashboard run: {self.run_id}")

            # Broadcast test run start
            self._broadcast_if_enabled(
                'broadcast_test_run_start',
                self.run_id, test_command
            )

        except Exception as e:
            logging.error(f"Failed to start dashboard session: {e}")
            self.enabled = False

    def pytest_runtest_setup(self, item):
        """Called before each test setup."""
        if not self.enabled or not self.db:
            return

        self.current_test_start = time.time()
        test_info = self._extract_test_info(item)

        # Store initial test info
        self.test_results[item.nodeid] = {
            'start_time': datetime.now(timezone.utc),
            'test_info': test_info,
            'setup_start': time.time()
        }

        # Broadcast test start
        self._broadcast_if_enabled(
            'broadcast_test_start',
            self.run_id, test_info['test_name'], test_info['test_file']
        )

    def pytest_runtest_call(self, item):
        """Called when the test is actually executed."""
        if not self.enabled or not self.db:
            return

        if item.nodeid in self.test_results:
            self.test_results[item.nodeid]['setup_duration'] = time.time() - self.test_results[item.nodeid]['setup_start']
            self.test_results[item.nodeid]['call_start'] = time.time()

    def pytest_runtest_teardown(self, item):
        """Called during test teardown."""
        if not self.enabled or not self.db:
            return

        if item.nodeid in self.test_results:
            self.test_results[item.nodeid]['teardown_start'] = time.time()

    def pytest_runtest_logreport(self, report):
        """Called for each test report (setup, call, teardown)."""
        if not self.enabled or not self.db:
            return

        # We only care about the 'call' phase for final results
        if report.when != 'call':
            return

        try:
            self._record_test_result(report)
        except Exception as e:
            logging.error(f"Failed to record test result for {report.nodeid}: {e}")

    def pytest_sessionfinish(self, session, exitstatus):
        """Called at the end of the test session."""
        if not self.enabled or not self.db:
            return

        try:
            # Update test run with final statistics
            duration = time.time() - self.start_time

            # Determine final status
            final_status = TestStatus.PASSED
            if self.session_stats['failed'] > 0 or self.session_stats['error'] > 0:
                final_status = TestStatus.FAILED
            elif self.session_stats['total'] == 0:
                final_status = TestStatus.SKIPPED

            updates = {
                'finished_at': datetime.now(timezone.utc),
                'status': final_status,
                'duration_seconds': duration,
                'total_tests': self.session_stats['total'],
                'passed_tests': self.session_stats['passed'],
                'failed_tests': self.session_stats['failed'],
                'skipped_tests': self.session_stats['skipped'],
                'error_tests': self.session_stats['error']
            }

            self.db.update_test_run(self.run_id, **updates)

            # Process coverage data if available
            self._process_coverage_data()

            logging.info(f"Completed test dashboard run: {self.run_id}")
            logging.info(f"  Tests: {self.session_stats['total']}, "
                        f"Passed: {self.session_stats['passed']}, "
                        f"Failed: {self.session_stats['failed']}, "
                        f"Duration: {duration:.2f}s")

            # Broadcast test run end
            self._broadcast_if_enabled(
                'broadcast_test_run_end',
                self.run_id, duration, self.session_stats
            )

        except Exception as e:
            logging.error(f"Failed to finalize dashboard session: {e}")
        finally:
            if self.db:
                self.db.close()
            self.cleanup_realtime_broadcasting()

    def _extract_test_info(self, item) -> Dict[str, Any]:
        """Extract comprehensive test information from pytest item."""
        # Get file path relative to project root
        test_file = str(Path(item.fspath).relative_to(Path.cwd()))

        # Extract class and method names
        test_class = None
        test_method = item.name

        if '::' in item.nodeid:
            parts = item.nodeid.split('::')
            if len(parts) >= 2 and not parts[1].startswith('test_'):
                test_class = parts[1]
                test_method = parts[2] if len(parts) > 2 else parts[1]
            else:
                test_method = parts[-1]

        # Determine test type from markers or naming
        test_type = TestType.UNIT  # default

        if hasattr(item, 'pytestmark'):
            for marker in item.pytestmark:
                if marker.name == 'integration':
                    test_type = TestType.INTEGRATION
                elif marker.name == 'e2e':
                    test_type = TestType.E2E
                elif marker.name in ['api', 'rest', 'http']:
                    test_type = TestType.API

        # Check for type hints in test name/path
        if 'integration' in test_file.lower() or 'integration' in test_method.lower():
            test_type = TestType.INTEGRATION
        elif 'api' in test_file.lower() or 'api' in test_method.lower():
            test_type = TestType.API
        elif 'e2e' in test_file.lower() or 'end_to_end' in test_file.lower():
            test_type = TestType.E2E

        return {
            'test_name': item.nodeid,
            'test_file': test_file,
            'test_class': test_class,
            'test_method': test_method,
            'test_type': test_type
        }

    def _record_test_result(self, report):
        """Record a test result in the database."""
        if report.nodeid not in self.test_results:
            return

        test_data = self.test_results[report.nodeid]
        test_info = test_data['test_info']

        # Determine test status
        if report.passed:
            status = TestStatus.PASSED
            self.session_stats['passed'] += 1
        elif report.failed:
            status = TestStatus.FAILED
            self.session_stats['failed'] += 1
        elif report.skipped:
            status = TestStatus.SKIPPED
            self.session_stats['skipped'] += 1
        else:
            status = TestStatus.ERROR
            self.session_stats['error'] += 1

        self.session_stats['total'] += 1

        # Calculate durations
        call_duration = 0
        setup_duration = test_data.get('setup_duration', 0)
        teardown_duration = 0

        if 'call_start' in test_data:
            call_duration = report.duration
        if 'teardown_start' in test_data:
            teardown_duration = time.time() - test_data['teardown_start']

        total_duration = setup_duration + call_duration + teardown_duration

        # Extract error information
        error_message = None
        error_traceback = None

        if report.failed and hasattr(report, 'longrepr'):
            if hasattr(report.longrepr, 'reprcrash'):
                error_message = str(report.longrepr.reprcrash.message)
            error_traceback = str(report.longrepr)

        # Count assertions (rough estimate from traceback)
        assertions_count = 0
        if error_traceback:
            assertions_count = error_traceback.count('assert ') + error_traceback.count('AssertionError')

        # Create test result object
        test_result = TestResult(
            test_name=test_info['test_name'],
            test_file=test_info['test_file'],
            test_class=test_info['test_class'],
            test_method=test_info['test_method'],
            test_type=test_info['test_type'],
            status=status,
            duration_seconds=total_duration,
            error_message=error_message,
            error_traceback=error_traceback,
            setup_duration=setup_duration,
            teardown_duration=teardown_duration,
            assertions_count=max(1, assertions_count),  # At least 1 assertion per test
            started_at=test_data['start_time'],
            finished_at=datetime.now(timezone.utc)
        )

        # Store in database
        self.db.add_test_result(self.run_id, test_result)

        # Broadcast test end
        self._broadcast_if_enabled(
            'broadcast_test_end',
            self.run_id, test_result.test_name, status.value,
            total_duration, error_message
        )

        # Broadcast progress update
        self._broadcast_if_enabled(
            'broadcast_progress_update',
            self.run_id, self.session_stats['total'],
            sum(self.session_stats.values()), test_result.test_name
        )

    def _collect_environment_info(self) -> Dict[str, Any]:
        """Collect environment information for the test run."""
        try:
            return {
                'python_version': sys.version,
                'platform': sys.platform,
                'cwd': str(Path.cwd()),
                'pytest_version': pytest.__version__,
                'environment_variables': {
                    key: value for key, value in os.environ.items()
                    if key.startswith(('DJANGO_', 'PYTEST_', 'TEST_', 'CI_'))
                }
            }
        except Exception as e:
            logging.warning(f"Failed to collect environment info: {e}")
            return {}

    def _get_git_info(self) -> Dict[str, Optional[str]]:
        """Get current git commit and branch information."""
        git_info = {'commit': None, 'branch': None}

        try:
            # Get current commit
            result = subprocess.run(
                ['git', 'rev-parse', 'HEAD'],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                git_info['commit'] = result.stdout.strip()

            # Get current branch
            result = subprocess.run(
                ['git', 'branch', '--show-current'],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                git_info['branch'] = result.stdout.strip()

        except (subprocess.SubprocessError, FileNotFoundError):
            # Git not available or not in a git repository
            pass

        return git_info

    def _process_coverage_data(self):
        """Process coverage data from pytest-cov if available."""
        try:
            # Try to find coverage data files
            coverage_files = []
            for pattern in ['.coverage', 'htmlcov/index.html', 'coverage.xml']:
                if Path(pattern).exists():
                    coverage_files.append(pattern)

            if not coverage_files:
                return

            # Try to import coverage module to extract data
            try:
                import coverage

                cov = coverage.Coverage()
                cov.load()

                # Get measured files
                measured_files = cov.get_data().measured_files()

                for file_path in measured_files:
                    try:
                        # Get coverage analysis for this file
                        analysis = cov.analysis2(file_path)
                        filename = analysis[0]
                        executed_lines = set(analysis[1])
                        missing_lines = list(analysis[3])
                        excluded_lines = list(analysis[4]) if len(analysis) > 4 else []

                        # Calculate coverage stats
                        total_lines = len(executed_lines) + len(missing_lines)
                        covered_lines = len(executed_lines)
                        coverage_percentage = (covered_lines / total_lines * 100) if total_lines > 0 else 100.0

                        # Create coverage data record
                        coverage_data = CoverageData(
                            file_path=str(Path(filename).relative_to(Path.cwd())),
                            total_lines=total_lines,
                            covered_lines=covered_lines,
                            missing_lines=missing_lines,
                            excluded_lines=excluded_lines,
                            coverage_percentage=coverage_percentage
                        )

                        self.db.add_coverage_data(self.run_id, coverage_data)

                        # Broadcast coverage update
                        self._broadcast_if_enabled(
                            'broadcast_coverage_update',
                            self.run_id, coverage_data.file_path, coverage_data.coverage_percentage
                        )

                    except Exception as e:
                        logging.warning(f"Failed to process coverage for {file_path}: {e}")

            except ImportError:
                logging.info("Coverage module not available for detailed analysis")

        except Exception as e:
            logging.warning(f"Failed to process coverage data: {e}")


# Plugin instance
dashboard_plugin = DashboardTestPlugin()


def pytest_addoption(parser):
    """Register command-line options."""
    dashboard_plugin.pytest_addoption(parser)


def pytest_configure(config):
    """Configure the plugin."""
    dashboard_plugin.pytest_configure(config)


def pytest_sessionstart(session):
    """Session start hook."""
    dashboard_plugin.pytest_sessionstart(session)


def pytest_runtest_setup(item):
    """Test setup hook."""
    dashboard_plugin.pytest_runtest_setup(item)


def pytest_runtest_call(item):
    """Test call hook."""
    dashboard_plugin.pytest_runtest_call(item)


def pytest_runtest_teardown(item):
    """Test teardown hook."""
    dashboard_plugin.pytest_runtest_teardown(item)


def pytest_runtest_logreport(report):
    """Test report hook."""
    dashboard_plugin.pytest_runtest_logreport(report)


def pytest_sessionfinish(session, exitstatus):
    """Session finish hook."""
    dashboard_plugin.pytest_sessionfinish(session, exitstatus)