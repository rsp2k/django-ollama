#!/usr/bin/env python3
"""
Django-Ollama Test Dashboard Launcher

Simple script to launch the dashboard server with sample data.
"""

import sys
import subprocess
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_dependencies():
    """Check if required dependencies are installed."""
    required_packages = [
        'fastapi',
        'uvicorn'
    ]

    missing_packages = []

    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)

    if missing_packages:
        logger.error(f"Missing required packages: {', '.join(missing_packages)}")
        logger.info("Install them with: pip install -r requirements.txt")
        return False

    return True


def setup_sample_data():
    """Set up sample data if database doesn't exist."""
    from database import TestDashboardDB
    from models import TestRun, TestResult, CoverageData, TestStatus, TestType
    from datetime import datetime, timezone
    import uuid
    import random

    db_path = Path(__file__).parent / "demo_dashboard.db"

    if db_path.exists():
        logger.info(f"Database already exists at {db_path}")
        return

    logger.info("Setting up sample data...")

    db = TestDashboardDB(str(db_path))

    try:
        # Create some sample test runs
        sample_runs = []

        for i in range(5):
            run_id = db.create_test_run(
                test_command=f"pytest tests/test_suite_{i+1}.py -v",
                git_branch="main",
                git_commit=f"abc123{i:02d}",
                environment_info={
                    "python_version": "3.11.0",
                    "platform": "linux",
                    "pytest_version": "7.4.0"
                }
            )

            # Update run with results
            total_tests = random.randint(20, 100)
            passed_tests = int(total_tests * random.uniform(0.7, 0.95))
            failed_tests = total_tests - passed_tests
            duration = random.uniform(30, 300)

            db.update_test_run(run_id,
                status=TestStatus.PASSED if failed_tests == 0 else TestStatus.FAILED,
                finished_at=datetime.now(timezone.utc),
                total_tests=total_tests,
                passed_tests=passed_tests,
                failed_tests=failed_tests,
                duration_seconds=duration
            )

            # Add some test results
            for j in range(min(10, total_tests)):
                test_result = TestResult(
                    test_name=f"test_function_{j+1}",
                    test_file=f"tests/test_module_{j//3 + 1}.py",
                    test_class=f"TestClass{j//3 + 1}",
                    test_method=f"test_method_{j+1}",
                    test_type=TestType.UNIT,
                    status=TestStatus.PASSED if j < passed_tests else TestStatus.FAILED,
                    duration_seconds=random.uniform(0.1, 5.0),
                    assertions_count=random.randint(1, 10),
                    started_at=datetime.now(timezone.utc),
                    finished_at=datetime.now(timezone.utc)
                )

                if test_result.status == TestStatus.FAILED:
                    test_result.error_message = f"AssertionError: Expected value but got different result in test {j+1}"
                    test_result.error_traceback = f"Traceback (most recent call last):\n  File 'test_file.py', line {j+10}, in test_method\n    assert expected == actual\nAssertionError: Expected 'foo' but got 'bar'"

                db.add_test_result(run_id, test_result)

            # Add some coverage data
            sample_files = [
                "src/main.py",
                "src/models.py",
                "src/utils.py",
                "src/api.py",
                "src/database.py"
            ]

            for file_path in sample_files:
                coverage = CoverageData(
                    file_path=file_path,
                    total_lines=random.randint(50, 500),
                    covered_lines=0,
                    missing_lines=[],
                    branch_total=random.randint(10, 50),
                    branch_covered=0
                )
                coverage.covered_lines = int(coverage.total_lines * random.uniform(0.6, 0.95))
                coverage.branch_covered = int(coverage.branch_total * random.uniform(0.5, 0.9))
                coverage.coverage_percentage = (coverage.covered_lines / coverage.total_lines) * 100

                # Generate some missing lines
                missing_count = coverage.total_lines - coverage.covered_lines
                coverage.missing_lines = random.sample(range(1, coverage.total_lines + 1), missing_count)

                db.add_coverage_data(run_id, coverage)

            sample_runs.append(run_id)

        logger.info(f"Created {len(sample_runs)} sample test runs")
        logger.info(f"Sample database created at {db_path}")

    except Exception as e:
        logger.error(f"Failed to create sample data: {e}")
        if db_path.exists():
            db_path.unlink()
        raise


def main():
    """Main launcher function."""
    logger.info("🧪 Django-Ollama Test Dashboard Launcher")

    # Check dependencies
    if not check_dependencies():
        sys.exit(1)

    # Setup sample data if needed
    try:
        setup_sample_data()
    except Exception as e:
        logger.error(f"Failed to setup sample data: {e}")
        sys.exit(1)

    # Launch server
    server_script = Path(__file__).parent / "server.py"

    logger.info("🚀 Starting dashboard server...")
    logger.info("📊 Dashboard will be available at: http://localhost:8080")
    logger.info("📚 API documentation at: http://localhost:8080/api/docs")
    logger.info("Press Ctrl+C to stop the server")

    try:
        # Use subprocess to run the server
        subprocess.run([
            sys.executable,
            str(server_script),
            "--host", "0.0.0.0",
            "--port", "8080",
            "--reload"
        ])
    except KeyboardInterrupt:
        logger.info("👋 Dashboard stopped by user")
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()