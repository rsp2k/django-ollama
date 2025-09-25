"""
Data models and schemas for the django-ollama test dashboard.

Defines the structure for storing test results, coverage data, and historical metrics
with proper relationships and constraints for SQLite.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, Any, List
import json


class TestStatus(Enum):
    """Test execution status enumeration."""
    RUNNING = "RUNNING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    ERROR = "ERROR"


class TestType(Enum):
    """Test type classification."""
    UNIT = "UNIT"
    INTEGRATION = "INTEGRATION"
    API = "API"
    E2E = "E2E"


@dataclass
class TestRun:
    """Model for a test execution session."""
    id: Optional[int] = None
    run_id: str = ""  # UUID for this test run
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: Optional[datetime] = None
    status: TestStatus = TestStatus.RUNNING
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    skipped_tests: int = 0
    error_tests: int = 0
    duration_seconds: float = 0.0
    test_command: str = ""
    environment_info: Dict[str, Any] = field(default_factory=dict)
    git_commit: Optional[str] = None
    git_branch: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def is_finished(self) -> bool:
        """Check if test run is completed."""
        return self.status != TestStatus.RUNNING

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_tests == 0:
            return 0.0
        return (self.passed_tests / self.total_tests) * 100

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'run_id': self.run_id,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'finished_at': self.finished_at.isoformat() if self.finished_at else None,
            'status': self.status.value,
            'total_tests': self.total_tests,
            'passed_tests': self.passed_tests,
            'failed_tests': self.failed_tests,
            'skipped_tests': self.skipped_tests,
            'error_tests': self.error_tests,
            'duration_seconds': self.duration_seconds,
            'test_command': self.test_command,
            'environment_info': self.environment_info,
            'git_commit': self.git_commit,
            'git_branch': self.git_branch,
            'success_rate': self.success_rate,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


@dataclass
class TestResult:
    """Model for individual test results."""
    id: Optional[int] = None
    run_id: int = 0  # Foreign key to TestRun
    test_name: str = ""
    test_file: str = ""
    test_class: Optional[str] = None
    test_method: str = ""
    test_type: TestType = TestType.UNIT
    status: TestStatus = TestStatus.RUNNING
    duration_seconds: float = 0.0
    error_message: Optional[str] = None
    error_traceback: Optional[str] = None
    setup_duration: float = 0.0
    teardown_duration: float = 0.0
    assertions_count: int = 0
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'run_id': self.run_id,
            'test_name': self.test_name,
            'test_file': self.test_file,
            'test_class': self.test_class,
            'test_method': self.test_method,
            'test_type': self.test_type.value,
            'status': self.status.value,
            'duration_seconds': self.duration_seconds,
            'error_message': self.error_message,
            'error_traceback': self.error_traceback,
            'setup_duration': self.setup_duration,
            'teardown_duration': self.teardown_duration,
            'assertions_count': self.assertions_count,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'finished_at': self.finished_at.isoformat() if self.finished_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


@dataclass
class CoverageData:
    """Model for code coverage information."""
    id: Optional[int] = None
    run_id: int = 0  # Foreign key to TestRun
    file_path: str = ""
    total_lines: int = 0
    covered_lines: int = 0
    missing_lines: List[int] = field(default_factory=list)
    excluded_lines: List[int] = field(default_factory=list)
    branch_total: int = 0
    branch_covered: int = 0
    missing_branches: List[tuple] = field(default_factory=list)
    coverage_percentage: float = 0.0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def line_coverage_rate(self) -> float:
        """Calculate line coverage rate."""
        if self.total_lines == 0:
            return 100.0
        return (self.covered_lines / self.total_lines) * 100

    @property
    def branch_coverage_rate(self) -> float:
        """Calculate branch coverage rate."""
        if self.branch_total == 0:
            return 100.0
        return (self.branch_covered / self.branch_total) * 100

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'run_id': self.run_id,
            'file_path': self.file_path,
            'total_lines': self.total_lines,
            'covered_lines': self.covered_lines,
            'missing_lines': self.missing_lines,
            'excluded_lines': self.excluded_lines,
            'branch_total': self.branch_total,
            'branch_covered': self.branch_covered,
            'missing_branches': self.missing_branches,
            'coverage_percentage': self.coverage_percentage,
            'line_coverage_rate': self.line_coverage_rate,
            'branch_coverage_rate': self.branch_coverage_rate,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


@dataclass
class TestMetrics:
    """Model for aggregated test metrics."""
    id: Optional[int] = None
    date: datetime = field(default_factory=lambda: datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0))
    total_runs: int = 0
    successful_runs: int = 0
    failed_runs: int = 0
    average_duration: float = 0.0
    total_tests: int = 0
    average_success_rate: float = 0.0
    coverage_average: float = 0.0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'date': self.date.isoformat() if self.date else None,
            'total_runs': self.total_runs,
            'successful_runs': self.successful_runs,
            'failed_runs': self.failed_runs,
            'average_duration': self.average_duration,
            'total_tests': self.total_tests,
            'average_success_rate': self.average_success_rate,
            'coverage_average': self.coverage_average,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


# SQL Schema Definition
SQL_SCHEMA = """
-- Test runs table
CREATE TABLE IF NOT EXISTS test_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT UNIQUE NOT NULL,
    started_at TIMESTAMP NOT NULL,
    finished_at TIMESTAMP,
    status TEXT NOT NULL CHECK (status IN ('RUNNING', 'PASSED', 'FAILED', 'SKIPPED', 'ERROR')),
    total_tests INTEGER DEFAULT 0,
    passed_tests INTEGER DEFAULT 0,
    failed_tests INTEGER DEFAULT 0,
    skipped_tests INTEGER DEFAULT 0,
    error_tests INTEGER DEFAULT 0,
    duration_seconds REAL DEFAULT 0.0,
    test_command TEXT DEFAULT '',
    environment_info TEXT DEFAULT '{}', -- JSON string
    git_commit TEXT,
    git_branch TEXT,
    created_at TIMESTAMP NOT NULL
);

-- Test results table
CREATE TABLE IF NOT EXISTS test_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    test_name TEXT NOT NULL,
    test_file TEXT NOT NULL,
    test_class TEXT,
    test_method TEXT NOT NULL,
    test_type TEXT NOT NULL CHECK (test_type IN ('UNIT', 'INTEGRATION', 'API', 'E2E')),
    status TEXT NOT NULL CHECK (status IN ('RUNNING', 'PASSED', 'FAILED', 'SKIPPED', 'ERROR')),
    duration_seconds REAL DEFAULT 0.0,
    error_message TEXT,
    error_traceback TEXT,
    setup_duration REAL DEFAULT 0.0,
    teardown_duration REAL DEFAULT 0.0,
    assertions_count INTEGER DEFAULT 0,
    started_at TIMESTAMP NOT NULL,
    finished_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL,
    FOREIGN KEY (run_id) REFERENCES test_runs (id) ON DELETE CASCADE
);

-- Coverage data table
CREATE TABLE IF NOT EXISTS coverage_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    file_path TEXT NOT NULL,
    total_lines INTEGER DEFAULT 0,
    covered_lines INTEGER DEFAULT 0,
    missing_lines TEXT DEFAULT '[]', -- JSON array of line numbers
    excluded_lines TEXT DEFAULT '[]', -- JSON array of line numbers
    branch_total INTEGER DEFAULT 0,
    branch_covered INTEGER DEFAULT 0,
    missing_branches TEXT DEFAULT '[]', -- JSON array of branch tuples
    coverage_percentage REAL DEFAULT 0.0,
    created_at TIMESTAMP NOT NULL,
    FOREIGN KEY (run_id) REFERENCES test_runs (id) ON DELETE CASCADE
);

-- Test metrics table for daily aggregations
CREATE TABLE IF NOT EXISTS test_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE UNIQUE NOT NULL,
    total_runs INTEGER DEFAULT 0,
    successful_runs INTEGER DEFAULT 0,
    failed_runs INTEGER DEFAULT 0,
    average_duration REAL DEFAULT 0.0,
    total_tests INTEGER DEFAULT 0,
    average_success_rate REAL DEFAULT 0.0,
    coverage_average REAL DEFAULT 0.0,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

-- Indexes for performance optimization
CREATE INDEX IF NOT EXISTS idx_test_runs_status ON test_runs(status);
CREATE INDEX IF NOT EXISTS idx_test_runs_started_at ON test_runs(started_at);
CREATE INDEX IF NOT EXISTS idx_test_runs_run_id ON test_runs(run_id);
CREATE INDEX IF NOT EXISTS idx_test_runs_git_branch ON test_runs(git_branch);

CREATE INDEX IF NOT EXISTS idx_test_results_run_id ON test_results(run_id);
CREATE INDEX IF NOT EXISTS idx_test_results_status ON test_results(status);
CREATE INDEX IF NOT EXISTS idx_test_results_test_file ON test_results(test_file);
CREATE INDEX IF NOT EXISTS idx_test_results_test_type ON test_results(test_type);
CREATE INDEX IF NOT EXISTS idx_test_results_duration ON test_results(duration_seconds);

CREATE INDEX IF NOT EXISTS idx_coverage_data_run_id ON coverage_data(run_id);
CREATE INDEX IF NOT EXISTS idx_coverage_data_file_path ON coverage_data(file_path);
CREATE INDEX IF NOT EXISTS idx_coverage_data_coverage_percentage ON coverage_data(coverage_percentage);

CREATE INDEX IF NOT EXISTS idx_test_metrics_date ON test_metrics(date);

-- Composite indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_test_runs_status_started_at ON test_runs(status, started_at);
CREATE INDEX IF NOT EXISTS idx_test_results_run_status ON test_results(run_id, status);
CREATE INDEX IF NOT EXISTS idx_coverage_run_file ON coverage_data(run_id, file_path);
"""