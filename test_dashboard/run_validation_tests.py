#!/usr/bin/env python3
"""
Django-Ollama Test Dashboard Comprehensive Validation Suite

This script runs a complete validation of the test dashboard system including:
- System requirements validation
- Database integrity tests
- API endpoint validation
- WebSocket functionality tests
- pytest plugin integration tests
- Performance benchmarks
- Security validation

Usage:
    python run_validation_tests.py                    # Full validation
    python run_validation_tests.py --quick           # Quick validation
    python run_validation_tests.py --component api   # Test specific component
    python run_validation_tests.py --report          # Generate detailed report
"""

import argparse
import json
import multiprocessing
import os
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import uuid

# Add test_dashboard to path
sys.path.insert(0, str(Path(__file__).parent))

# Import validation modules
from setup_dashboard import SystemValidator, print_success, print_error, print_info, print_header
from benchmark_dashboard import (
    DatabaseBenchmark, APIBenchmark, WebSocketBenchmark, SystemBenchmark, PerformanceMetrics
)


class ValidationResult:
    """Container for validation test results."""

    def __init__(self, component: str, test_name: str):
        self.component = component
        self.test_name = test_name
        self.passed = False
        self.duration = 0.0
        self.error_message = ""
        self.details = {}
        self.start_time = time.time()

    def mark_passed(self, details: Dict = None):
        """Mark test as passed."""
        self.passed = True
        self.duration = time.time() - self.start_time
        self.details = details or {}

    def mark_failed(self, error_message: str, details: Dict = None):
        """Mark test as failed."""
        self.passed = False
        self.duration = time.time() - self.start_time
        self.error_message = error_message
        self.details = details or {}

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'component': self.component,
            'test_name': self.test_name,
            'passed': self.passed,
            'duration': self.duration,
            'error_message': self.error_message,
            'details': self.details
        }


class ComponentValidator:
    """Base class for component-specific validators."""

    def __init__(self, name: str):
        self.name = name
        self.results = []

    def add_result(self, result: ValidationResult):
        """Add a validation result."""
        self.results.append(result)

    def run_validation(self) -> List[ValidationResult]:
        """Run validation tests for this component."""
        raise NotImplementedError

    def print_summary(self):
        """Print validation summary for this component."""
        if not self.results:
            return

        passed = sum(1 for r in self.results if r.passed)
        total = len(self.results)
        success_rate = passed / total * 100 if total > 0 else 0

        print(f"\n{self.name} Component:")
        print(f"  Tests: {passed}/{total} passed ({success_rate:.1f}%)")

        failed_tests = [r for r in self.results if not r.passed]
        if failed_tests:
            print("  Failed tests:")
            for result in failed_tests:
                print(f"    ❌ {result.test_name}: {result.error_message}")


class DatabaseValidator(ComponentValidator):
    """Validate database functionality."""

    def __init__(self):
        super().__init__("Database")

    def run_validation(self) -> List[ValidationResult]:
        """Run database validation tests."""
        print_info("Validating database functionality...")

        # Test database creation
        result = ValidationResult("database", "database_creation")
        try:
            with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
                db_path = f.name

            from database import TestDashboardDB

            db = TestDashboardDB(db_path)

            # Verify tables exist
            conn = db._get_connection()
            cursor = conn.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
            """)
            tables = [row[0] for row in cursor.fetchall()]

            expected_tables = ['test_runs', 'test_results', 'coverage_data', 'test_metrics']
            if all(table in tables for table in expected_tables):
                result.mark_passed({'tables': tables})
            else:
                missing = set(expected_tables) - set(tables)
                result.mark_failed(f"Missing tables: {missing}")

            db.close()

            # Cleanup
            if Path(db_path).exists():
                Path(db_path).unlink()

        except Exception as e:
            result.mark_failed(f"Database creation failed: {e}")

        self.add_result(result)

        # Test CRUD operations
        result = ValidationResult("database", "crud_operations")
        try:
            with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
                db_path = f.name

            db = TestDashboardDB(db_path)

            # Create test run
            run_id = db.create_test_run("validation_test")
            if not run_id:
                raise Exception("Failed to create test run")

            # Read test run
            run = db.get_test_run(run_id)
            if not run or run.run_id != run_id:
                raise Exception("Failed to read test run")

            # Update test run
            updated = db.update_test_run(run_id, total_tests=10, passed_tests=8)
            if not updated:
                raise Exception("Failed to update test run")

            # Add test result
            from models import TestResult, TestStatus, TestType
            test_result = TestResult(
                test_name="validation_test",
                test_file="validation.py",
                test_method="test_validation",
                test_type=TestType.UNIT,
                status=TestStatus.PASSED,
                duration_seconds=0.1,
                started_at=datetime.now(),
                finished_at=datetime.now()
            )

            result_id = db.add_test_result(run_id, test_result)
            if not result_id:
                raise Exception("Failed to add test result")

            result.mark_passed({
                'run_id': run_id,
                'result_id': result_id
            })

            db.close()

            if Path(db_path).exists():
                Path(db_path).unlink()

        except Exception as e:
            result.mark_failed(f"CRUD operations failed: {e}")

        self.add_result(result)

        # Test query performance
        result = ValidationResult("database", "query_performance")
        try:
            with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
                db_path = f.name

            db = TestDashboardDB(db_path)

            # Create test data
            run_ids = []
            for i in range(100):
                run_id = db.create_test_run(f"perf_test_{i}")
                run_ids.append(run_id)

            # Test query speed
            start_time = time.time()
            recent_runs = db.get_recent_test_runs(limit=50)
            query_time = time.time() - start_time

            if query_time < 1.0 and len(recent_runs) == 50:
                result.mark_passed({
                    'query_time': query_time,
                    'results_count': len(recent_runs)
                })
            else:
                result.mark_failed(f"Query too slow: {query_time:.2f}s or incorrect count: {len(recent_runs)}")

            db.close()

            if Path(db_path).exists():
                Path(db_path).unlink()

        except Exception as e:
            result.mark_failed(f"Query performance test failed: {e}")

        self.add_result(result)

        return self.results


class APIValidator(ComponentValidator):
    """Validate API functionality."""

    def __init__(self, base_url: str = "http://localhost:8080"):
        super().__init__("API")
        self.base_url = base_url

    def run_validation(self) -> List[ValidationResult]:
        """Run API validation tests."""
        print_info("Validating API functionality...")

        import requests

        # Test health endpoint
        result = ValidationResult("api", "health_endpoint")
        try:
            response = requests.get(f"{self.base_url}/api/health", timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    result.mark_passed({'response_time': response.elapsed.total_seconds()})
                else:
                    result.mark_failed(f"Unhealthy status: {data.get('status')}")
            else:
                result.mark_failed(f"HTTP {response.status_code}: {response.text}")

        except requests.exceptions.ConnectionError:
            result.mark_failed("API server not running or not accessible")
        except Exception as e:
            result.mark_failed(f"Health check failed: {e}")

        self.add_result(result)

        # Skip other API tests if server is not running
        if not result.passed:
            print_info("Skipping remaining API tests (server not accessible)")
            return self.results

        # Test dashboard summary endpoint
        result = ValidationResult("api", "dashboard_summary")
        try:
            response = requests.get(f"{self.base_url}/api/dashboard/summary", timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success" and "data" in data:
                    result.mark_passed({'response_time': response.elapsed.total_seconds()})
                else:
                    result.mark_failed(f"Invalid response format: {data}")
            else:
                result.mark_failed(f"HTTP {response.status_code}: {response.text}")

        except Exception as e:
            result.mark_failed(f"Dashboard summary failed: {e}")

        self.add_result(result)

        # Test recent runs endpoint
        result = ValidationResult("api", "recent_runs")
        try:
            response = requests.get(f"{self.base_url}/api/dashboard/recent-runs", timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success" and isinstance(data.get("data"), list):
                    result.mark_passed({
                        'response_time': response.elapsed.total_seconds(),
                        'runs_count': len(data["data"])
                    })
                else:
                    result.mark_failed(f"Invalid response format: {data}")
            else:
                result.mark_failed(f"HTTP {response.status_code}: {response.text}")

        except Exception as e:
            result.mark_failed(f"Recent runs test failed: {e}")

        self.add_result(result)

        # Test system stats endpoint
        result = ValidationResult("api", "system_stats")
        try:
            response = requests.get(f"{self.base_url}/api/stats", timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success" and "data" in data:
                    result.mark_passed({'response_time': response.elapsed.total_seconds()})
                else:
                    result.mark_failed(f"Invalid response format: {data}")
            else:
                result.mark_failed(f"HTTP {response.status_code}: {response.text}")

        except Exception as e:
            result.mark_failed(f"System stats test failed: {e}")

        self.add_result(result)

        return self.results


class WebSocketValidator(ComponentValidator):
    """Validate WebSocket functionality."""

    def __init__(self, ws_url: str = "ws://localhost:8080/ws"):
        super().__init__("WebSocket")
        self.ws_url = ws_url

    def run_validation(self) -> List[ValidationResult]:
        """Run WebSocket validation tests."""
        print_info("Validating WebSocket functionality...")

        import asyncio
        import json

        try:
            import websockets
        except ImportError:
            result = ValidationResult("websocket", "websocket_import")
            result.mark_failed("websockets package not available")
            self.add_result(result)
            return self.results

        # Test WebSocket connection
        result = ValidationResult("websocket", "connection")

        async def test_connection():
            try:
                async with websockets.connect(self.ws_url, timeout=10) as websocket:
                    # Should receive connection established message
                    message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    data = json.loads(message)

                    if data.get("type") == "connection_established":
                        result.mark_passed({'connection_id': data.get('connection_id')})
                    else:
                        result.mark_failed(f"Unexpected message type: {data.get('type')}")

            except asyncio.TimeoutError:
                result.mark_failed("Connection timeout")
            except Exception as e:
                result.mark_failed(f"Connection failed: {e}")

        try:
            asyncio.run(test_connection())
        except Exception as e:
            result.mark_failed(f"WebSocket test failed: {e}")

        self.add_result(result)

        # Skip other WebSocket tests if connection failed
        if not result.passed:
            print_info("Skipping remaining WebSocket tests (connection failed)")
            return self.results

        # Test ping/pong
        result = ValidationResult("websocket", "ping_pong")

        async def test_ping_pong():
            try:
                async with websockets.connect(self.ws_url, timeout=10) as websocket:
                    # Skip connection message
                    await websocket.recv()

                    # Send ping
                    ping_message = {"type": "ping"}
                    await websocket.send(json.dumps(ping_message))

                    # Wait for pong
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    data = json.loads(response)

                    if data.get("type") == "pong":
                        result.mark_passed({'response_time': result.duration})
                    else:
                        result.mark_failed(f"Expected pong, got: {data.get('type')}")

            except Exception as e:
                result.mark_failed(f"Ping/pong failed: {e}")

        try:
            asyncio.run(test_ping_pong())
        except Exception as e:
            result.mark_failed(f"Ping/pong test failed: {e}")

        self.add_result(result)

        return self.results


class PytestPluginValidator(ComponentValidator):
    """Validate pytest plugin functionality."""

    def __init__(self):
        super().__init__("pytest Plugin")

    def run_validation(self) -> List[ValidationResult]:
        """Run pytest plugin validation tests."""
        print_info("Validating pytest plugin functionality...")

        # Test plugin import
        result = ValidationResult("pytest_plugin", "plugin_import")
        try:
            from plugins.pytest_dashboard import DashboardTestPlugin
            plugin = DashboardTestPlugin()

            result.mark_passed({'plugin_class': str(type(plugin))})

        except ImportError as e:
            result.mark_failed(f"Failed to import plugin: {e}")
        except Exception as e:
            result.mark_failed(f"Plugin import error: {e}")

        self.add_result(result)

        # Test plugin configuration
        result = ValidationResult("pytest_plugin", "plugin_configuration")
        try:
            import subprocess
            import tempfile

            with tempfile.TemporaryDirectory() as temp_dir:
                # Create a simple test file
                test_file = Path(temp_dir) / "test_plugin_validation.py"
                test_file.write_text("""
import pytest

def test_simple():
    assert True

def test_another():
    assert 1 + 1 == 2
""")

                # Run pytest with --help to check if dashboard options are available
                process = subprocess.run([
                    sys.executable, "-m", "pytest", "--help"
                ], capture_output=True, text=True, cwd=temp_dir, timeout=30)

                if process.returncode == 0 and "--dashboard" in process.stdout:
                    result.mark_passed({'help_output_contains_dashboard': True})
                else:
                    result.mark_failed("Dashboard options not available in pytest --help")

        except Exception as e:
            result.mark_failed(f"Plugin configuration test failed: {e}")

        self.add_result(result)

        return self.results


class SecurityValidator(ComponentValidator):
    """Validate security features."""

    def __init__(self, base_url: str = "http://localhost:8080"):
        super().__init__("Security")
        self.base_url = base_url

    def run_validation(self) -> List[ValidationResult]:
        """Run security validation tests."""
        print_info("Validating security features...")

        import requests

        # Test CORS headers
        result = ValidationResult("security", "cors_headers")
        try:
            response = requests.options(f"{self.base_url}/api/health", timeout=10)

            cors_headers = [
                'access-control-allow-origin',
                'access-control-allow-methods'
            ]

            missing_headers = []
            for header in cors_headers:
                if header.lower() not in [h.lower() for h in response.headers]:
                    missing_headers.append(header)

            if not missing_headers:
                result.mark_passed({'cors_headers': dict(response.headers)})
            else:
                result.mark_failed(f"Missing CORS headers: {missing_headers}")

        except requests.exceptions.ConnectionError:
            result.mark_failed("API server not accessible")
        except Exception as e:
            result.mark_failed(f"CORS test failed: {e}")

        self.add_result(result)

        # Test SQL injection protection (basic check)
        result = ValidationResult("security", "sql_injection_protection")
        try:
            # Test with potentially malicious input
            malicious_inputs = [
                "'; DROP TABLE test_runs; --",
                "' OR '1'='1",
                "UNION SELECT * FROM test_runs",
            ]

            all_safe = True
            for malicious_input in malicious_inputs:
                response = requests.get(
                    f"{self.base_url}/api/dashboard/runs/{malicious_input}",
                    timeout=10
                )

                # Should return 404 (not found) or 400 (bad request), not 500 (server error)
                if response.status_code == 500:
                    all_safe = False
                    break

            if all_safe:
                result.mark_passed({'tested_inputs': len(malicious_inputs)})
            else:
                result.mark_failed("Potential SQL injection vulnerability detected")

        except requests.exceptions.ConnectionError:
            result.mark_failed("API server not accessible")
        except Exception as e:
            result.mark_failed(f"SQL injection test failed: {e}")

        self.add_result(result)

        # Test input validation
        result = ValidationResult("security", "input_validation")
        try:
            # Test with invalid data
            invalid_data = {
                "type": "test_run_start",
                "run_id": "x" * 10000,  # Very long string
                "total_tests": "not_a_number"
            }

            response = requests.post(
                f"{self.base_url}/api/test/simulate-event",
                json=invalid_data,
                timeout=10
            )

            # Should handle invalid input gracefully
            if response.status_code in [400, 422]:  # Bad request or validation error
                result.mark_passed({'response_code': response.status_code})
            elif response.status_code == 500:
                result.mark_failed("Server error on invalid input (poor error handling)")
            else:
                result.mark_failed(f"Unexpected response to invalid input: {response.status_code}")

        except requests.exceptions.ConnectionError:
            result.mark_failed("API server not accessible")
        except Exception as e:
            result.mark_failed(f"Input validation test failed: {e}")

        self.add_result(result)

        return self.results


class ValidationSuite:
    """Main validation suite coordinator."""

    def __init__(self, quick_mode: bool = False):
        self.quick_mode = quick_mode
        self.validators = []
        self.start_time = time.time()
        self.system_info = {
            'python_version': sys.version,
            'platform': sys.platform,
            'cpu_count': multiprocessing.cpu_count(),
            'timestamp': datetime.now().isoformat()
        }

    def add_validator(self, validator: ComponentValidator):
        """Add a component validator."""
        self.validators.append(validator)

    def run_all_validations(self) -> Dict:
        """Run all validation tests."""
        print_header("Django-Ollama Test Dashboard Validation Suite")

        # System validation first
        system_validator = SystemValidator()
        system_passed = system_validator.validate_all()

        if not system_passed:
            print_error("System validation failed. Fix issues before proceeding.")
            return {
                'system_validation': False,
                'components': [],
                'summary': {
                    'total_tests': 0,
                    'passed_tests': 0,
                    'failed_tests': 0,
                    'success_rate': 0.0
                }
            }

        # Run component validations
        component_results = []
        all_results = []

        for validator in self.validators:
            print_header(f"Validating {validator.name} Component")

            try:
                validator_results = validator.run_validation()
                all_results.extend(validator_results)

                component_summary = {
                    'component': validator.name,
                    'total_tests': len(validator_results),
                    'passed_tests': sum(1 for r in validator_results if r.passed),
                    'failed_tests': sum(1 for r in validator_results if not r.passed),
                    'results': [r.to_dict() for r in validator_results]
                }

                component_results.append(component_summary)
                validator.print_summary()

            except Exception as e:
                print_error(f"Validator {validator.name} failed: {e}")
                component_results.append({
                    'component': validator.name,
                    'error': str(e),
                    'total_tests': 0,
                    'passed_tests': 0,
                    'failed_tests': 1,
                    'results': []
                })

        # Calculate overall summary
        total_tests = sum(comp['total_tests'] for comp in component_results)
        passed_tests = sum(comp['passed_tests'] for comp in component_results)
        failed_tests = sum(comp['failed_tests'] for comp in component_results)
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0

        duration = time.time() - self.start_time

        summary = {
            'system_validation': system_passed,
            'components': component_results,
            'summary': {
                'total_tests': total_tests,
                'passed_tests': passed_tests,
                'failed_tests': failed_tests,
                'success_rate': success_rate,
                'duration': duration
            },
            'system_info': self.system_info
        }

        self.print_final_summary(summary)
        return summary

    def print_final_summary(self, summary: Dict):
        """Print final validation summary."""
        print_header("Validation Summary")

        overall_summary = summary['summary']

        print(f"Total Tests: {overall_summary['total_tests']}")
        print(f"Passed: {overall_summary['passed_tests']}")
        print(f"Failed: {overall_summary['failed_tests']}")
        print(f"Success Rate: {overall_summary['success_rate']:.1f}%")
        print(f"Duration: {overall_summary['duration']:.2f} seconds")

        if overall_summary['failed_tests'] == 0:
            print_success("\n🎉 All validation tests passed!")
            print_info("The Django-Ollama Test Dashboard is ready for use.")
        else:
            print_error(f"\n❌ {overall_summary['failed_tests']} validation tests failed.")
            print_info("Review the failures above and fix issues before deployment.")

        # Component breakdown
        print("\nComponent Breakdown:")
        for component in summary['components']:
            if 'error' in component:
                print(f"  {component['component']}: ERROR - {component['error']}")
            else:
                success_rate = (component['passed_tests'] / component['total_tests'] * 100) if component['total_tests'] > 0 else 0
                print(f"  {component['component']}: {component['passed_tests']}/{component['total_tests']} ({success_rate:.1f}%)")


def main():
    """Main validation function."""
    parser = argparse.ArgumentParser(description="Django-Ollama Test Dashboard Validation Suite")
    parser.add_argument("--quick", action="store_true", help="Run quick validation (skip performance tests)")
    parser.add_argument("--component", choices=['database', 'api', 'websocket', 'plugin', 'security'], help="Test specific component only")
    parser.add_argument("--report", help="Save detailed report to JSON file")
    parser.add_argument("--server-url", default="http://localhost:8080", help="Dashboard server URL")
    parser.add_argument("--websocket-url", default="ws://localhost:8080/ws", help="WebSocket URL")

    args = parser.parse_args()

    # Initialize validation suite
    suite = ValidationSuite(quick_mode=args.quick)

    # Add validators based on component selection
    if not args.component or args.component == 'database':
        suite.add_validator(DatabaseValidator())

    if not args.component or args.component == 'api':
        suite.add_validator(APIValidator(args.server_url))

    if not args.component or args.component == 'websocket':
        suite.add_validator(WebSocketValidator(args.websocket_url))

    if not args.component or args.component == 'plugin':
        suite.add_validator(PytestPluginValidator())

    if not args.component or args.component == 'security':
        suite.add_validator(SecurityValidator(args.server_url))

    # Run validation
    results = suite.run_all_validations()

    # Save report if requested
    if args.report:
        with open(args.report, 'w') as f:
            json.dump(results, f, indent=2)
        print_info(f"Detailed report saved to {args.report}")

    # Exit with appropriate code
    if results['summary']['failed_tests'] == 0:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()