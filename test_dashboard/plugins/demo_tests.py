"""
Demo test file for testing the pytest dashboard integration.

This file contains various types of tests to demonstrate the dashboard's
capabilities in capturing and displaying test results.

Run with:
    pytest --dashboard test_dashboard/plugins/demo_tests.py --dashboard-name="Demo Tests"
"""

import pytest
import time
import random
from datetime import datetime


class TestBasicFunctionality:
    """Basic test functionality demonstration."""

    def test_simple_pass(self):
        """A simple test that always passes."""
        assert 1 + 1 == 2

    def test_simple_fail(self):
        """A test that always fails to demonstrate error handling."""
        assert 1 + 1 == 3, "Math doesn't work this way!"

    def test_with_multiple_assertions(self):
        """Test with multiple assertions for assertion counting."""
        assert isinstance("hello", str)
        assert len("hello") == 5
        assert "hello".upper() == "HELLO"
        assert "hello"[:2] == "he"

    @pytest.mark.skip(reason="Demonstrating skipped test")
    def test_skipped_example(self):
        """This test will be skipped."""
        assert False, "This should never run"


class TestTimingDemonstration:
    """Tests with different execution times."""

    def test_very_fast(self):
        """Ultra-fast test (< 1ms)."""
        assert True

    def test_fast(self):
        """Fast test (~10ms)."""
        time.sleep(0.01)
        assert True

    def test_medium_speed(self):
        """Medium speed test (~100ms)."""
        time.sleep(0.1)
        result = sum(range(1000))
        assert result == 499500

    @pytest.mark.slow
    def test_slow(self):
        """Slow test (~500ms)."""
        time.sleep(0.5)
        assert True

    def test_variable_timing(self):
        """Test with variable execution time."""
        sleep_time = random.uniform(0.05, 0.3)
        time.sleep(sleep_time)
        assert sleep_time > 0


@pytest.mark.integration
class TestIntegrationExample:
    """Integration tests demonstration."""

    def test_api_simulation(self):
        """Simulate an API test."""
        # Simulate API call delay
        time.sleep(0.2)

        # Simulate API response processing
        response = {"status": "success", "data": [1, 2, 3, 4, 5]}

        assert response["status"] == "success"
        assert len(response["data"]) == 5
        assert sum(response["data"]) == 15

    def test_database_simulation(self):
        """Simulate a database integration test."""
        # Simulate database query delay
        time.sleep(0.15)

        # Simulate database results
        users = [
            {"id": 1, "name": "Alice", "active": True},
            {"id": 2, "name": "Bob", "active": False},
            {"id": 3, "name": "Charlie", "active": True},
        ]

        active_users = [u for u in users if u["active"]]

        assert len(users) == 3
        assert len(active_users) == 2
        assert all(u["active"] for u in active_users)

    def test_file_processing_simulation(self):
        """Simulate file processing test."""
        time.sleep(0.1)

        # Simulate processing multiple files
        files = ["file1.txt", "file2.csv", "file3.json"]
        processed_files = []

        for file in files:
            time.sleep(0.05)  # Processing delay
            processed_files.append(f"processed_{file}")

        assert len(processed_files) == len(files)
        assert all("processed_" in f for f in processed_files)


class TestErrorHandling:
    """Tests demonstrating various types of errors."""

    def test_assertion_error(self):
        """Test with custom assertion error message."""
        value = random.randint(1, 10)
        assert value > 5, f"Value {value} should be greater than 5"

    def test_type_error_simulation(self):
        """Test that might raise a TypeError."""
        data = {"name": "test", "value": 42}

        # This should work
        assert data["name"].upper() == "TEST"

        # This might fail depending on the data
        if random.random() > 0.7:
            # Simulate accessing wrong type
            result = data["name"] + data["value"]  # This would fail
            assert result is not None

    def test_value_error_simulation(self):
        """Test that might raise a ValueError."""
        numbers = ["1", "2", "3", "not_a_number"]
        converted = []

        for num_str in numbers[:3]:  # Only convert first 3
            converted.append(int(num_str))

        assert len(converted) == 3
        assert sum(converted) == 6

    def test_random_failure(self):
        """Test that randomly fails to simulate flaky tests."""
        if random.random() > 0.8:
            raise Exception("Random failure occurred!")
        assert True


@pytest.mark.dashboard_track
class TestSpecialTracking:
    """Tests marked for special dashboard tracking."""

    def test_critical_feature(self):
        """Critical feature test that gets special tracking."""
        time.sleep(0.1)
        critical_data = {"status": "operational", "uptime": 99.9}

        assert critical_data["status"] == "operational"
        assert critical_data["uptime"] > 99.0

    def test_performance_benchmark(self):
        """Performance benchmark test."""
        start_time = time.time()

        # Simulate work
        result = 0
        for i in range(10000):
            result += i * 2

        duration = time.time() - start_time

        assert result > 0
        assert duration < 1.0, f"Performance test took too long: {duration}s"

    def test_security_check(self):
        """Security-related test with special tracking."""
        time.sleep(0.05)

        # Simulate security validation
        permissions = ["read", "write", "admin"]
        user_permissions = ["read", "write"]

        assert "admin" not in user_permissions
        assert all(p in permissions for p in user_permissions)


@pytest.mark.dashboard_ignore
class TestInternalHelpers:
    """Internal helper tests that don't clutter the dashboard."""

    def test_helper_function_1(self):
        """Internal helper test 1."""
        assert True

    def test_helper_function_2(self):
        """Internal helper test 2."""
        assert True


class TestCoverageDemo:
    """Tests to demonstrate coverage tracking."""

    def test_covered_function(self):
        """Test that covers a simple function."""
        def sample_function(x, y):
            if x > y:
                return x * 2
            else:
                return y * 2

        result = sample_function(5, 3)
        assert result == 10

    def test_partial_coverage(self):
        """Test that only covers some branches."""
        def complex_function(a, b, c):
            if a > 0:
                if b > 0:
                    return a + b
                else:
                    return a - b  # This branch won't be covered
            else:
                return c  # This branch won't be covered either

        result = complex_function(5, 3, 1)
        assert result == 8

    def test_exception_handling(self):
        """Test exception handling paths."""
        def risky_function(value):
            try:
                return 10 / value
            except ZeroDivisionError:
                return 0
            finally:
                pass  # Cleanup code

        assert risky_function(5) == 2.0
        assert risky_function(0) == 0


@pytest.mark.parametrize("input_value,expected", [
    (1, 2),
    (2, 4),
    (3, 6),
    (4, 8),
    (5, 10),
])
def test_parametrized_example(input_value, expected):
    """Parametrized test to show multiple test instances."""
    time.sleep(0.02)  # Small delay to show timing differences
    result = input_value * 2
    assert result == expected


class TestAsyncSimulation:
    """Tests that simulate async operations."""

    def test_async_simulation_1(self):
        """Simulate async operation with sleep."""
        time.sleep(0.3)  # Simulate async I/O
        assert True

    def test_async_simulation_2(self):
        """Another async simulation."""
        time.sleep(0.2)  # Different timing
        assert True

    def test_concurrent_operations(self):
        """Simulate multiple concurrent operations."""
        # Simulate starting multiple operations
        operations = []
        for i in range(3):
            time.sleep(0.1)  # Simulate operation delay
            operations.append(f"operation_{i}")

        assert len(operations) == 3
        assert all("operation_" in op for op in operations)


# Test that demonstrates setup and teardown timing
class TestSetupTeardown:
    """Tests with setup and teardown to show timing breakdown."""

    def setup_method(self):
        """Setup method with some delay."""
        time.sleep(0.05)
        self.test_data = {"initialized": True}

    def teardown_method(self):
        """Teardown method with cleanup delay."""
        time.sleep(0.03)
        self.test_data = None

    def test_with_setup_teardown(self):
        """Test that uses setup and teardown."""
        time.sleep(0.1)  # Actual test time
        assert self.test_data["initialized"] is True

    def test_another_setup_teardown(self):
        """Another test with setup and teardown."""
        time.sleep(0.08)
        assert self.test_data is not None


if __name__ == "__main__":
    # When run directly, execute with dashboard
    import subprocess
    import sys

    cmd = [
        sys.executable, "-m", "pytest",
        __file__,
        "--dashboard",
        "--dashboard-name=Demo Test Suite",
        "-v"
    ]

    print("Running demo tests with dashboard integration...")
    print(f"Command: {' '.join(cmd)}")

    subprocess.run(cmd)