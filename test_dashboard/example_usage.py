#!/usr/bin/env python3
"""
Example usage of the django-ollama test dashboard database layer.

This script demonstrates how to:
1. Initialize the database
2. Create test runs and add results
3. Add coverage data
4. Query performance metrics
5. Analyze historical trends
6. Generate dashboard data
"""

import sys
from datetime import datetime, timezone, timedelta
import random
import json
from pathlib import Path

# Import directly from modules
from database import TestDashboardDB, DatabaseError
from models import TestRun, TestResult, CoverageData, TestStatus, TestType
from queries import QueryOptimizer

def create_database(db_path: str = "test_dashboard.db", retention_days: int = 30) -> TestDashboardDB:
    """Create and initialize a test dashboard database instance."""
    from migrations.migration_manager import MigrationManager

    # Initialize with migrations
    migration_manager = MigrationManager(db_path)
    migration_manager.migrate()

    # Create database instance
    db = TestDashboardDB(db_path, retention_days)
    return db


def generate_sample_data(db):
    """Generate sample test data for demonstration."""
    print("🎯 Generating sample test data...")

    # Sample test files and names
    test_files = [
        "tests/test_models.py",
        "tests/test_api.py",
        "tests/test_auth.py",
        "tests/test_utils.py",
        "tests/integration/test_endpoints.py",
        "tests/integration/test_database.py",
    ]

    test_names = [
        "test_user_creation",
        "test_user_authentication",
        "test_password_validation",
        "test_api_response",
        "test_database_connection",
        "test_model_validation",
        "test_permissions",
        "test_error_handling",
        "test_data_integrity",
        "test_performance",
    ]

    # Generate test runs over the last 30 days
    for day_offset in range(30, 0, -1):
        run_date = datetime.now(timezone.utc) - timedelta(days=day_offset)

        # 1-3 runs per day
        for run_num in range(random.randint(1, 3)):
            # Create test run
            run_id = db.create_test_run(
                test_command=f"pytest tests/ -v",
                git_commit=f"abc{random.randint(1000, 9999)}",
                git_branch=random.choice(["main", "develop", "feature/auth", "bugfix/db"]),
                environment_info={
                    "python_version": "3.11.0",
                    "pytest_version": "7.4.0",
                    "os": "Linux",
                    "ci": random.choice([True, False])
                }
            )

            # Update started_at to historical date
            db.update_test_run(run_id, started_at=run_date)

            # Generate test results
            total_tests = random.randint(20, 50)
            passed_tests = 0
            failed_tests = 0
            skipped_tests = 0

            for i in range(total_tests):
                test_file = random.choice(test_files)
                test_name = random.choice(test_names)

                # Determine status with realistic distribution
                status_choice = random.random()
                if status_choice < 0.85:  # 85% pass rate
                    status = TestStatus.PASSED
                    passed_tests += 1
                elif status_choice < 0.92:  # 7% fail rate
                    status = TestStatus.FAILED
                    failed_tests += 1
                else:  # 8% skip rate
                    status = TestStatus.SKIPPED
                    skipped_tests += 1

                # Create test result
                test_result = TestResult(
                    test_name=f"{test_name}_{i}",
                    test_file=test_file,
                    test_class=f"Test{test_name.replace('test_', '').title()}",
                    test_method=test_name,
                    test_type=TestType.INTEGRATION if "integration" in test_file else TestType.UNIT,
                    status=status,
                    duration_seconds=random.uniform(0.01, 2.0),
                    error_message="AssertionError: Expected True, got False" if status == TestStatus.FAILED else None,
                    setup_duration=random.uniform(0.001, 0.1),
                    teardown_duration=random.uniform(0.001, 0.05),
                    assertions_count=random.randint(1, 10),
                    started_at=run_date + timedelta(seconds=i * 0.1),
                    finished_at=run_date + timedelta(seconds=i * 0.1 + random.uniform(0.01, 2.0)),
                )

                db.add_test_result(run_id, test_result)

            # Add coverage data
            for test_file in test_files:
                if random.random() < 0.7:  # 70% chance to have coverage data
                    source_file = test_file.replace("tests/", "src/").replace("test_", "")

                    coverage = CoverageData(
                        file_path=source_file,
                        total_lines=random.randint(50, 300),
                        covered_lines=random.randint(30, 280),
                        missing_lines=[random.randint(1, 300) for _ in range(random.randint(0, 10))],
                        branch_total=random.randint(5, 50),
                        branch_covered=random.randint(3, 45),
                        coverage_percentage=random.uniform(70.0, 95.0),
                    )
                    coverage.covered_lines = min(coverage.covered_lines, coverage.total_lines)
                    coverage.branch_covered = min(coverage.branch_covered, coverage.branch_total)

                    db.add_coverage_data(run_id, coverage)

            # Finish the test run
            total_duration = random.uniform(10.0, 120.0)
            final_status = TestStatus.PASSED if failed_tests == 0 else TestStatus.FAILED

            db.update_test_run(run_id,
                status=final_status,
                finished_at=run_date + timedelta(seconds=total_duration),
                total_tests=total_tests,
                passed_tests=passed_tests,
                failed_tests=failed_tests,
                skipped_tests=skipped_tests,
                duration_seconds=total_duration
            )

    print(f"✅ Generated sample data for {30} days")


def demonstrate_basic_operations(db):
    """Demonstrate basic database operations."""
    print("\n📊 Demonstrating Basic Operations")
    print("=" * 50)

    # Get recent test runs
    recent_runs = db.get_recent_test_runs(limit=5)
    print(f"📈 Recent test runs: {len(recent_runs)}")

    for run in recent_runs:
        print(f"  • {run.run_id[:8]}... - {run.status.value} - {run.total_tests} tests - {run.success_rate:.1f}% success")

    # Get dashboard summary
    summary = db.get_dashboard_summary()
    print(f"\n📋 Dashboard Summary:")
    print(f"  • Recent 24h runs: {summary['recent_24h']['total_runs']}")
    print(f"  • Average success rate: {summary['recent_24h']['avg_success_rate']:.1f}%")
    print(f"  • Total runs all time: {summary['overall']['total_runs']}")

    if recent_runs:
        run = recent_runs[0]
        print(f"\n🔍 Detailed analysis of run {run.run_id[:8]}...")

        # Get test results for this run
        results = db.get_test_results(run.run_id, limit=5)
        print(f"  • Test results: {len(results)} (showing first 5)")
        for result in results:
            print(f"    - {result.test_name}: {result.status.value} ({result.duration_seconds:.3f}s)")

        # Get coverage summary
        coverage = db.get_coverage_summary(run.run_id)
        if coverage:
            print(f"  • Coverage: {coverage['line_coverage']:.1f}% line coverage")
            print(f"    - Files: {coverage['file_count']}, Lines: {coverage['covered_lines']}/{coverage['total_lines']}")


def demonstrate_advanced_queries(db):
    """Demonstrate advanced query capabilities."""
    print("\n🚀 Demonstrating Advanced Queries")
    print("=" * 50)

    optimizer = QueryOptimizer(db._get_connection)

    # Get a recent run for analysis
    recent_runs = db.get_recent_test_runs(limit=1)
    if not recent_runs:
        print("No recent runs found for analysis")
        return

    run = recent_runs[0]
    run_id = run.run_id

    # Performance metrics
    performance = optimizer.get_test_run_performance_metrics(run_id)
    if performance:
        print(f"⚡ Performance Metrics for {run_id[:8]}...")
        if 'performance_summary' in performance:
            summary = performance['performance_summary']
            print(f"  • Total duration: {summary.get('total_duration', 0):.2f}s")
            print(f"  • Average test duration: {summary.get('avg_test_duration', 0):.3f}s")
            print(f"  • Files tested: {summary.get('files_tested', 0)}")

        if 'slowest_tests' in performance and performance['slowest_tests']:
            print(f"  • Slowest tests:")
            for test in performance['slowest_tests'][:3]:
                print(f"    - {test['test_name']}: {test['duration_seconds']:.3f}s")

    # Failure analysis
    failures = optimizer.get_failure_analysis(run_id)
    if failures and failures['summary']['total_failures'] > 0:
        print(f"\n❌ Failure Analysis for {run_id[:8]}...")
        summary = failures['summary']
        print(f"  • Total failures: {summary['total_failures']}")
        print(f"  • Unique error patterns: {summary['unique_error_patterns']}")
        print(f"  • Files affected: {summary['files_affected']}")

    # Historical comparison
    comparison = optimizer.get_historical_comparison(run_id, comparison_days=7)
    if comparison and 'comparison_summary' in comparison:
        print(f"\n📈 Historical Comparison (7 days):")
        comp = comparison['comparison_summary']
        print(f"  • Success rate change: {comp.get('success_rate_change', 0):+.1f}%")
        print(f"  • Duration change: {comp.get('duration_change', 0):+.1f}s")

    # Flaky tests
    flaky_tests = optimizer.get_flaky_tests(days=14, min_runs=3)
    if flaky_tests:
        print(f"\n🔄 Flaky Tests (last 14 days):")
        for test in flaky_tests[:3]:
            print(f"  • {test['test_name']}: {test['pass_rate']*100:.1f}% pass rate (flakiness: {test['flakiness_score']:.1f})")

    # Test suite health
    health = optimizer.get_test_suite_health()
    if health:
        print(f"\n🏥 Test Suite Health:")
        print(f"  • Health score: {health.get('health_score', 0)}/100")
        if 'recommendations' in health and health['recommendations']:
            print(f"  • Recommendations:")
            for rec in health['recommendations'][:3]:
                print(f"    - {rec['severity'].upper()}: {rec['message']}")


def demonstrate_trends_and_analytics(db):
    """Demonstrate trend analysis and analytics."""
    print("\n📊 Demonstrating Trends and Analytics")
    print("=" * 50)

    optimizer = QueryOptimizer(db._get_connection)

    # Get trend data
    trends = db.get_trend_data(days=7)
    if trends:
        print(f"📈 Test Trends (last 7 days):")
        for trend in trends[:5]:
            print(f"  • {trend['date']}: {trend['total_runs']} runs, {trend['avg_success_rate']:.1f}% success")

    # Coverage trends
    coverage_trends = optimizer.get_coverage_trends(days=14)
    if coverage_trends and coverage_trends['summary']['trend_days'] > 0:
        print(f"\n📋 Coverage Trends:")
        summary = coverage_trends['summary']
        print(f"  • Latest average coverage: {summary['latest_avg_coverage']:.1f}%")
        print(f"  • Files analyzed: {summary['files_analyzed']}")

        if coverage_trends['files_needing_attention']:
            print(f"  • Files needing attention:")
            for file_data in coverage_trends['files_needing_attention'][:3]:
                print(f"    - {file_data['file_path']}: {file_data['avg_coverage']:.1f}% average coverage")


def cleanup_demo(db):
    """Demonstrate data cleanup capabilities."""
    print("\n🧹 Demonstrating Data Cleanup")
    print("=" * 50)

    # Show current data count
    summary = db.get_dashboard_summary()
    total_runs = summary['overall']['total_runs']
    print(f"📊 Current total runs: {total_runs}")

    # Demonstrate cleanup (but don't actually delete the demo data)
    print(f"🗑️  Cleanup would remove data older than {db.retention_days} days")

    # Show migration status
    from migrations.migration_manager import MigrationManager
    migrator = MigrationManager(str(db.db_path))
    status = migrator.get_migration_status()

    print(f"\n🔄 Migration Status:")
    print(f"  • Current version: {status.get('current_version', 'None')}")
    print(f"  • Applied migrations: {status.get('applied_count', 0)}")
    print(f"  • Pending migrations: {status.get('pending_count', 0)}")
    print(f"  • Schema valid: {status.get('schema_valid', False)}")


def main():
    """Main demonstration function."""
    print("🎬 Django-Ollama Test Dashboard Database Demo")
    print("=" * 60)

    # Initialize database
    db_path = "demo_dashboard.db"
    db = create_database(db_path, retention_days=30)

    print(f"💾 Database initialized at: {Path(db_path).absolute()}")

    # Check if we need to generate sample data
    summary = db.get_dashboard_summary()
    if summary['overall']['total_runs'] == 0:
        generate_sample_data(db)

    # Run demonstrations
    demonstrate_basic_operations(db)
    demonstrate_advanced_queries(db)
    demonstrate_trends_and_analytics(db)
    cleanup_demo(db)

    print(f"\n✅ Demo completed!")
    print(f"📁 Database file: {Path(db_path).absolute()}")
    print(f"🔍 You can examine the database using: sqlite3 {db_path}")

    # Close database connection
    db.close()


if __name__ == "__main__":
    main()