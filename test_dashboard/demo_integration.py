#!/usr/bin/env python3
"""
Demo script showing how to integrate the dashboard with test results.
This demonstrates the complete workflow from test execution to dashboard display.
"""

import sys
import json
import random
from pathlib import Path
from datetime import datetime, timezone
from typing import List

# Add current directory to path for imports
sys.path.append(str(Path(__file__).parent))

from database import TestDashboardDB
from models import TestRun, TestResult, CoverageData, TestStatus, TestType


class DashboardIntegrationDemo:
    """Demo class showing dashboard integration patterns."""

    def __init__(self):
        self.db_path = Path(__file__).parent / "demo_dashboard.db"
        self.db = TestDashboardDB(str(self.db_path))

    def simulate_test_run(self, test_suite_name: str, num_tests: int = 20) -> str:
        """Simulate a complete test run with results and coverage."""
        print(f"🧪 Starting test run for {test_suite_name}...")

        # 1. Create test run
        run_id = self.db.create_test_run(
            test_command=f"python -m pytest {test_suite_name} -v --cov=src",
            git_branch="feature/dashboard-integration",
            git_commit="abc123def456",
            environment_info={
                "python_version": "3.11.0",
                "pytest_version": "7.4.0",
                "coverage_version": "6.5.0",
                "django_version": "4.2.0",
                "ollama_version": "0.1.0",
                "platform": "linux",
                "ci": False
            }
        )

        print(f"📝 Created test run: {run_id[:8]}...")

        # 2. Simulate test execution with results
        test_results = self._generate_test_results(num_tests)
        total_tests = len(test_results)
        passed_tests = sum(1 for r in test_results if r.status == TestStatus.PASSED)
        failed_tests = sum(1 for r in test_results if r.status == TestStatus.FAILED)
        error_tests = sum(1 for r in test_results if r.status == TestStatus.ERROR)
        skipped_tests = sum(1 for r in test_results if r.status == TestStatus.SKIPPED)

        # Add each test result
        for result in test_results:
            self.db.add_test_result(run_id, result)

        print(f"✅ Added {total_tests} test results")

        # 3. Generate and add coverage data
        coverage_data = self._generate_coverage_data()
        for coverage in coverage_data:
            self.db.add_coverage_data(run_id, coverage)

        print(f"📊 Added coverage data for {len(coverage_data)} files")

        # 4. Update test run with final status
        overall_status = TestStatus.PASSED if failed_tests == 0 and error_tests == 0 else TestStatus.FAILED
        total_duration = sum(r.duration_seconds for r in test_results)

        self.db.update_test_run(
            run_id,
            status=overall_status,
            finished_at=datetime.now(timezone.utc),
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            error_tests=error_tests,
            skipped_tests=skipped_tests,
            duration_seconds=total_duration
        )

        print(f"🏁 Test run completed: {overall_status.value}")
        print(f"📈 Results: {passed_tests}P/{failed_tests}F/{error_tests}E/{skipped_tests}S")
        print(f"⏱️ Duration: {total_duration:.2f}s")

        return run_id

    def _generate_test_results(self, num_tests: int) -> List[TestResult]:
        """Generate realistic test results."""
        results = []
        test_files = [
            "tests/test_models.py",
            "tests/test_api.py",
            "tests/test_utils.py",
            "tests/test_integration.py",
            "tests/test_views.py"
        ]
        test_types = [TestType.UNIT, TestType.INTEGRATION, TestType.API, TestType.E2E]

        for i in range(num_tests):
            # Simulate realistic test distribution
            # 80% pass, 15% fail, 3% error, 2% skip
            outcome = random.choices(
                [TestStatus.PASSED, TestStatus.FAILED, TestStatus.ERROR, TestStatus.SKIPPED],
                weights=[80, 15, 3, 2]
            )[0]

            test_file = random.choice(test_files)
            test_class = f"Test{test_file.split('/')[-1].replace('test_', '').replace('.py', '').title()}"
            test_method = f"test_method_{i+1}"
            test_type = random.choice(test_types)

            result = TestResult(
                test_name=f"{test_class}::{test_method}",
                test_file=test_file,
                test_class=test_class,
                test_method=test_method,
                test_type=test_type,
                status=outcome,
                duration_seconds=random.uniform(0.1, 10.0),
                setup_duration=random.uniform(0.01, 0.5),
                teardown_duration=random.uniform(0.01, 0.3),
                assertions_count=random.randint(1, 15),
                started_at=datetime.now(timezone.utc),
                finished_at=datetime.now(timezone.utc)
            )

            # Add error details for failed/error tests
            if outcome == TestStatus.FAILED:
                result.error_message = f"AssertionError: Test assertion failed in {test_method}"
                result.error_traceback = f"""Traceback (most recent call last):
  File "{test_file}", line {random.randint(10, 100)}, in {test_method}
    assert expected == actual, f"Expected {{expected}}, got {{actual}}"
AssertionError: Expected 'expected_value', got 'actual_value'
Test assertion failed in {test_method}"""

            elif outcome == TestStatus.ERROR:
                result.error_message = f"RuntimeError: Unexpected error in {test_method}"
                result.error_traceback = f"""Traceback (most recent call last):
  File "{test_file}", line {random.randint(10, 100)}, in {test_method}
    result = some_function()
  File "src/utils.py", line {random.randint(5, 50)}, in some_function
    raise RuntimeError("Unexpected condition occurred")
RuntimeError: Unexpected error in {test_method}"""

            results.append(result)

        return results

    def _generate_coverage_data(self) -> List[CoverageData]:
        """Generate realistic coverage data."""
        source_files = [
            "src/models.py",
            "src/api.py",
            "src/utils.py",
            "src/views.py",
            "src/database.py",
            "src/auth.py",
            "src/serializers.py",
            "src/exceptions.py",
            "src/middleware.py",
            "src/tasks.py"
        ]

        coverage_data = []

        for file_path in source_files:
            total_lines = random.randint(50, 500)
            # Generate realistic coverage - most files well covered
            coverage_rate = random.uniform(0.6, 0.95) if random.random() > 0.2 else random.uniform(0.3, 0.7)
            covered_lines = int(total_lines * coverage_rate)

            # Generate missing lines
            all_lines = list(range(1, total_lines + 1))
            missing_lines = random.sample(all_lines, total_lines - covered_lines)

            # Generate branch coverage
            branch_total = random.randint(5, 30)
            branch_covered = int(branch_total * random.uniform(0.5, 0.9))

            coverage = CoverageData(
                file_path=file_path,
                total_lines=total_lines,
                covered_lines=covered_lines,
                missing_lines=sorted(missing_lines),
                excluded_lines=[],
                branch_total=branch_total,
                branch_covered=branch_covered,
                missing_branches=[],
                coverage_percentage=coverage_rate * 100
            )

            coverage_data.append(coverage)

        return coverage_data

    def show_dashboard_summary(self):
        """Display a summary of dashboard data."""
        print("\n📊 Dashboard Summary")
        print("=" * 50)

        summary = self.db.get_dashboard_summary()

        print("Recent Activity (24h):")
        recent = summary.get('recent_24h', {})
        print(f"  Total Runs: {recent.get('total_runs', 0)}")
        print(f"  Passed: {recent.get('passed_runs', 0)}")
        print(f"  Failed: {recent.get('failed_runs', 0)}")
        print(f"  Running: {recent.get('running_runs', 0)}")
        print(f"  Avg Success Rate: {recent.get('avg_success_rate', 0):.1f}%")
        print(f"  Avg Duration: {recent.get('avg_duration', 0):.2f}s")

        print("\nOverall Statistics:")
        overall = summary.get('overall', {})
        print(f"  Total Runs (All Time): {overall.get('total_runs', 0)}")
        print(f"  Last Run: {overall.get('last_run_time', 'Never')}")
        print(f"  Overall Avg Duration: {overall.get('avg_duration', 0):.2f}s")

        # Get recent runs
        recent_runs = self.db.get_recent_test_runs(limit=5)
        print(f"\nRecent Test Runs ({len(recent_runs)}):")
        for run in recent_runs:
            print(f"  {run.run_id[:8]} | {run.status.value:>7} | {run.total_tests:>3} tests | {run.duration_seconds:>6.1f}s | {run.success_rate:>5.1f}%")

        # Get trend data
        trends = self.db.get_trend_data(days=7)
        print(f"\nTrend Data (7 days): {len(trends)} data points")

        return summary

    def run_demo(self):
        """Run the complete integration demo."""
        print("🎬 Django-Ollama Dashboard Integration Demo")
        print("=" * 60)

        # Run multiple test suites to show variety
        test_suites = [
            ("tests/unit", 25),
            ("tests/integration", 15),
            ("tests/api", 20),
            ("tests/e2e", 8)
        ]

        run_ids = []
        for suite_name, num_tests in test_suites:
            run_id = self.simulate_test_run(suite_name, num_tests)
            run_ids.append(run_id)
            print()

        print(f"✨ Demo completed! Created {len(run_ids)} test runs")

        # Show summary
        self.show_dashboard_summary()

        print(f"\n🌐 Dashboard URL: http://localhost:8080")
        print(f"📊 Database: {self.db_path}")
        print("\n🚀 To start the dashboard server:")
        print("   python launch_dashboard.py")

        return run_ids


def main():
    """Main demo function."""
    demo = DashboardIntegrationDemo()

    try:
        demo.run_demo()
    except KeyboardInterrupt:
        print("\n👋 Demo stopped by user")
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        raise


if __name__ == "__main__":
    main()