"""
Django-Ollama Test Dashboard Database Layer

A comprehensive SQLite-based database infrastructure for tracking test results,
coverage data, and historical metrics with high performance and reliability.

Key Components:
- models.py: Data models and schema definitions
- database.py: Main database operations layer
- queries.py: Optimized query implementations
- migrations/: Schema versioning and migration system

Features:
- Thread-safe connection pooling
- Optimized queries with proper indexing
- Historical data analysis and trends
- Automated data retention policies
- Comprehensive test result tracking
- Real-time dashboard data support
"""

from .database import TestDashboardDB, DatabaseError
from .models import TestRun, TestResult, CoverageData, TestMetrics, TestStatus, TestType
from .queries import QueryOptimizer
from .migrations.migration_manager import MigrationManager

__version__ = "1.0.0"

__all__ = [
    'TestDashboardDB',
    'DatabaseError',
    'TestRun',
    'TestResult',
    'CoverageData',
    'TestMetrics',
    'TestStatus',
    'TestType',
    'QueryOptimizer',
    'MigrationManager',
]


def create_database(db_path: str = "test_dashboard.db", retention_days: int = 30) -> TestDashboardDB:
    """
    Create and initialize a test dashboard database instance.

    Args:
        db_path: Path to the SQLite database file
        retention_days: Number of days to retain test data

    Returns:
        Initialized TestDashboardDB instance
    """
    # Initialize with migrations
    migration_manager = MigrationManager(db_path)
    migration_manager.migrate()

    # Create database instance
    db = TestDashboardDB(db_path, retention_days)
    return db