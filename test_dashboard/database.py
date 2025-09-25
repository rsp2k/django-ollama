"""
Main database operations layer for the django-ollama test dashboard.

Provides high-level database operations with connection pooling, transaction management,
and optimized queries for dashboard data retrieval.
"""

import sqlite3
import threading
import json
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple, Union
import uuid
import logging

from models import (
    TestRun, TestResult, CoverageData, TestMetrics,
    TestStatus, TestType, SQL_SCHEMA
)

logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    """Custom exception for database operations."""
    pass


class TestDashboardDB:
    """
    High-performance SQLite database manager for test dashboard.

    Features:
    - Connection pooling with thread safety
    - Automatic transaction management
    - Optimized queries for dashboard operations
    - Data retention and cleanup mechanisms
    """

    def __init__(self, db_path: str = "test_dashboard.db", retention_days: int = 30):
        self.db_path = Path(db_path)
        self.retention_days = retention_days
        self._local = threading.local()
        self._init_database()

    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection with optimizations."""
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            conn = sqlite3.connect(
                str(self.db_path),
                timeout=30.0,
                check_same_thread=False
            )

            # SQLite optimizations
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA cache_size=10000")
            conn.execute("PRAGMA temp_store=MEMORY")
            conn.execute("PRAGMA mmap_size=268435456")  # 256MB
            conn.execute("PRAGMA foreign_keys=ON")

            # Row factory for dict-like access
            conn.row_factory = sqlite3.Row
            self._local.connection = conn

        return self._local.connection

    @contextmanager
    def _transaction(self):
        """Context manager for database transactions with rollback support."""
        conn = self._get_connection()
        try:
            conn.execute("BEGIN IMMEDIATE")
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    def _init_database(self):
        """Initialize database with schema and indexes via migrations."""
        try:
            # Use migration manager to ensure proper schema versioning
            from migrations.migration_manager import MigrationManager
            migrations_dir = Path(__file__).parent / "migrations"
            migrator = MigrationManager(str(self.db_path), str(migrations_dir))
            success = migrator.migrate()

            if not success:
                raise DatabaseError("Migration failed")

            logger.info(f"Database initialized at {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise DatabaseError(f"Database initialization failed: {e}")

    def create_test_run(self, test_command: str = "", git_commit: str = None,
                       git_branch: str = None, environment_info: Dict[str, Any] = None) -> str:
        """Create a new test run and return its run_id."""
        run_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        environment_info = environment_info or {}

        test_run = TestRun(
            run_id=run_id,
            started_at=now,
            test_command=test_command,
            git_commit=git_commit,
            git_branch=git_branch,
            environment_info=environment_info,
            created_at=now
        )

        try:
            with self._transaction() as conn:
                conn.execute("""
                    INSERT INTO test_runs (
                        run_id, started_at, status, test_command, environment_info,
                        git_commit, git_branch, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    test_run.run_id, test_run.started_at, test_run.status.value,
                    test_run.test_command, json.dumps(test_run.environment_info),
                    test_run.git_commit, test_run.git_branch, test_run.created_at
                ))

            logger.info(f"Created test run {run_id}")
            return run_id

        except Exception as e:
            logger.error(f"Failed to create test run: {e}")
            raise DatabaseError(f"Failed to create test run: {e}")

    def update_test_run(self, run_id: str, **updates) -> bool:
        """Update test run with provided fields."""
        if not updates:
            return True

        # Build dynamic update query
        set_clauses = []
        values = []

        for field, value in updates.items():
            if field == 'status' and isinstance(value, TestStatus):
                value = value.value
            elif field == 'environment_info' and isinstance(value, dict):
                value = json.dumps(value)
            elif field in ['started_at', 'finished_at'] and isinstance(value, datetime):
                pass  # Keep datetime as is

            set_clauses.append(f"{field} = ?")
            values.append(value)

        values.append(run_id)

        try:
            with self._transaction() as conn:
                cursor = conn.execute(f"""
                    UPDATE test_runs
                    SET {', '.join(set_clauses)}
                    WHERE run_id = ?
                """, values)

                return cursor.rowcount > 0

        except Exception as e:
            logger.error(f"Failed to update test run {run_id}: {e}")
            raise DatabaseError(f"Failed to update test run: {e}")

    def get_test_run(self, run_id: str) -> Optional[TestRun]:
        """Retrieve test run by run_id."""
        try:
            conn = self._get_connection()
            cursor = conn.execute("""
                SELECT * FROM test_runs WHERE run_id = ?
            """, (run_id,))

            row = cursor.fetchone()
            if not row:
                return None

            return self._row_to_test_run(row)

        except Exception as e:
            logger.error(f"Failed to get test run {run_id}: {e}")
            raise DatabaseError(f"Failed to get test run: {e}")

    def get_recent_test_runs(self, limit: int = 50, status: TestStatus = None) -> List[TestRun]:
        """Get recent test runs with optional status filter."""
        try:
            conn = self._get_connection()
            query = "SELECT * FROM test_runs"
            params = []

            if status:
                query += " WHERE status = ?"
                params.append(status.value)

            query += " ORDER BY started_at DESC LIMIT ?"
            params.append(limit)

            cursor = conn.execute(query, params)
            return [self._row_to_test_run(row) for row in cursor.fetchall()]

        except Exception as e:
            logger.error(f"Failed to get recent test runs: {e}")
            raise DatabaseError(f"Failed to get recent test runs: {e}")

    def add_test_result(self, run_id: str, test_result: TestResult) -> int:
        """Add a test result to the database."""
        try:
            # Get the internal run_id (database ID)
            conn = self._get_connection()
            cursor = conn.execute("SELECT id FROM test_runs WHERE run_id = ?", (run_id,))
            row = cursor.fetchone()
            if not row:
                raise DatabaseError(f"Test run {run_id} not found")

            internal_run_id = row['id']
            test_result.run_id = internal_run_id

            with self._transaction() as conn:
                cursor = conn.execute("""
                    INSERT INTO test_results (
                        run_id, test_name, test_file, test_class, test_method,
                        test_type, status, duration_seconds, error_message, error_traceback,
                        setup_duration, teardown_duration, assertions_count,
                        started_at, finished_at, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    test_result.run_id, test_result.test_name, test_result.test_file,
                    test_result.test_class, test_result.test_method, test_result.test_type.value,
                    test_result.status.value, test_result.duration_seconds, test_result.error_message,
                    test_result.error_traceback, test_result.setup_duration, test_result.teardown_duration,
                    test_result.assertions_count, test_result.started_at, test_result.finished_at,
                    test_result.created_at
                ))

                return cursor.lastrowid

        except Exception as e:
            logger.error(f"Failed to add test result: {e}")
            raise DatabaseError(f"Failed to add test result: {e}")

    def get_test_results(self, run_id: str, status: TestStatus = None,
                        limit: int = None, offset: int = 0) -> List[TestResult]:
        """Get test results for a run with optional filtering and pagination."""
        try:
            conn = self._get_connection()

            # Get internal run_id
            cursor = conn.execute("SELECT id FROM test_runs WHERE run_id = ?", (run_id,))
            row = cursor.fetchone()
            if not row:
                return []

            internal_run_id = row['id']

            query = "SELECT * FROM test_results WHERE run_id = ?"
            params = [internal_run_id]

            if status:
                query += " AND status = ?"
                params.append(status.value)

            query += " ORDER BY started_at DESC"

            if limit:
                query += " LIMIT ? OFFSET ?"
                params.extend([limit, offset])

            cursor = conn.execute(query, params)
            return [self._row_to_test_result(row) for row in cursor.fetchall()]

        except Exception as e:
            logger.error(f"Failed to get test results: {e}")
            raise DatabaseError(f"Failed to get test results: {e}")

    def add_coverage_data(self, run_id: str, coverage_data: CoverageData) -> int:
        """Add coverage data for a test run."""
        try:
            # Get the internal run_id
            conn = self._get_connection()
            cursor = conn.execute("SELECT id FROM test_runs WHERE run_id = ?", (run_id,))
            row = cursor.fetchone()
            if not row:
                raise DatabaseError(f"Test run {run_id} not found")

            internal_run_id = row['id']
            coverage_data.run_id = internal_run_id

            with self._transaction() as conn:
                cursor = conn.execute("""
                    INSERT INTO coverage_data (
                        run_id, file_path, total_lines, covered_lines, missing_lines,
                        excluded_lines, branch_total, branch_covered, missing_branches,
                        coverage_percentage, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    coverage_data.run_id, coverage_data.file_path, coverage_data.total_lines,
                    coverage_data.covered_lines, json.dumps(coverage_data.missing_lines),
                    json.dumps(coverage_data.excluded_lines), coverage_data.branch_total,
                    coverage_data.branch_covered, json.dumps(coverage_data.missing_branches),
                    coverage_data.coverage_percentage, coverage_data.created_at
                ))

                return cursor.lastrowid

        except Exception as e:
            logger.error(f"Failed to add coverage data: {e}")
            raise DatabaseError(f"Failed to add coverage data: {e}")

    def get_coverage_summary(self, run_id: str) -> Dict[str, Any]:
        """Get coverage summary for a test run."""
        try:
            conn = self._get_connection()

            # Get internal run_id
            cursor = conn.execute("SELECT id FROM test_runs WHERE run_id = ?", (run_id,))
            row = cursor.fetchone()
            if not row:
                return {}

            internal_run_id = row['id']

            cursor = conn.execute("""
                SELECT
                    COUNT(*) as file_count,
                    SUM(total_lines) as total_lines,
                    SUM(covered_lines) as covered_lines,
                    AVG(coverage_percentage) as average_coverage,
                    MIN(coverage_percentage) as min_coverage,
                    MAX(coverage_percentage) as max_coverage
                FROM coverage_data
                WHERE run_id = ?
            """, (internal_run_id,))

            row = cursor.fetchone()
            if not row or not row['file_count']:
                return {}

            return {
                'file_count': row['file_count'],
                'total_lines': row['total_lines'] or 0,
                'covered_lines': row['covered_lines'] or 0,
                'line_coverage': (row['covered_lines'] / row['total_lines'] * 100) if row['total_lines'] else 0,
                'average_coverage': row['average_coverage'] or 0,
                'min_coverage': row['min_coverage'] or 0,
                'max_coverage': row['max_coverage'] or 0,
            }

        except Exception as e:
            logger.error(f"Failed to get coverage summary: {e}")
            return {}

    def get_dashboard_summary(self) -> Dict[str, Any]:
        """Get high-level dashboard statistics."""
        try:
            conn = self._get_connection()

            # Recent runs (last 24 hours)
            yesterday = datetime.now(timezone.utc) - timedelta(days=1)
            cursor = conn.execute("""
                SELECT
                    COUNT(*) as total_runs,
                    COUNT(CASE WHEN status = 'PASSED' THEN 1 END) as passed_runs,
                    COUNT(CASE WHEN status = 'FAILED' THEN 1 END) as failed_runs,
                    COUNT(CASE WHEN status = 'RUNNING' THEN 1 END) as running_runs,
                    AVG(duration_seconds) as avg_duration,
                    AVG(CAST(passed_tests AS FLOAT) / NULLIF(total_tests, 0) * 100) as avg_success_rate
                FROM test_runs
                WHERE started_at >= ?
            """, (yesterday,))

            recent_stats = cursor.fetchone()

            # Overall statistics
            cursor = conn.execute("""
                SELECT
                    COUNT(*) as total_runs_all_time,
                    MAX(started_at) as last_run_time,
                    AVG(duration_seconds) as overall_avg_duration
                FROM test_runs
            """)

            overall_stats = cursor.fetchone()

            # Currently running tests
            cursor = conn.execute("""
                SELECT run_id, started_at, test_command
                FROM test_runs
                WHERE status = 'RUNNING'
                ORDER BY started_at DESC
            """)

            running_tests = [dict(row) for row in cursor.fetchall()]

            return {
                'recent_24h': {
                    'total_runs': recent_stats['total_runs'] or 0,
                    'passed_runs': recent_stats['passed_runs'] or 0,
                    'failed_runs': recent_stats['failed_runs'] or 0,
                    'running_runs': recent_stats['running_runs'] or 0,
                    'avg_duration': recent_stats['avg_duration'] or 0,
                    'avg_success_rate': recent_stats['avg_success_rate'] or 0,
                },
                'overall': {
                    'total_runs': overall_stats['total_runs_all_time'] or 0,
                    'last_run_time': overall_stats['last_run_time'],
                    'avg_duration': overall_stats['overall_avg_duration'] or 0,
                },
                'running_tests': running_tests,
            }

        except Exception as e:
            logger.error(f"Failed to get dashboard summary: {e}")
            return {}

    def cleanup_old_data(self):
        """Remove test data older than retention_days."""
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=self.retention_days)

            with self._transaction() as conn:
                # Delete old test runs (CASCADE will handle related data)
                cursor = conn.execute("""
                    DELETE FROM test_runs WHERE started_at < ?
                """, (cutoff_date,))

                deleted_runs = cursor.rowcount

                # Update metrics if we deleted anything
                if deleted_runs > 0:
                    # Clean up orphaned metrics
                    conn.execute("""
                        DELETE FROM test_metrics
                        WHERE date < ? AND date NOT IN (
                            SELECT DISTINCT DATE(started_at) FROM test_runs
                        )
                    """, (cutoff_date.date(),))

            logger.info(f"Cleaned up {deleted_runs} old test runs")
            return deleted_runs

        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")
            return 0

    def get_trend_data(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get trend data for the specified number of days."""
        try:
            start_date = datetime.now(timezone.utc) - timedelta(days=days)

            conn = self._get_connection()
            cursor = conn.execute("""
                SELECT
                    DATE(started_at) as date,
                    COUNT(*) as total_runs,
                    COUNT(CASE WHEN status = 'PASSED' THEN 1 END) as passed_runs,
                    COUNT(CASE WHEN status = 'FAILED' THEN 1 END) as failed_runs,
                    AVG(duration_seconds) as avg_duration,
                    AVG(CAST(passed_tests AS FLOAT) / NULLIF(total_tests, 0) * 100) as avg_success_rate,
                    SUM(total_tests) as total_tests
                FROM test_runs
                WHERE started_at >= ?
                GROUP BY DATE(started_at)
                ORDER BY date DESC
            """, (start_date,))

            return [dict(row) for row in cursor.fetchall()]

        except Exception as e:
            logger.error(f"Failed to get trend data: {e}")
            return []

    def _row_to_test_run(self, row: sqlite3.Row) -> TestRun:
        """Convert database row to TestRun object."""
        return TestRun(
            id=row['id'],
            run_id=row['run_id'],
            started_at=datetime.fromisoformat(row['started_at'].replace('Z', '+00:00')) if row['started_at'] else None,
            finished_at=datetime.fromisoformat(row['finished_at'].replace('Z', '+00:00')) if row['finished_at'] else None,
            status=TestStatus(row['status']),
            total_tests=row['total_tests'],
            passed_tests=row['passed_tests'],
            failed_tests=row['failed_tests'],
            skipped_tests=row['skipped_tests'],
            error_tests=row['error_tests'],
            duration_seconds=row['duration_seconds'],
            test_command=row['test_command'],
            environment_info=json.loads(row['environment_info']) if row['environment_info'] else {},
            git_commit=row['git_commit'],
            git_branch=row['git_branch'],
            created_at=datetime.fromisoformat(row['created_at'].replace('Z', '+00:00')) if row['created_at'] else None,
        )

    def _row_to_test_result(self, row: sqlite3.Row) -> TestResult:
        """Convert database row to TestResult object."""
        return TestResult(
            id=row['id'],
            run_id=row['run_id'],
            test_name=row['test_name'],
            test_file=row['test_file'],
            test_class=row['test_class'],
            test_method=row['test_method'],
            test_type=TestType(row['test_type']),
            status=TestStatus(row['status']),
            duration_seconds=row['duration_seconds'],
            error_message=row['error_message'],
            error_traceback=row['error_traceback'],
            setup_duration=row['setup_duration'],
            teardown_duration=row['teardown_duration'],
            assertions_count=row['assertions_count'],
            started_at=datetime.fromisoformat(row['started_at'].replace('Z', '+00:00')) if row['started_at'] else None,
            finished_at=datetime.fromisoformat(row['finished_at'].replace('Z', '+00:00')) if row['finished_at'] else None,
            created_at=datetime.fromisoformat(row['created_at'].replace('Z', '+00:00')) if row['created_at'] else None,
        )

    def close(self):
        """Close database connection."""
        if hasattr(self._local, 'connection') and self._local.connection:
            self._local.connection.close()
            self._local.connection = None