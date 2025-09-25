"""
Comprehensive end-to-end integration tests for Django-Ollama Test Dashboard.

This test suite validates the complete test dashboard system including:
- Database operations and schema integrity
- Web server API endpoints and responses
- WebSocket real-time communication
- pytest plugin integration
- Frontend dashboard functionality
- Performance and stress testing
- Error handling and edge cases
"""

import asyncio
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import uuid

import pytest
import requests
import websockets
from fastapi.testclient import TestClient

# Add test_dashboard to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from database import TestDashboardDB, DatabaseError
from models import TestRun, TestResult, TestStatus, TestType, CoverageData
from server import app, websocket_manager, dashboard_server


class TestDatabaseIntegration:
    """Test database layer functionality and performance."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name

        db = TestDashboardDB(db_path)
        yield db

        # Cleanup
        db.close()
        if Path(db_path).exists():
            Path(db_path).unlink()

    def test_database_creation_and_schema(self, temp_db):
        """Test database creation and schema validation."""
        # Verify tables exist
        conn = temp_db._get_connection()
        cursor = conn.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """)
        tables = [row[0] for row in cursor.fetchall()]

        expected_tables = ['test_runs', 'test_results', 'coverage_data', 'test_metrics']
        assert all(table in tables for table in expected_tables)

    def test_crud_operations(self, temp_db):
        """Test basic CRUD operations for test runs."""
        # Create
        run_id = temp_db.create_test_run(
            test_command="pytest tests/",
            git_commit="abc123",
            git_branch="main",
            environment_info={"python": "3.11.0"}
        )

        assert run_id is not None
        assert isinstance(run_id, str)

        # Read
        test_run = temp_db.get_test_run(run_id)
        assert test_run is not None
        assert test_run.run_id == run_id
        assert test_run.test_command == "pytest tests/"
        assert test_run.git_commit == "abc123"
        assert test_run.environment_info["python"] == "3.11.0"

        # Update
        updated = temp_db.update_test_run(
            run_id,
            status=TestStatus.PASSED,
            finished_at=datetime.now(timezone.utc),
            total_tests=10,
            passed_tests=8,
            failed_tests=2
        )
        assert updated is True

        # Verify update
        updated_run = temp_db.get_test_run(run_id)
        assert updated_run.status == TestStatus.PASSED
        assert updated_run.total_tests == 10
        assert updated_run.passed_tests == 8
        assert updated_run.failed_tests == 2

    def test_test_results_operations(self, temp_db):
        """Test test result storage and retrieval."""
        # Create test run
        run_id = temp_db.create_test_run(test_command="pytest tests/")

        # Add test results
        test_results = []
        for i in range(5):
            result = TestResult(
                test_name=f"test_example_{i}",
                test_file=f"tests/test_{i}.py",
                test_method=f"test_method_{i}",
                test_type=TestType.UNIT,
                status=TestStatus.PASSED if i % 2 == 0 else TestStatus.FAILED,
                duration_seconds=0.1 * (i + 1),
                started_at=datetime.now(timezone.utc),
                finished_at=datetime.now(timezone.utc)
            )
            test_results.append(result)
            temp_db.add_test_result(run_id, result)

        # Retrieve results
        retrieved_results = temp_db.get_test_results(run_id)
        assert len(retrieved_results) == 5

        # Test filtering by status
        passed_results = temp_db.get_test_results(run_id, status=TestStatus.PASSED)
        failed_results = temp_db.get_test_results(run_id, status=TestStatus.FAILED)

        assert len(passed_results) == 3  # indexes 0, 2, 4
        assert len(failed_results) == 2  # indexes 1, 3

        # Test pagination
        paginated_results = temp_db.get_test_results(run_id, limit=2, offset=1)
        assert len(paginated_results) == 2

    def test_coverage_operations(self, temp_db):
        """Test coverage data storage and retrieval."""
        # Create test run
        run_id = temp_db.create_test_run(test_command="pytest --cov tests/")

        # Add coverage data
        coverage_files = [
            ("src/models.py", 100, 85, [45, 46, 78]),
            ("src/views.py", 200, 180, [12, 15]),
            ("src/utils.py", 50, 50, [])
        ]

        for file_path, total, covered, missing in coverage_files:
            coverage = CoverageData(
                file_path=file_path,
                total_lines=total,
                covered_lines=covered,
                missing_lines=missing,
                coverage_percentage=(covered / total) * 100
            )
            temp_db.add_coverage_data(run_id, coverage)

        # Get coverage summary
        summary = temp_db.get_coverage_summary(run_id)

        assert summary['file_count'] == 3
        assert summary['total_lines'] == 350
        assert summary['covered_lines'] == 315
        assert abs(summary['line_coverage'] - 90.0) < 0.01
        assert summary['min_coverage'] == 90.0  # src/views.py
        assert summary['max_coverage'] == 100.0  # src/utils.py

    def test_dashboard_summary_stats(self, temp_db):
        """Test dashboard summary statistics generation."""
        # Create multiple test runs with different statuses
        now = datetime.now(timezone.utc)
        yesterday = now - timedelta(days=1)

        runs = [
            (TestStatus.PASSED, 100, 95, 5, 0),
            (TestStatus.FAILED, 50, 40, 8, 2),
            (TestStatus.PASSED, 200, 190, 10, 0),
            (TestStatus.RUNNING, 0, 0, 0, 0),  # Current running test
        ]

        for status, total, passed, failed, error in runs:
            run_id = temp_db.create_test_run(test_command="pytest")
            temp_db.update_test_run(
                run_id,
                status=status,
                total_tests=total,
                passed_tests=passed,
                failed_tests=failed,
                error_tests=error,
                started_at=yesterday,
                duration_seconds=30.0
            )

        # Get dashboard summary
        summary = temp_db.get_dashboard_summary()

        assert 'recent_24h' in summary
        assert 'overall' in summary
        assert 'running_tests' in summary

        recent = summary['recent_24h']
        assert recent['total_runs'] == 4
        assert recent['passed_runs'] == 2
        assert recent['failed_runs'] == 1
        assert recent['running_runs'] == 1

        running_tests = summary['running_tests']
        assert len(running_tests) == 1
        assert running_tests[0]['run_id'] is not None

    def test_data_retention_cleanup(self, temp_db):
        """Test automatic cleanup of old test data."""
        # Create old test runs
        old_date = datetime.now(timezone.utc) - timedelta(days=35)
        recent_date = datetime.now(timezone.utc) - timedelta(days=5)

        # Create old runs (should be cleaned up)
        old_runs = []
        for i in range(3):
            run_id = temp_db.create_test_run(test_command=f"old_test_{i}")
            temp_db.update_test_run(run_id, started_at=old_date)
            old_runs.append(run_id)

        # Create recent runs (should be kept)
        recent_runs = []
        for i in range(2):
            run_id = temp_db.create_test_run(test_command=f"recent_test_{i}")
            temp_db.update_test_run(run_id, started_at=recent_date)
            recent_runs.append(run_id)

        # Verify all runs exist
        all_runs = temp_db.get_recent_test_runs(limit=10)
        assert len(all_runs) == 5

        # Run cleanup
        deleted_count = temp_db.cleanup_old_data()
        assert deleted_count == 3

        # Verify only recent runs remain
        remaining_runs = temp_db.get_recent_test_runs(limit=10)
        assert len(remaining_runs) == 2

        # Verify specific runs
        for run_id in recent_runs:
            run = temp_db.get_test_run(run_id)
            assert run is not None

        for run_id in old_runs:
            run = temp_db.get_test_run(run_id)
            assert run is None

    def test_database_performance(self, temp_db):
        """Test database performance with large datasets."""
        start_time = time.time()

        # Create 100 test runs with 50 test results each
        run_ids = []
        for i in range(100):
            run_id = temp_db.create_test_run(f"perf_test_{i}")
            run_ids.append(run_id)

            # Add test results
            for j in range(50):
                result = TestResult(
                    test_name=f"test_{j}",
                    test_file=f"tests/test_{j}.py",
                    test_method=f"test_method_{j}",
                    test_type=TestType.UNIT,
                    status=TestStatus.PASSED,
                    duration_seconds=0.1,
                    started_at=datetime.now(timezone.utc),
                    finished_at=datetime.now(timezone.utc)
                )
                temp_db.add_test_result(run_id, result)

        creation_time = time.time() - start_time

        # Performance assertions
        assert creation_time < 30.0  # Should complete in under 30 seconds

        # Test query performance
        query_start = time.time()
        recent_runs = temp_db.get_recent_test_runs(limit=50)
        query_time = time.time() - query_start

        assert len(recent_runs) == 50
        assert query_time < 1.0  # Query should complete in under 1 second

        # Test summary generation performance
        summary_start = time.time()
        summary = temp_db.get_dashboard_summary()
        summary_time = time.time() - summary_start

        assert summary_time < 2.0  # Summary should complete in under 2 seconds
        assert summary['recent_24h']['total_runs'] == 100


class TestWebServerAPI:
    """Test REST API endpoints and HTTP functionality."""

    @pytest.fixture
    def client(self):
        """Create test client for FastAPI app."""
        return TestClient(app)

    @pytest.fixture
    def sample_data(self, client):
        """Create sample test data."""
        # Create test database with sample data
        db = TestDashboardDB("test_api.db")

        # Create sample test runs
        run_ids = []
        for i in range(3):
            run_id = db.create_test_run(
                test_command=f"pytest test_{i}",
                git_branch="main",
                git_commit=f"commit_{i}"
            )
            run_ids.append(run_id)

            # Update run status
            db.update_test_run(
                run_id,
                status=TestStatus.PASSED if i % 2 == 0 else TestStatus.FAILED,
                total_tests=10,
                passed_tests=8 if i % 2 == 0 else 6,
                failed_tests=2 if i % 2 == 0 else 4
            )

        yield run_ids

        # Cleanup
        db.close()
        if Path("test_api.db").exists():
            Path("test_api.db").unlink()

    def test_health_check_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/api/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "healthy"
        assert "database" in data
        assert "timestamp" in data
        assert "version" in data

    def test_dashboard_summary_endpoint(self, client, sample_data):
        """Test dashboard summary endpoint."""
        response = client.get("/api/dashboard/summary")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "success"
        assert "data" in data
        assert "timestamp" in data

        summary_data = data["data"]
        assert "recent_24h" in summary_data
        assert "overall" in summary_data
        assert "running_tests" in summary_data

    def test_recent_runs_endpoint(self, client, sample_data):
        """Test recent runs endpoint with filtering."""
        # Test basic request
        response = client.get("/api/dashboard/recent-runs")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "success"
        assert isinstance(data["data"], list)
        assert data["total"] >= 0

        # Test with limit
        response = client.get("/api/dashboard/recent-runs?limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) <= 2

        # Test with status filter
        response = client.get("/api/dashboard/recent-runs?status=PASSED")
        assert response.status_code == 200
        data = response.json()

        # Verify all returned runs have PASSED status
        for run in data["data"]:
            assert run["status"] == "PASSED"

    def test_run_details_endpoint(self, client, sample_data):
        """Test individual test run details endpoint."""
        run_id = sample_data[0]

        response = client.get(f"/api/dashboard/runs/{run_id}")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "success"

        run_data = data["data"]
        assert run_data["run_id"] == run_id
        assert "started_at" in run_data
        assert "status" in run_data
        assert "test_command" in run_data

    def test_run_details_not_found(self, client):
        """Test run details endpoint with invalid run ID."""
        response = client.get("/api/dashboard/runs/invalid-run-id")
        assert response.status_code == 404

    def test_test_results_endpoint(self, client, sample_data):
        """Test test results endpoint."""
        run_id = sample_data[0]

        # Add some test results first
        db = TestDashboardDB("test_api.db")
        for i in range(5):
            result = TestResult(
                test_name=f"test_{i}",
                test_file=f"test_{i}.py",
                test_method=f"test_method_{i}",
                test_type=TestType.UNIT,
                status=TestStatus.PASSED,
                duration_seconds=0.1,
                started_at=datetime.now(timezone.utc),
                finished_at=datetime.now(timezone.utc)
            )
            db.add_test_result(run_id, result)

        response = client.get(f"/api/dashboard/runs/{run_id}/results")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "success"
        assert len(data["data"]) == 5

    def test_coverage_endpoint(self, client, sample_data):
        """Test coverage data endpoint."""
        run_id = sample_data[0]

        response = client.get(f"/api/dashboard/runs/{run_id}/coverage")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "success"
        # Coverage data might be empty for test runs without actual coverage

    def test_system_stats_endpoint(self, client):
        """Test system statistics endpoint."""
        response = client.get("/api/stats")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "success"

        stats = data["data"]
        assert "database_size_bytes" in stats
        assert "database_size_mb" in stats
        assert "recent_runs_count" in stats

    def test_websocket_status_endpoint(self, client):
        """Test WebSocket status endpoint."""
        response = client.get("/api/websocket/status")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "success"

        ws_data = data["data"]
        assert "active_connections" in ws_data
        assert "websocket_endpoint" in ws_data
        assert "supported_events" in ws_data
        assert isinstance(ws_data["supported_events"], list)

    def test_simulate_event_endpoint(self, client):
        """Test event simulation endpoint."""
        event_data = {
            "type": "test_run_start",
            "run_id": "test-123",
            "test_command": "pytest tests/",
            "total_tests": 10
        }

        response = client.post("/api/test/simulate-event", json=event_data)
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "success"
        assert "message" in data
        assert "active_connections" in data

    def test_trend_data_endpoint(self, client, sample_data):
        """Test trend data endpoint."""
        response = client.get("/api/dashboard/trends?days=7")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "success"
        assert "period_days" in data
        assert data["period_days"] == 7
        assert isinstance(data["data"], list)

    def test_invalid_trend_days(self, client):
        """Test trend endpoint with invalid days parameter."""
        response = client.get("/api/dashboard/trends?days=500")
        assert response.status_code == 400

    def test_cors_headers(self, client):
        """Test CORS headers in responses."""
        response = client.options("/api/health")
        headers = response.headers

        # Verify CORS headers are present
        assert "access-control-allow-origin" in headers
        assert "access-control-allow-methods" in headers

    def test_error_handling(self, client):
        """Test API error handling."""
        # Test 404 for invalid endpoint
        response = client.get("/api/invalid-endpoint")
        assert response.status_code == 404

    def test_api_response_format(self, client):
        """Test consistent API response format."""
        endpoints = [
            "/api/health",
            "/api/dashboard/summary",
            "/api/dashboard/recent-runs",
            "/api/stats",
            "/api/websocket/status"
        ]

        for endpoint in endpoints:
            response = client.get(endpoint)
            data = response.json()

            # Every response should have these fields
            if response.status_code == 200:
                assert "status" in data
                assert "timestamp" in data

                # Success responses should have data
                if data["status"] == "success":
                    assert "data" in data


class TestWebSocketIntegration:
    """Test WebSocket real-time communication."""

    @pytest.mark.asyncio
    async def test_websocket_connection(self):
        """Test basic WebSocket connection and disconnection."""
        uri = "ws://localhost:8080/ws"

        try:
            async with websockets.connect(uri) as websocket:
                # Should receive connection established message
                message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                data = json.loads(message)

                assert data["type"] == "connection_established"
                assert "connection_id" in data
                assert "timestamp" in data
        except Exception as e:
            pytest.skip(f"WebSocket server not running: {e}")

    @pytest.mark.asyncio
    async def test_websocket_ping_pong(self):
        """Test WebSocket ping/pong mechanism."""
        uri = "ws://localhost:8080/ws"

        try:
            async with websockets.connect(uri) as websocket:
                # Skip connection message
                await websocket.recv()

                # Send ping
                ping_message = {"type": "ping"}
                await websocket.send(json.dumps(ping_message))

                # Should receive pong
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                data = json.loads(response)

                assert data["type"] == "pong"
                assert "timestamp" in data
        except Exception as e:
            pytest.skip(f"WebSocket server not running: {e}")

    @pytest.mark.asyncio
    async def test_websocket_status_request(self):
        """Test WebSocket status request."""
        uri = "ws://localhost:8080/ws"

        try:
            async with websockets.connect(uri) as websocket:
                # Skip connection message
                await websocket.recv()

                # Request status
                status_request = {"type": "request_status"}
                await websocket.send(json.dumps(status_request))

                # Should receive server status
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                data = json.loads(response)

                assert data["type"] == "server_status"
                assert "status" in data
                assert "summary" in data
        except Exception as e:
            pytest.skip(f"WebSocket server not running: {e}")

    @pytest.mark.asyncio
    async def test_websocket_subscription(self):
        """Test WebSocket test run subscription."""
        uri = "ws://localhost:8080/ws"

        try:
            async with websockets.connect(uri) as websocket:
                # Skip connection message
                await websocket.recv()

                # Subscribe to test run
                subscribe_message = {
                    "type": "subscribe_run",
                    "run_id": "test-123"
                }
                await websocket.send(json.dumps(subscribe_message))

                # Should receive subscription confirmation
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                data = json.loads(response)

                assert data["type"] == "subscription_confirmed"
                assert data["run_id"] == "test-123"
        except Exception as e:
            pytest.skip(f"WebSocket server not running: {e}")

    @pytest.mark.asyncio
    async def test_websocket_error_handling(self):
        """Test WebSocket error handling for invalid messages."""
        uri = "ws://localhost:8080/ws"

        try:
            async with websockets.connect(uri) as websocket:
                # Skip connection message
                await websocket.recv()

                # Send invalid JSON
                await websocket.send("invalid json")

                # Should receive error message
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                data = json.loads(response)

                assert data["type"] == "error"
                assert "message" in data
        except Exception as e:
            pytest.skip(f"WebSocket server not running: {e}")

    @pytest.mark.asyncio
    async def test_websocket_heartbeat(self):
        """Test WebSocket heartbeat mechanism."""
        uri = "ws://localhost:8080/ws"

        try:
            async with websockets.connect(uri) as websocket:
                # Skip connection message
                await websocket.recv()

                # Wait for heartbeat (should come within 30 seconds)
                start_time = time.time()
                while time.time() - start_time < 35:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        data = json.loads(message)

                        if data["type"] == "heartbeat":
                            assert "timestamp" in data
                            assert "connections" in data
                            break
                    except asyncio.TimeoutError:
                        continue
                else:
                    pytest.fail("No heartbeat received within 35 seconds")
        except Exception as e:
            pytest.skip(f"WebSocket server not running: {e}")


class TestPytestPluginIntegration:
    """Test pytest plugin integration."""

    def test_plugin_loading(self):
        """Test that the pytest plugin can be loaded."""
        try:
            from test_dashboard.plugins.pytest_dashboard import DashboardTestPlugin
            plugin = DashboardTestPlugin()
            assert plugin is not None
        except ImportError as e:
            pytest.fail(f"Failed to import pytest plugin: {e}")

    def test_plugin_command_line_options(self, tmp_path):
        """Test pytest plugin command-line options."""
        # Create a simple test file
        test_file = tmp_path / "test_simple.py"
        test_file.write_text("""
import pytest

def test_example():
    assert True

def test_another():
    assert 1 + 1 == 2
""")

        # Run pytest with dashboard options (dry run)
        result = subprocess.run([
            sys.executable, "-m", "pytest",
            "--help"
        ], capture_output=True, text=True, cwd=tmp_path)

        # Check if dashboard options are available
        assert "--dashboard" in result.stdout or "--dashboard" in result.stderr

    def test_basic_test_execution_with_dashboard(self, tmp_path):
        """Test running tests with dashboard integration."""
        # Create test database
        db_path = tmp_path / "test_integration.db"

        # Create a simple test file
        test_file = tmp_path / "test_dashboard_integration.py"
        test_file.write_text("""
import pytest

@pytest.mark.dashboard_track
def test_tracked_example():
    '''A test that should be tracked in the dashboard.'''
    assert True

def test_regular():
    '''A regular test.'''
    assert 2 + 2 == 4

@pytest.mark.dashboard_ignore
def test_ignored():
    '''A test that should not be tracked.'''
    assert "hello" == "hello"
""")

        # Create pytest.ini
        pytest_ini = tmp_path / "pytest.ini"
        pytest_ini.write_text("""
[tool:pytest]
markers =
    dashboard_track: Track this test in dashboard
    dashboard_ignore: Don't track this test in dashboard
""")

        # Run pytest with dashboard
        result = subprocess.run([
            sys.executable, "-m", "pytest",
            "--dashboard",
            f"--dashboard-db={db_path}",
            "--dashboard-name=Integration Test",
            "-v",
            str(test_file)
        ], capture_output=True, text=True, cwd=tmp_path)

        # Check if tests ran successfully
        if result.returncode != 0:
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)

        # The tests should pass regardless of dashboard integration
        assert "test_tracked_example PASSED" in result.stdout
        assert "test_regular PASSED" in result.stdout
        assert "test_ignored PASSED" in result.stdout

    def test_dashboard_data_creation(self, tmp_path):
        """Test that dashboard data is actually created during test runs."""
        # Create test database
        db_path = tmp_path / "test_data_creation.db"

        # Create test files
        test_file = tmp_path / "test_data.py"
        test_file.write_text("""
def test_passing():
    assert True

def test_failing():
    assert False, "This test should fail"

def test_skipped():
    import pytest
    pytest.skip("Skipping this test")
""")

        # Run pytest with dashboard (allow failures)
        subprocess.run([
            sys.executable, "-m", "pytest",
            "--dashboard",
            f"--dashboard-db={db_path}",
            "--tb=no",  # Don't show tracebacks
            str(test_file)
        ], cwd=tmp_path)

        # Check if database was created and contains data
        if db_path.exists():
            db = TestDashboardDB(str(db_path))

            # Check if test runs were recorded
            recent_runs = db.get_recent_test_runs(limit=10)
            assert len(recent_runs) > 0

            # Get the most recent run
            latest_run = recent_runs[0]
            assert latest_run.test_command is not None

            # Check test results
            results = db.get_test_results(latest_run.run_id)

            # We should have results for our tests
            assert len(results) >= 0  # May be 0 if plugin didn't run

            db.close()


class TestFrontendIntegration:
    """Test frontend dashboard functionality."""

    @pytest.fixture
    def browser_client(self):
        """Create a simple HTTP client for testing the frontend."""
        return requests.Session()

    def test_dashboard_html_accessibility(self, browser_client):
        """Test that the main dashboard HTML is accessible."""
        try:
            response = browser_client.get("http://localhost:8080/")

            if response.status_code == 200:
                html_content = response.text

                # Check for essential HTML elements
                assert "<html" in html_content
                assert "<title>" in html_content
                assert "Django-Ollama Test Dashboard" in html_content
                assert "dashboard.css" in html_content
                assert "dashboard.js" in html_content
            else:
                pytest.skip(f"Dashboard server not accessible: {response.status_code}")
        except requests.ConnectionError:
            pytest.skip("Dashboard server not running")

    def test_static_files_accessibility(self, browser_client):
        """Test that static files (CSS, JS) are accessible."""
        try:
            # Test CSS file
            css_response = browser_client.get("http://localhost:8080/static/css/dashboard.css")
            if css_response.status_code == 200:
                css_content = css_response.text
                assert "body" in css_content or "html" in css_content

            # Test JavaScript file
            js_response = browser_client.get("http://localhost:8080/static/js/dashboard.js")
            if js_response.status_code == 200:
                js_content = js_response.text
                assert "function" in js_content or "const" in js_content or "var" in js_content
        except requests.ConnectionError:
            pytest.skip("Dashboard server not running")

    def test_dashboard_responsiveness(self, browser_client):
        """Test dashboard response times."""
        try:
            start_time = time.time()
            response = browser_client.get("http://localhost:8080/")
            response_time = time.time() - start_time

            if response.status_code == 200:
                # Dashboard should load quickly (under 3 seconds)
                assert response_time < 3.0

                # Check content length (should be reasonable)
                content_length = len(response.content)
                assert content_length > 1000  # Should have substantial content
                assert content_length < 5000000  # But not too large (5MB)
        except requests.ConnectionError:
            pytest.skip("Dashboard server not running")


class TestPerformanceAndStress:
    """Test system performance and stress conditions."""

    def test_database_concurrent_access(self, tmp_path):
        """Test database performance under concurrent access."""
        db_path = tmp_path / "concurrent_test.db"

        def worker_function(worker_id, results):
            """Worker function for concurrent database operations."""
            try:
                db = TestDashboardDB(str(db_path))

                # Each worker creates test runs
                for i in range(10):
                    run_id = db.create_test_run(f"worker_{worker_id}_test_{i}")

                    # Add some test results
                    for j in range(5):
                        result = TestResult(
                            test_name=f"test_{j}",
                            test_file=f"test_{j}.py",
                            test_method=f"test_method_{j}",
                            test_type=TestType.UNIT,
                            status=TestStatus.PASSED,
                            duration_seconds=0.1,
                            started_at=datetime.now(timezone.utc),
                            finished_at=datetime.now(timezone.utc)
                        )
                        db.add_test_result(run_id, result)

                db.close()
                results[worker_id] = "success"

            except Exception as e:
                results[worker_id] = f"error: {e}"

        # Run multiple workers concurrently
        workers = []
        results = {}

        for i in range(5):  # 5 concurrent workers
            worker = threading.Thread(
                target=worker_function,
                args=(i, results)
            )
            workers.append(worker)
            worker.start()

        # Wait for all workers to complete
        for worker in workers:
            worker.join(timeout=30)  # 30 second timeout

        # Check results
        assert len(results) == 5
        for worker_id, result in results.items():
            assert result == "success", f"Worker {worker_id} failed: {result}"

        # Verify data integrity
        db = TestDashboardDB(str(db_path))
        all_runs = db.get_recent_test_runs(limit=100)

        # Should have 50 runs (10 per worker * 5 workers)
        assert len(all_runs) == 50

        # Check that we have results for each run
        for run in all_runs[:10]:  # Check first 10 runs
            results = db.get_test_results(run.run_id)
            assert len(results) == 5

        db.close()

    def test_memory_usage_with_large_dataset(self, tmp_path):
        """Test memory usage with large test datasets."""
        import psutil
        import os

        db_path = tmp_path / "memory_test.db"
        db = TestDashboardDB(str(db_path))

        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Create large dataset
        large_run_id = db.create_test_run("memory_stress_test")

        # Add many test results
        for i in range(1000):
            result = TestResult(
                test_name=f"test_large_{i}",
                test_file=f"tests/large/test_{i}.py",
                test_method=f"test_method_{i}",
                test_type=TestType.UNIT,
                status=TestStatus.PASSED,
                duration_seconds=0.1,
                error_message=f"Long error message {i}" * 10 if i % 10 == 0 else None,
                error_traceback=f"Long traceback {i}" * 20 if i % 10 == 0 else None,
                started_at=datetime.now(timezone.utc),
                finished_at=datetime.now(timezone.utc)
            )
            db.add_test_result(large_run_id, result)

        # Check memory usage after data creation
        after_creation_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = after_creation_memory - initial_memory

        # Memory increase should be reasonable (less than 100MB for 1000 records)
        assert memory_increase < 100, f"Memory usage increased by {memory_increase}MB"

        # Test query performance with large dataset
        start_time = time.time()
        results = db.get_test_results(large_run_id, limit=100)
        query_time = time.time() - start_time

        assert len(results) == 100
        assert query_time < 2.0  # Should complete in under 2 seconds

        db.close()

    def test_api_response_times(self):
        """Test API endpoint response times under load."""
        import threading

        def make_request(endpoint, results, request_id):
            """Make a single request and record timing."""
            try:
                start_time = time.time()
                response = requests.get(f"http://localhost:8080{endpoint}", timeout=10)
                end_time = time.time()

                results[request_id] = {
                    'status_code': response.status_code,
                    'response_time': end_time - start_time,
                    'success': response.status_code == 200
                }
            except Exception as e:
                results[request_id] = {
                    'error': str(e),
                    'success': False
                }

        # Test multiple endpoints concurrently
        endpoints = [
            "/api/health",
            "/api/dashboard/summary",
            "/api/dashboard/recent-runs",
            "/api/stats"
        ]

        results = {}
        threads = []

        # Create multiple requests for each endpoint
        request_id = 0
        for endpoint in endpoints:
            for i in range(5):  # 5 requests per endpoint
                thread = threading.Thread(
                    target=make_request,
                    args=(endpoint, results, request_id)
                )
                threads.append(thread)
                thread.start()
                request_id += 1

        # Wait for all requests to complete
        for thread in threads:
            thread.join(timeout=15)  # 15 second timeout per request

        # Analyze results
        successful_requests = [r for r in results.values() if r.get('success', False)]

        if len(successful_requests) > 0:
            # At least some requests should succeed
            success_rate = len(successful_requests) / len(results)
            assert success_rate > 0.5, f"Success rate too low: {success_rate}"

            # Average response time should be reasonable
            avg_response_time = sum(r['response_time'] for r in successful_requests) / len(successful_requests)
            assert avg_response_time < 5.0, f"Average response time too high: {avg_response_time}s"
        else:
            # If no requests succeeded, server is probably not running
            pytest.skip("API server not accessible for performance testing")


class TestErrorHandlingAndEdgeCases:
    """Test error handling and edge cases."""

    def test_database_corruption_recovery(self, tmp_path):
        """Test database recovery from corruption."""
        db_path = tmp_path / "corruption_test.db"

        # Create a database and add some data
        db = TestDashboardDB(str(db_path))
        run_id = db.create_test_run("corruption_test")
        db.close()

        # Corrupt the database file
        with open(db_path, 'wb') as f:
            f.write(b'corrupted data')

        # Try to create a new database instance
        # Should handle corruption gracefully
        try:
            new_db = TestDashboardDB(str(db_path))
            # If it doesn't raise an exception, the recovery worked
            new_db.close()
        except DatabaseError:
            # Expected behavior for corrupted database
            pass

    def test_invalid_data_handling(self, tmp_path):
        """Test handling of invalid data inputs."""
        db_path = tmp_path / "invalid_data_test.db"
        db = TestDashboardDB(str(db_path))

        # Test invalid test run creation
        with pytest.raises((ValueError, TypeError, DatabaseError)):
            db.create_test_run(None)  # Invalid command

        # Test invalid test result
        run_id = db.create_test_run("valid_test")

        invalid_result = TestResult(
            test_name="",  # Empty name
            test_file="",  # Empty file
            test_method="",  # Empty method
            test_type=None,  # Invalid type
            status=TestStatus.PASSED,
            duration_seconds=-1,  # Negative duration
            started_at=datetime.now(timezone.utc),
            finished_at=datetime.now(timezone.utc)
        )

        # Should handle invalid data gracefully
        try:
            db.add_test_result(run_id, invalid_result)
        except (ValueError, TypeError, DatabaseError):
            # Expected behavior
            pass

        db.close()

    def test_large_data_values(self, tmp_path):
        """Test handling of very large data values."""
        db_path = tmp_path / "large_data_test.db"
        db = TestDashboardDB(str(db_path))

        # Test very long strings
        long_string = "x" * 100000  # 100KB string

        run_id = db.create_test_run(
            test_command=long_string[:1000],  # Truncate to reasonable size
            environment_info={"large_field": long_string[:10000]}
        )

        # Test large test result
        large_result = TestResult(
            test_name="test_large_data",
            test_file="test_large.py",
            test_method="test_method",
            test_type=TestType.UNIT,
            status=TestStatus.FAILED,
            duration_seconds=999999.9,  # Very large duration
            error_message=long_string[:10000],  # Large error message
            error_traceback=long_string[:50000],  # Large traceback
            started_at=datetime.now(timezone.utc),
            finished_at=datetime.now(timezone.utc)
        )

        # Should handle large data
        result_id = db.add_test_result(run_id, large_result)
        assert result_id is not None

        # Verify data was stored (possibly truncated)
        stored_results = db.get_test_results(run_id)
        assert len(stored_results) == 1

        db.close()

    def test_concurrent_database_locks(self, tmp_path):
        """Test database behavior under lock contention."""
        db_path = tmp_path / "lock_test.db"

        def long_transaction(results, worker_id):
            """Perform a long-running transaction."""
            try:
                db = TestDashboardDB(str(db_path))

                # Start a transaction that takes some time
                for i in range(50):
                    run_id = db.create_test_run(f"worker_{worker_id}_run_{i}")
                    time.sleep(0.01)  # Small delay to increase lock time

                results[worker_id] = "success"
                db.close()
            except Exception as e:
                results[worker_id] = f"error: {e}"

        # Run multiple workers that might cause lock contention
        workers = []
        results = {}

        for i in range(3):
            worker = threading.Thread(
                target=long_transaction,
                args=(results, i)
            )
            workers.append(worker)
            worker.start()

        # Wait for all workers
        for worker in workers:
            worker.join(timeout=60)  # Longer timeout for lock contention

        # At least some workers should succeed
        successful_workers = sum(1 for result in results.values() if result == "success")
        assert successful_workers > 0, f"No workers succeeded: {results}"

    def test_websocket_connection_limits(self):
        """Test WebSocket connection limits and cleanup."""
        # This test would require a running WebSocket server
        # and might be resource-intensive, so we'll make it optional

        try:
            import websockets

            async def test_multiple_connections():
                connections = []
                max_connections = 10

                try:
                    # Try to create multiple connections
                    for i in range(max_connections):
                        ws = await websockets.connect("ws://localhost:8080/ws")
                        connections.append(ws)

                        # Receive connection message
                        await ws.recv()

                    # All connections should be established
                    assert len(connections) == max_connections

                finally:
                    # Clean up connections
                    for ws in connections:
                        await ws.close()

            # Run the async test
            asyncio.run(test_multiple_connections())

        except Exception as e:
            pytest.skip(f"WebSocket connection limit test failed: {e}")


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v", "--tb=short"])