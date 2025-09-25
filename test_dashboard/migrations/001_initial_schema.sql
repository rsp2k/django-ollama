-- Initial schema migration for django-ollama test dashboard
-- Version: 001
-- Created: 2024-09-24

-- Migration: Create initial test dashboard tables and indexes

-- Test runs table - stores information about test execution sessions
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

-- Test results table - stores individual test results
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

-- Coverage data table - stores code coverage information
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

-- Test metrics table - stores daily aggregated metrics
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

-- Primary indexes for performance optimization
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

-- Schema version tracking
CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at TIMESTAMP NOT NULL,
    description TEXT
);

INSERT INTO schema_migrations (version, applied_at, description)
VALUES ('001', datetime('now'), 'Initial schema with test_runs, test_results, coverage_data, and test_metrics tables');