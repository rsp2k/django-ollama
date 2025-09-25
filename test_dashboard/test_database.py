#!/usr/bin/env python3
"""
Test suite for the django-ollama test dashboard database layer.

Validates all core functionality including:
- Database initialization and migrations
- Test run and result management
- Coverage data operations
- Query optimization
- Data integrity and performance
"""

import unittest
import tempfile
import os
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path

from database import TestDashboardDB, DatabaseError
from models import TestRun, TestResult, CoverageData, TestStatus, TestType
from queries import QueryOptimizer
from migrations.migration_manager import MigrationManager


class TestDatabaseOperations(unittest.TestCase):
    """Test core database operations."""

    def setUp(self):
        """Set up test database."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = self.temp_db.name
        self.db = TestDashboardDB(self.db_path, retention_days=7)

    def tearDown(self):
        """Clean up test database."""
        self.db.close()
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_database_initialization(self):
        """Test database initialization and schema creation."""
        # Database should be initialized
        self.assertTrue(os.path.exists(self.db_path))

        # Check schema exists
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        conn.close()

        expected_tables = {'test_runs', 'test_results', 'coverage_data', 'test_metrics', 'schema_migrations'}

        # Debug: Print actual tables if assertion fails
        if not expected_tables.issubset(tables):
            print(f"Expected: {expected_tables}")
            print(f"Actual: {tables}")
            print(f"Missing: {expected_tables - tables}")

        self.assertTrue(expected_tables.issubset(tables))

    def test_test_run_lifecycle(self):
        """Test complete test run lifecycle."""
        # Create test run
        run_id = self.db.create_test_run(
            test_command="pytest tests/",
            git_commit="abc123",
            git_branch="main"
        )

        self.assertIsNotNone(run_id)
        self.assertTrue(len(run_id) > 10)  # Should be UUID

        # Retrieve test run
        test_run = self.db.get_test_run(run_id)
        self.assertIsNotNone(test_run)
        self.assertEqual(test_run.run_id, run_id)
        self.assertEqual(test_run.status, TestStatus.RUNNING)

        # Update test run
        success = self.db.update_test_run(run_id,
            status=TestStatus.PASSED,
            total_tests=10,
            passed_tests=8,
            failed_tests=2,
            duration_seconds=45.5
        )

        self.assertTrue(success)

        # Verify update
        updated_run = self.db.get_test_run(run_id)
        self.assertEqual(updated_run.status, TestStatus.PASSED)
        self.assertEqual(updated_run.total_tests, 10)
        self.assertEqual(updated_run.success_rate, 80.0)

    def test_test_results_management(self):
        """Test test result operations."""
        # Create test run first
        run_id = self.db.create_test_run(test_command="pytest")

        # Add test result
        test_result = TestResult(
            test_name="test_user_login",
            test_file="tests/test_auth.py",
            test_class="TestAuthentication",
            test_method="test_user_login",
            test_type=TestType.UNIT,
            status=TestStatus.PASSED,
            duration_seconds=0.123,
            assertions_count=5
        )

        result_id = self.db.add_test_result(run_id, test_result)
        self.assertIsNotNone(result_id)

        # Retrieve test results
        results = self.db.get_test_results(run_id)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].test_name, "test_user_login")
        self.assertEqual(results[0].status, TestStatus.PASSED)

        # Test filtering
        failed_result = TestResult(
            test_name="test_user_logout",
            test_file="tests/test_auth.py",
            test_method="test_user_logout",
            test_type=TestType.UNIT,
            status=TestStatus.FAILED,
            duration_seconds=0.456,
            error_message="AssertionError: Expected redirect"
        )

        self.db.add_test_result(run_id, failed_result)

        # Get only failed tests
        failed_results = self.db.get_test_results(run_id, status=TestStatus.FAILED)
        self.assertEqual(len(failed_results), 1)
        self.assertEqual(failed_results[0].status, TestStatus.FAILED)

    def test_coverage_data_operations(self):
        """Test coverage data management."""
        # Create test run
        run_id = self.db.create_test_run(test_command="pytest --cov")

        # Add coverage data
        coverage = CoverageData(
            file_path="src/models.py",
            total_lines=100,
            covered_lines=85,
            missing_lines=[10, 25, 50, 75, 90],
            coverage_percentage=85.0,
            branch_total=20,
            branch_covered=18
        )

        coverage_id = self.db.add_coverage_data(run_id, coverage)
        self.assertIsNotNone(coverage_id)

        # Get coverage summary
        summary = self.db.get_coverage_summary(run_id)
        self.assertEqual(summary['file_count'], 1)
        self.assertEqual(summary['total_lines'], 100)
        self.assertEqual(summary['covered_lines'], 85)
        self.assertEqual(summary['line_coverage'], 85.0)

    def test_dashboard_summary(self):
        """Test dashboard summary generation."""
        # Create test data
        run_id = self.db.create_test_run(test_command="pytest")

        # Update to completed
        self.db.update_test_run(run_id,
            status=TestStatus.PASSED,
            total_tests=50,
            passed_tests=45,
            failed_tests=5,
            duration_seconds=120.0
        )

        # Get summary
        summary = self.db.get_dashboard_summary()

        # Should have recent data (though might be 0 due to timing)
        self.assertIn('recent_24h', summary)
        self.assertIn('overall', summary)
        self.assertIn('running_tests', summary)

        # Overall should show our test
        self.assertGreaterEqual(summary['overall']['total_runs'], 1)

    def test_data_cleanup(self):
        """Test data retention and cleanup."""
        # Create old test run (simulate by direct database insertion)
        old_date = datetime.now(timezone.utc) - timedelta(days=10)

        conn = self.db._get_connection()
        cursor = conn.execute("""
            INSERT INTO test_runs (run_id, started_at, status, created_at)
            VALUES (?, ?, ?, ?)
        """, ("old-run-123", old_date, TestStatus.PASSED.value, old_date))
        conn.commit()

        # Verify it exists
        runs_before = self.db.get_recent_test_runs(limit=100)
        old_run_exists = any(run.run_id == "old-run-123" for run in runs_before)
        self.assertTrue(old_run_exists)

        # Clean up (with 7 day retention, 10 day old run should be removed)
        deleted_count = self.db.cleanup_old_data()
        self.assertGreaterEqual(deleted_count, 1)

        # Verify cleanup
        runs_after = self.db.get_recent_test_runs(limit=100)
        old_run_exists_after = any(run.run_id == "old-run-123" for run in runs_after)
        self.assertFalse(old_run_exists_after)


class TestQueryOptimizer(unittest.TestCase):
    """Test query optimization functionality."""

    def setUp(self):
        """Set up test database with sample data."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = self.temp_db.name
        self.db = TestDashboardDB(self.db_path, retention_days=30)
        self.optimizer = QueryOptimizer(self.db._get_connection)

        # Create sample test run with results
        self.run_id = self.db.create_test_run(test_command="pytest tests/")

        # Add several test results
        for i in range(10):
            status = TestStatus.PASSED if i < 8 else TestStatus.FAILED
            result = TestResult(
                test_name=f"test_function_{i}",
                test_file=f"tests/test_file_{i % 3}.py",
                test_method=f"test_function_{i}",
                test_type=TestType.UNIT,
                status=status,
                duration_seconds=0.1 * (i + 1),
                error_message="Test failed" if status == TestStatus.FAILED else None
            )
            self.db.add_test_result(self.run_id, result)

        # Complete the run
        self.db.update_test_run(self.run_id,
            status=TestStatus.FAILED,
            total_tests=10,
            passed_tests=8,
            failed_tests=2,
            duration_seconds=15.0
        )

    def tearDown(self):
        """Clean up test database."""
        self.db.close()
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_performance_metrics(self):
        """Test performance metrics query."""
        metrics = self.optimizer.get_test_run_performance_metrics(self.run_id)

        self.assertIsNotNone(metrics)
        self.assertIn('run_info', metrics)
        self.assertIn('status_breakdown', metrics)
        self.assertIn('slowest_tests', metrics)

        # Check run info
        self.assertEqual(metrics['run_info']['total_tests'], 10)

        # Check status breakdown
        status_breakdown = metrics['status_breakdown']
        self.assertEqual(status_breakdown['PASSED']['count'], 8)
        self.assertEqual(status_breakdown['FAILED']['count'], 2)

        # Check slowest tests
        slowest = metrics['slowest_tests']
        self.assertGreater(len(slowest), 0)
        # Should be sorted by duration (descending)
        self.assertGreaterEqual(slowest[0]['duration_seconds'], slowest[-1]['duration_seconds'])

    def test_failure_analysis(self):
        """Test failure analysis query."""
        analysis = self.optimizer.get_failure_analysis(self.run_id)

        self.assertIsNotNone(analysis)
        self.assertIn('failed_tests', analysis)
        self.assertIn('summary', analysis)

        # Should have 2 failed tests
        self.assertEqual(analysis['summary']['total_failures'], 2)
        self.assertEqual(len(analysis['failed_tests']), 2)

        # Failed tests should have error messages
        for test in analysis['failed_tests']:
            self.assertIsNotNone(test['error_message'])

    def test_test_suite_health(self):
        """Test suite health analysis."""
        health = self.optimizer.get_test_suite_health()

        self.assertIsNotNone(health)
        self.assertIn('health_score', health)
        self.assertIn('recommendations', health)

        # Health score should be 0-100
        score = health['health_score']
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)


class TestMigrationManager(unittest.TestCase):
    """Test database migration functionality."""

    def setUp(self):
        """Set up temporary database for migration testing."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = self.temp_db.name

        # Use the migrations directory from our package
        migrations_dir = Path(__file__).parent / "migrations"
        self.migrator = MigrationManager(self.db_path, str(migrations_dir))

    def tearDown(self):
        """Clean up test database."""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_migration_initialization(self):
        """Test migration table initialization."""
        self.migrator.initialize_migration_table()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='schema_migrations'")
        result = cursor.fetchone()
        conn.close()

        self.assertIsNotNone(result)

    def test_migration_discovery(self):
        """Test migration file discovery."""
        migrations = self.migrator.discover_migrations()

        # Should find at least our initial migration
        self.assertGreater(len(migrations), 0)

        # Check format of discovered migrations
        for version, path in migrations:
            self.assertRegex(version, r'^\d{3}$')
            self.assertTrue(path.exists())
            self.assertTrue(path.name.endswith('.sql'))

    def test_migration_execution(self):
        """Test migration application."""
        success = self.migrator.migrate()
        self.assertTrue(success)

        # Check applied migrations
        applied = self.migrator.get_applied_migrations()
        self.assertGreater(len(applied), 0)

        # Should have our initial migration
        self.assertIn('001', applied)

        # Current version should be set
        current = self.migrator.get_current_version()
        self.assertIsNotNone(current)

    def test_schema_validation(self):
        """Test schema validation."""
        # Apply migrations first
        self.migrator.migrate()

        # Validate schema
        is_valid = self.migrator.validate_schema()
        self.assertTrue(is_valid)

    def test_migration_status(self):
        """Test migration status reporting."""
        status = self.migrator.get_migration_status()

        self.assertIn('total_migrations', status)
        self.assertIn('applied_count', status)
        self.assertIn('pending_count', status)
        self.assertIn('schema_valid', status)


def run_tests():
    """Run all database tests."""
    print("🧪 Running Django-Ollama Test Dashboard Database Tests")
    print("=" * 60)

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add test cases
    suite.addTests(loader.loadTestsFromTestCase(TestDatabaseOperations))
    suite.addTests(loader.loadTestsFromTestCase(TestQueryOptimizer))
    suite.addTests(loader.loadTestsFromTestCase(TestMigrationManager))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Summary
    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("✅ All tests passed!")
        return True
    else:
        print(f"❌ {len(result.failures)} failures, {len(result.errors)} errors")
        return False


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)