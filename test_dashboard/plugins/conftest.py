"""
Pytest configuration for django-ollama test dashboard integration.

This conftest.py file automatically registers the dashboard plugin and provides
fixtures for test dashboard integration.
"""

import pytest
import logging
from pathlib import Path

# Configure logging for plugin
logging.basicConfig(
    level=logging.INFO,
    format='[DASHBOARD] %(levelname)s: %(message)s'
)

pytest_plugins = ["test_dashboard.plugins.pytest_dashboard"]


@pytest.fixture(scope="session")
def dashboard_plugin():
    """
    Provide access to the dashboard plugin instance.

    This fixture allows tests to interact with the dashboard plugin
    for advanced configuration or monitoring.
    """
    from test_dashboard.plugins.pytest_dashboard import dashboard_plugin
    return dashboard_plugin


@pytest.fixture(scope="session")
def dashboard_db():
    """
    Provide access to the dashboard database instance.

    Only available when dashboard integration is enabled.
    """
    from test_dashboard.plugins.pytest_dashboard import dashboard_plugin
    if dashboard_plugin.enabled and dashboard_plugin.db:
        return dashboard_plugin.db
    return None


@pytest.fixture(scope="session")
def test_run_id():
    """
    Provide the current test run ID.

    Useful for tests that need to reference their own run ID.
    """
    from test_dashboard.plugins.pytest_dashboard import dashboard_plugin
    return dashboard_plugin.run_id


@pytest.fixture
def dashboard_logger():
    """
    Provide a dashboard-specific logger for tests.
    """
    return logging.getLogger("test_dashboard")


def pytest_configure(config):
    """
    Additional configuration for dashboard integration.
    """
    # Add custom markers for test dashboard
    config.addinivalue_line(
        "markers",
        "dashboard_track: Mark test for special dashboard tracking"
    )

    config.addinivalue_line(
        "markers",
        "dashboard_ignore: Mark test to ignore in dashboard (still runs)"
    )


def pytest_collection_modifyitems(config, items):
    """
    Modify collected test items for dashboard integration.

    This hook can be used to add special handling for dashboard-marked tests.
    """
    dashboard_enabled = config.getoption("--dashboard", default=False)

    if not dashboard_enabled:
        return

    # Add logging for dashboard-tracked tests
    dashboard_tracked = []
    dashboard_ignored = []

    for item in items:
        if item.get_closest_marker("dashboard_track"):
            dashboard_tracked.append(item.nodeid)
        elif item.get_closest_marker("dashboard_ignore"):
            dashboard_ignored.append(item.nodeid)

    if dashboard_tracked:
        logging.info(f"Dashboard tracking enabled for {len(dashboard_tracked)} tests")

    if dashboard_ignored:
        logging.info(f"Dashboard ignoring {len(dashboard_ignored)} tests")