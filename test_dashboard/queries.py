"""
Optimized query implementations for the django-ollama test dashboard.

Provides specialized query methods for common dashboard operations,
focusing on performance and efficient data retrieval patterns.
"""

import sqlite3
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple
import logging

from models import TestStatus, TestType

logger = logging.getLogger(__name__)


class QueryOptimizer:
    """
    High-performance query implementations for dashboard operations.

    Focuses on common access patterns with optimized SQL queries,
    proper indexing utilization, and minimal data transfer.
    """

    def __init__(self, db_connection_factory):
        """Initialize with database connection factory."""
        self.get_connection = db_connection_factory

    def get_test_run_performance_metrics(self, run_id: str) -> Dict[str, Any]:
        """Get detailed performance metrics for a specific test run."""
        try:
            conn = self.get_connection()

            # Get internal run_id and basic run info
            cursor = conn.execute("""
                SELECT id, total_tests, passed_tests, failed_tests,
                       duration_seconds, status, started_at
                FROM test_runs
                WHERE run_id = ?
            """, (run_id,))

            run_info = cursor.fetchone()
            if not run_info:
                return {}

            internal_run_id = run_info['id']

            # Test performance breakdown
            cursor = conn.execute("""
                SELECT
                    status,
                    COUNT(*) as count,
                    AVG(duration_seconds) as avg_duration,
                    MIN(duration_seconds) as min_duration,
                    MAX(duration_seconds) as max_duration,
                    SUM(duration_seconds) as total_duration
                FROM test_results
                WHERE run_id = ?
                GROUP BY status
            """, (internal_run_id,))

            status_breakdown = {row['status']: dict(row) for row in cursor.fetchall()}

            # Slowest tests
            cursor = conn.execute("""
                SELECT test_name, test_file, duration_seconds, status
                FROM test_results
                WHERE run_id = ?
                ORDER BY duration_seconds DESC
                LIMIT 10
            """, (internal_run_id,))

            slowest_tests = [dict(row) for row in cursor.fetchall()]

            # Test type distribution
            cursor = conn.execute("""
                SELECT
                    test_type,
                    COUNT(*) as count,
                    AVG(duration_seconds) as avg_duration,
                    COUNT(CASE WHEN status = 'PASSED' THEN 1 END) as passed,
                    COUNT(CASE WHEN status = 'FAILED' THEN 1 END) as failed
                FROM test_results
                WHERE run_id = ?
                GROUP BY test_type
            """, (internal_run_id,))

            type_breakdown = {row['test_type']: dict(row) for row in cursor.fetchall()}

            # File-based performance (top files by test count and duration)
            cursor = conn.execute("""
                SELECT
                    test_file,
                    COUNT(*) as test_count,
                    SUM(duration_seconds) as total_duration,
                    AVG(duration_seconds) as avg_duration,
                    COUNT(CASE WHEN status = 'PASSED' THEN 1 END) as passed,
                    COUNT(CASE WHEN status = 'FAILED' THEN 1 END) as failed
                FROM test_results
                WHERE run_id = ?
                GROUP BY test_file
                ORDER BY total_duration DESC
                LIMIT 15
            """, (internal_run_id,))

            file_breakdown = [dict(row) for row in cursor.fetchall()]

            return {
                'run_info': dict(run_info),
                'status_breakdown': status_breakdown,
                'slowest_tests': slowest_tests,
                'type_breakdown': type_breakdown,
                'file_breakdown': file_breakdown,
                'performance_summary': {
                    'total_duration': sum(s.get('total_duration', 0) for s in status_breakdown.values()),
                    'avg_test_duration': sum(s.get('avg_duration', 0) * s.get('count', 0) for s in status_breakdown.values()) / max(sum(s.get('count', 0) for s in status_breakdown.values()), 1),
                    'files_tested': len(file_breakdown),
                }
            }

        except Exception as e:
            logger.error(f"Failed to get performance metrics for {run_id}: {e}")
            return {}

    def get_failure_analysis(self, run_id: str) -> Dict[str, Any]:
        """Analyze test failures with error categorization and patterns."""
        try:
            conn = self.get_connection()

            # Get internal run_id
            cursor = conn.execute("SELECT id FROM test_runs WHERE run_id = ?", (run_id,))
            row = cursor.fetchone()
            if not row:
                return {}

            internal_run_id = row['id']

            # Failed tests with error details
            cursor = conn.execute("""
                SELECT test_name, test_file, test_class, test_method,
                       error_message, error_traceback, duration_seconds
                FROM test_results
                WHERE run_id = ? AND status = 'FAILED'
                ORDER BY duration_seconds DESC
            """, (internal_run_id,))

            failed_tests = [dict(row) for row in cursor.fetchall()]

            # Error pattern analysis
            error_patterns = {}
            for test in failed_tests:
                if test['error_message']:
                    # Simple error categorization
                    error_key = test['error_message'].split('\n')[0][:100]  # First line, truncated
                    if error_key not in error_patterns:
                        error_patterns[error_key] = {
                            'count': 0,
                            'tests': [],
                            'files': set()
                        }
                    error_patterns[error_key]['count'] += 1
                    error_patterns[error_key]['tests'].append(test['test_name'])
                    error_patterns[error_key]['files'].add(test['test_file'])

            # Convert sets to lists for JSON serialization
            for pattern in error_patterns.values():
                pattern['files'] = list(pattern['files'])

            # Files with most failures
            cursor = conn.execute("""
                SELECT
                    test_file,
                    COUNT(*) as failure_count,
                    GROUP_CONCAT(test_name, ', ') as failed_tests
                FROM test_results
                WHERE run_id = ? AND status = 'FAILED'
                GROUP BY test_file
                ORDER BY failure_count DESC
                LIMIT 10
            """, (internal_run_id,))

            files_with_failures = [dict(row) for row in cursor.fetchall()]

            return {
                'failed_tests': failed_tests,
                'error_patterns': error_patterns,
                'files_with_failures': files_with_failures,
                'summary': {
                    'total_failures': len(failed_tests),
                    'unique_error_patterns': len(error_patterns),
                    'files_affected': len(files_with_failures),
                }
            }

        except Exception as e:
            logger.error(f"Failed to analyze failures for {run_id}: {e}")
            return {}

    def get_historical_comparison(self, run_id: str, comparison_days: int = 7) -> Dict[str, Any]:
        """Compare current run with historical data for the same test suite."""
        try:
            conn = self.get_connection()

            # Get current run info
            cursor = conn.execute("""
                SELECT id, git_branch, total_tests, passed_tests, failed_tests,
                       duration_seconds, started_at
                FROM test_runs
                WHERE run_id = ?
            """, (run_id,))

            current_run = cursor.fetchone()
            if not current_run:
                return {}

            # Get historical runs for comparison (same branch if available)
            start_date = datetime.now(timezone.utc) - timedelta(days=comparison_days)

            comparison_query = """
                SELECT id, run_id, total_tests, passed_tests, failed_tests,
                       duration_seconds, started_at, status
                FROM test_runs
                WHERE started_at >= ? AND id != ?
            """
            params = [start_date, current_run['id']]

            if current_run['git_branch']:
                comparison_query += " AND git_branch = ?"
                params.append(current_run['git_branch'])

            comparison_query += " ORDER BY started_at DESC LIMIT 20"

            cursor = conn.execute(comparison_query, params)
            historical_runs = [dict(row) for row in cursor.fetchall()]

            if not historical_runs:
                return {'current_run': dict(current_run), 'historical_runs': []}

            # Calculate trends and comparisons
            current_success_rate = (current_run['passed_tests'] / max(current_run['total_tests'], 1)) * 100

            historical_success_rates = []
            historical_durations = []

            for run in historical_runs:
                if run['total_tests'] > 0:
                    success_rate = (run['passed_tests'] / run['total_tests']) * 100
                    historical_success_rates.append(success_rate)
                    historical_durations.append(run['duration_seconds'])

            avg_historical_success_rate = sum(historical_success_rates) / len(historical_success_rates) if historical_success_rates else 0
            avg_historical_duration = sum(historical_durations) / len(historical_durations) if historical_durations else 0

            # Performance comparison for individual tests
            internal_run_id = current_run['id']

            cursor = conn.execute("""
                WITH current_tests AS (
                    SELECT test_name, duration_seconds, status
                    FROM test_results
                    WHERE run_id = ?
                ),
                historical_tests AS (
                    SELECT tr.test_name, AVG(tr.duration_seconds) as avg_duration,
                           COUNT(*) as run_count
                    FROM test_results tr
                    JOIN test_runs runs ON tr.run_id = runs.id
                    WHERE runs.started_at >= ?
                          AND runs.id != ?
                          AND tr.status = 'PASSED'
                    GROUP BY tr.test_name
                    HAVING COUNT(*) >= 2
                )
                SELECT
                    ct.test_name,
                    ct.duration_seconds as current_duration,
                    ct.status as current_status,
                    ht.avg_duration as avg_historical_duration,
                    ht.run_count as historical_run_count,
                    CASE
                        WHEN ht.avg_duration > 0
                        THEN ((ct.duration_seconds - ht.avg_duration) / ht.avg_duration) * 100
                        ELSE 0
                    END as performance_change_pct
                FROM current_tests ct
                JOIN historical_tests ht ON ct.test_name = ht.test_name
                WHERE ct.status = 'PASSED'
                ORDER BY performance_change_pct DESC
                LIMIT 20
            """, (internal_run_id, start_date, current_run['id']))

            test_performance_comparison = [dict(row) for row in cursor.fetchall()]

            return {
                'current_run': dict(current_run),
                'historical_runs': historical_runs,
                'comparison_summary': {
                    'success_rate_change': current_success_rate - avg_historical_success_rate,
                    'duration_change': current_run['duration_seconds'] - avg_historical_duration,
                    'current_success_rate': current_success_rate,
                    'avg_historical_success_rate': avg_historical_success_rate,
                    'current_duration': current_run['duration_seconds'],
                    'avg_historical_duration': avg_historical_duration,
                },
                'test_performance_comparison': test_performance_comparison,
            }

        except Exception as e:
            logger.error(f"Failed to get historical comparison for {run_id}: {e}")
            return {}

    def get_coverage_trends(self, days: int = 30) -> Dict[str, Any]:
        """Get coverage trends over time with file-level analysis."""
        try:
            conn = self.get_connection()
            start_date = datetime.now(timezone.utc) - timedelta(days=days)

            # Overall coverage trends by date
            cursor = conn.execute("""
                SELECT
                    DATE(tr.started_at) as date,
                    AVG(cd.coverage_percentage) as avg_coverage,
                    MIN(cd.coverage_percentage) as min_coverage,
                    MAX(cd.coverage_percentage) as max_coverage,
                    COUNT(DISTINCT cd.file_path) as files_covered,
                    SUM(cd.total_lines) as total_lines,
                    SUM(cd.covered_lines) as covered_lines
                FROM coverage_data cd
                JOIN test_runs tr ON cd.run_id = tr.id
                WHERE tr.started_at >= ?
                GROUP BY DATE(tr.started_at)
                ORDER BY date DESC
            """, (start_date,))

            daily_trends = [dict(row) for row in cursor.fetchall()]

            # File-level coverage analysis (most/least covered files)
            cursor = conn.execute("""
                SELECT
                    cd.file_path,
                    AVG(cd.coverage_percentage) as avg_coverage,
                    MIN(cd.coverage_percentage) as min_coverage,
                    MAX(cd.coverage_percentage) as max_coverage,
                    COUNT(*) as measurement_count,
                    AVG(cd.total_lines) as avg_total_lines
                FROM coverage_data cd
                JOIN test_runs tr ON cd.run_id = tr.id
                WHERE tr.started_at >= ?
                GROUP BY cd.file_path
                HAVING COUNT(*) >= 2
                ORDER BY avg_coverage ASC
                LIMIT 20
            """, (start_date,))

            files_needing_attention = [dict(row) for row in cursor.fetchall()]

            # Best covered files
            cursor = conn.execute("""
                SELECT
                    cd.file_path,
                    AVG(cd.coverage_percentage) as avg_coverage,
                    COUNT(*) as measurement_count,
                    AVG(cd.total_lines) as avg_total_lines
                FROM coverage_data cd
                JOIN test_runs tr ON cd.run_id = tr.id
                WHERE tr.started_at >= ?
                GROUP BY cd.file_path
                HAVING COUNT(*) >= 2 AND AVG(cd.coverage_percentage) > 90
                ORDER BY avg_coverage DESC
                LIMIT 10
            """, (start_date,))

            well_covered_files = [dict(row) for row in cursor.fetchall()]

            return {
                'daily_trends': daily_trends,
                'files_needing_attention': files_needing_attention,
                'well_covered_files': well_covered_files,
                'summary': {
                    'trend_days': len(daily_trends),
                    'latest_avg_coverage': daily_trends[0]['avg_coverage'] if daily_trends else 0,
                    'files_analyzed': len(files_needing_attention) + len(well_covered_files),
                }
            }

        except Exception as e:
            logger.error(f"Failed to get coverage trends: {e}")
            return {}

    def get_flaky_tests(self, days: int = 14, min_runs: int = 5) -> List[Dict[str, Any]]:
        """Identify potentially flaky tests based on inconsistent results."""
        try:
            conn = self.get_connection()
            start_date = datetime.now(timezone.utc) - timedelta(days=days)

            cursor = conn.execute("""
                SELECT
                    tr.test_name,
                    tr.test_file,
                    COUNT(*) as total_runs,
                    COUNT(CASE WHEN tr.status = 'PASSED' THEN 1 END) as passed_count,
                    COUNT(CASE WHEN tr.status = 'FAILED' THEN 1 END) as failed_count,
                    CAST(COUNT(CASE WHEN tr.status = 'PASSED' THEN 1 END) AS FLOAT) / COUNT(*) as pass_rate,
                    AVG(tr.duration_seconds) as avg_duration,
                    MIN(tr.duration_seconds) as min_duration,
                    MAX(tr.duration_seconds) as max_duration,
                    GROUP_CONCAT(DISTINCT tr.status) as seen_statuses
                FROM test_results tr
                JOIN test_runs runs ON tr.run_id = runs.id
                WHERE runs.started_at >= ?
                GROUP BY tr.test_name, tr.test_file
                HAVING COUNT(*) >= ?
                       AND COUNT(DISTINCT tr.status) > 1
                       AND pass_rate > 0.1 AND pass_rate < 0.9
                ORDER BY (MAX(tr.duration_seconds) - MIN(tr.duration_seconds)) DESC,
                         ABS(0.5 - pass_rate) ASC
                LIMIT 50
            """, (start_date, min_runs))

            flaky_tests = []
            for row in cursor.fetchall():
                test_data = dict(row)

                # Calculate flakiness score (0-100, higher is more flaky)
                pass_rate = test_data['pass_rate']
                duration_variance = (test_data['max_duration'] - test_data['min_duration']) / max(test_data['avg_duration'], 0.001)

                # Score based on how close pass rate is to 50% and duration variance
                flakiness_score = (1 - abs(pass_rate - 0.5) * 2) * 50 + min(duration_variance * 10, 50)
                test_data['flakiness_score'] = round(flakiness_score, 1)

                flaky_tests.append(test_data)

            return flaky_tests

        except Exception as e:
            logger.error(f"Failed to identify flaky tests: {e}")
            return []

    def get_test_suite_health(self) -> Dict[str, Any]:
        """Get overall test suite health metrics and recommendations."""
        try:
            conn = self.get_connection()

            # Recent test runs health (last 7 days)
            week_ago = datetime.now(timezone.utc) - timedelta(days=7)

            cursor = conn.execute("""
                SELECT
                    COUNT(*) as total_runs,
                    COUNT(CASE WHEN status = 'PASSED' THEN 1 END) as passed_runs,
                    COUNT(CASE WHEN status = 'FAILED' THEN 1 END) as failed_runs,
                    COUNT(CASE WHEN status = 'RUNNING' THEN 1 END) as running_runs,
                    AVG(duration_seconds) as avg_duration,
                    MIN(duration_seconds) as min_duration,
                    MAX(duration_seconds) as max_duration,
                    AVG(CAST(passed_tests AS FLOAT) / NULLIF(total_tests, 0) * 100) as avg_success_rate
                FROM test_runs
                WHERE started_at >= ?
            """, (week_ago,))

            recent_health = cursor.fetchone()

            # Test execution trends
            cursor = conn.execute("""
                SELECT
                    DATE(started_at) as date,
                    COUNT(*) as runs,
                    AVG(duration_seconds) as avg_duration,
                    AVG(CAST(passed_tests AS FLOAT) / NULLIF(total_tests, 0) * 100) as avg_success_rate
                FROM test_runs
                WHERE started_at >= ?
                GROUP BY DATE(started_at)
                ORDER BY date DESC
            """, (week_ago,))

            daily_health = [dict(row) for row in cursor.fetchall()]

            # Slowest growing test files (by average duration)
            cursor = conn.execute("""
                SELECT
                    tr.test_file,
                    COUNT(*) as test_count,
                    AVG(tr.duration_seconds) as avg_duration,
                    SUM(tr.duration_seconds) as total_duration,
                    COUNT(CASE WHEN tr.status = 'FAILED' THEN 1 END) as failure_count
                FROM test_results tr
                JOIN test_runs runs ON tr.run_id = runs.id
                WHERE runs.started_at >= ?
                GROUP BY tr.test_file
                HAVING COUNT(*) >= 5
                ORDER BY avg_duration DESC
                LIMIT 15
            """, (week_ago,))

            slow_test_files = [dict(row) for row in cursor.fetchall()]

            # Generate health recommendations
            recommendations = []

            if recent_health:
                avg_success_rate = recent_health['avg_success_rate'] or 0
                avg_duration = recent_health['avg_duration'] or 0

                if avg_success_rate < 90:
                    recommendations.append({
                        'type': 'success_rate',
                        'severity': 'high' if avg_success_rate < 80 else 'medium',
                        'message': f"Success rate is {avg_success_rate:.1f}%. Consider investigating frequent failures.",
                    })

                if avg_duration > 300:  # 5 minutes
                    recommendations.append({
                        'type': 'performance',
                        'severity': 'medium',
                        'message': f"Average test duration is {avg_duration:.1f}s. Consider optimizing slow tests.",
                    })

                if len(slow_test_files) > 0:
                    slowest_file = slow_test_files[0]
                    if slowest_file['avg_duration'] > 60:
                        recommendations.append({
                            'type': 'slow_tests',
                            'severity': 'medium',
                            'message': f"File '{slowest_file['test_file']}' has slow tests averaging {slowest_file['avg_duration']:.1f}s.",
                        })

            return {
                'recent_health': dict(recent_health) if recent_health else {},
                'daily_trends': daily_health,
                'slow_test_files': slow_test_files,
                'recommendations': recommendations,
                'health_score': self._calculate_health_score(recent_health, daily_health),
            }

        except Exception as e:
            logger.error(f"Failed to get test suite health: {e}")
            return {}

    def _calculate_health_score(self, recent_health: Optional[sqlite3.Row],
                              daily_trends: List[Dict[str, Any]]) -> int:
        """Calculate a health score from 0-100 based on various metrics."""
        if not recent_health:
            return 0

        score = 100

        # Success rate impact (40% of score)
        success_rate = recent_health['avg_success_rate'] or 0
        if success_rate < 50:
            score -= 40
        elif success_rate < 75:
            score -= 20
        elif success_rate < 90:
            score -= 10

        # Duration consistency (30% of score)
        avg_duration = recent_health['avg_duration'] or 0
        if avg_duration > 600:  # 10 minutes
            score -= 30
        elif avg_duration > 300:  # 5 minutes
            score -= 15

        # Run frequency and stability (30% of score)
        total_runs = recent_health['total_runs'] or 0
        if total_runs < 5:  # Less than 5 runs in a week
            score -= 20

        running_runs = recent_health['running_runs'] or 0
        if running_runs > 2:  # Too many stuck runs
            score -= 10

        return max(0, min(100, score))