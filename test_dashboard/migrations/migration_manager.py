"""
Database migration management for the django-ollama test dashboard.

Provides schema versioning, migration execution, and rollback capabilities
for the SQLite database.
"""

import sqlite3
from pathlib import Path
from typing import List, Tuple, Optional
from datetime import datetime, timezone
import logging
import re

logger = logging.getLogger(__name__)


class MigrationManager:
    """
    Manages database schema migrations with version tracking.

    Features:
    - Automatic migration discovery and execution
    - Schema version tracking
    - Rollback capabilities
    - Migration validation
    """

    def __init__(self, db_path: str, migrations_dir: str = None):
        self.db_path = Path(db_path)
        self.migrations_dir = Path(migrations_dir or Path(__file__).parent)

    def get_connection(self) -> sqlite3.Connection:
        """Get database connection with proper settings."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def initialize_migration_table(self):
        """Create the schema_migrations table if it doesn't exist."""
        with self.get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version TEXT PRIMARY KEY,
                    applied_at TIMESTAMP NOT NULL,
                    description TEXT
                )
            """)
            conn.commit()

    def get_applied_migrations(self) -> List[str]:
        """Get list of already applied migration versions."""
        self.initialize_migration_table()

        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT version FROM schema_migrations
                ORDER BY version
            """)
            return [row['version'] for row in cursor.fetchall()]

    def discover_migrations(self) -> List[Tuple[str, Path]]:
        """Discover all migration files in the migrations directory."""
        migration_files = []
        migration_pattern = re.compile(r'^(\d{3})_.*\.sql$')

        for file_path in self.migrations_dir.glob('*.sql'):
            match = migration_pattern.match(file_path.name)
            if match:
                version = match.group(1)
                migration_files.append((version, file_path))

        # Sort by version number
        migration_files.sort(key=lambda x: x[0])
        return migration_files

    def get_pending_migrations(self) -> List[Tuple[str, Path]]:
        """Get migrations that haven't been applied yet."""
        applied = set(self.get_applied_migrations())
        all_migrations = self.discover_migrations()

        return [(version, path) for version, path in all_migrations
                if version not in applied]

    def execute_migration(self, version: str, migration_path: Path) -> bool:
        """Execute a single migration file."""
        try:
            with open(migration_path, 'r', encoding='utf-8') as f:
                migration_sql = f.read()

            # Extract description from comments
            description_match = re.search(r'--\s*Migration:\s*(.+)', migration_sql)
            description = description_match.group(1).strip() if description_match else f"Migration {version}"

            with self.get_connection() as conn:
                # Execute the migration
                conn.executescript(migration_sql)

                # Record the migration as applied
                conn.execute("""
                    INSERT OR REPLACE INTO schema_migrations (version, applied_at, description)
                    VALUES (?, ?, ?)
                """, (version, datetime.now(timezone.utc), description))

                conn.commit()

            logger.info(f"Applied migration {version}: {description}")
            return True

        except Exception as e:
            logger.error(f"Failed to execute migration {version}: {e}")
            return False

    def migrate(self) -> bool:
        """Apply all pending migrations."""
        pending = self.get_pending_migrations()

        if not pending:
            logger.info("No pending migrations")
            return True

        logger.info(f"Found {len(pending)} pending migrations")

        for version, path in pending:
            if not self.execute_migration(version, path):
                logger.error(f"Migration stopped at version {version}")
                return False

        logger.info(f"Successfully applied {len(pending)} migrations")
        return True

    def get_current_version(self) -> Optional[str]:
        """Get the latest applied migration version."""
        applied = self.get_applied_migrations()
        return applied[-1] if applied else None

    def rollback_to_version(self, target_version: str) -> bool:
        """
        Rollback to a specific version.

        Note: This is a simple implementation that recreates the schema.
        For production use, consider implementing proper rollback migrations.
        """
        try:
            applied = self.get_applied_migrations()
            if target_version not in applied:
                logger.error(f"Version {target_version} was never applied")
                return False

            # Find migrations to rollback
            target_index = applied.index(target_version)
            migrations_to_rollback = applied[target_index + 1:]

            if not migrations_to_rollback:
                logger.info(f"Already at version {target_version}")
                return True

            logger.warning(f"Rolling back {len(migrations_to_rollback)} migrations")
            logger.warning("This will recreate the schema and lose all data!")

            # Simple rollback: drop all tables and re-apply migrations up to target
            with self.get_connection() as conn:
                # Get all table names
                cursor = conn.execute("""
                    SELECT name FROM sqlite_master
                    WHERE type='table' AND name NOT LIKE 'sqlite_%'
                """)
                tables = [row['name'] for row in cursor.fetchall()]

                # Drop all tables
                for table in tables:
                    conn.execute(f"DROP TABLE IF EXISTS {table}")

                conn.commit()

            # Re-apply migrations up to target version
            all_migrations = self.discover_migrations()
            for version, path in all_migrations:
                if version <= target_version:
                    if not self.execute_migration(version, path):
                        return False
                else:
                    break

            logger.info(f"Successfully rolled back to version {target_version}")
            return True

        except Exception as e:
            logger.error(f"Failed to rollback to version {target_version}: {e}")
            return False

    def validate_schema(self) -> bool:
        """Validate the current database schema."""
        try:
            with self.get_connection() as conn:
                # Check that all expected tables exist
                expected_tables = ['test_runs', 'test_results', 'coverage_data', 'test_metrics', 'schema_migrations']

                cursor = conn.execute("""
                    SELECT name FROM sqlite_master
                    WHERE type='table' AND name NOT LIKE 'sqlite_%'
                """)
                existing_tables = {row['name'] for row in cursor.fetchall()}

                missing_tables = set(expected_tables) - existing_tables
                if missing_tables:
                    logger.error(f"Missing tables: {missing_tables}")
                    return False

                # Check foreign key constraints
                cursor = conn.execute("PRAGMA foreign_key_check")
                fk_violations = cursor.fetchall()
                if fk_violations:
                    logger.error(f"Foreign key violations: {fk_violations}")
                    return False

                # Check indexes exist
                cursor = conn.execute("""
                    SELECT name FROM sqlite_master
                    WHERE type='index' AND name NOT LIKE 'sqlite_%'
                """)
                indexes = {row['name'] for row in cursor.fetchall()}

                expected_indexes = {
                    'idx_test_runs_status', 'idx_test_runs_started_at', 'idx_test_runs_run_id',
                    'idx_test_results_run_id', 'idx_test_results_status',
                    'idx_coverage_data_run_id', 'idx_test_metrics_date'
                }

                missing_indexes = expected_indexes - indexes
                if missing_indexes:
                    logger.warning(f"Missing recommended indexes: {missing_indexes}")

                logger.info("Schema validation passed")
                return True

        except Exception as e:
            logger.error(f"Schema validation failed: {e}")
            return False

    def get_migration_status(self) -> dict:
        """Get detailed migration status information."""
        try:
            applied = self.get_applied_migrations()
            all_migrations = self.discover_migrations()
            pending = self.get_pending_migrations()

            return {
                'current_version': self.get_current_version(),
                'total_migrations': len(all_migrations),
                'applied_count': len(applied),
                'pending_count': len(pending),
                'applied_versions': applied,
                'pending_versions': [v for v, p in pending],
                'schema_valid': self.validate_schema()
            }

        except Exception as e:
            logger.error(f"Failed to get migration status: {e}")
            return {'error': str(e)}