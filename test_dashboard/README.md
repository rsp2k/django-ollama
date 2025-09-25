# Django-Ollama Test Dashboard Database Layer

A high-performance SQLite database infrastructure for tracking test results, coverage data, and historical metrics in the django-ollama test dashboard.

## Architecture Overview

### Core Components

- **models.py**: Data models and schema definitions with proper relationships
- **database.py**: Main database operations layer with connection pooling
- **queries.py**: Optimized query implementations for dashboard operations
- **migrations/**: Schema versioning and migration management system

### Key Features

- **Thread-safe Operations**: Connection pooling with thread-local storage
- **Performance Optimized**: Strategic indexing and query optimization
- **Data Integrity**: Foreign key constraints and transaction management
- **Retention Management**: Automated cleanup of old test data
- **Historical Analysis**: Trend analysis and performance comparisons
- **Real-time Support**: Efficient queries for live dashboard updates

## Database Schema

### Core Tables

1. **test_runs**: Test execution sessions
   - Tracks overall run statistics and metadata
   - Stores git information and environment context
   - Manages run lifecycle (RUNNING → PASSED/FAILED/ERROR)

2. **test_results**: Individual test outcomes
   - Detailed test execution data
   - Performance metrics and error information
   - Links to parent test run via foreign key

3. **coverage_data**: Code coverage information
   - File-level coverage statistics
   - Line and branch coverage details
   - Missing coverage identification

4. **test_metrics**: Daily aggregated metrics
   - Historical trend data
   - Performance baselines
   - Dashboard summary statistics

## Usage Examples

### Basic Operations

```python
from test_dashboard import create_database, TestResult, TestStatus, TestType

# Initialize database
db = create_database("dashboard.db", retention_days=30)

# Create a test run
run_id = db.create_test_run(
    test_command="pytest tests/",
    git_commit="abc123",
    git_branch="feature/new-tests"
)

# Add test results
test_result = TestResult(
    test_name="test_user_authentication",
    test_file="tests/test_auth.py",
    test_method="test_user_authentication",
    test_type=TestType.UNIT,
    status=TestStatus.PASSED,
    duration_seconds=0.045,
    assertions_count=3
)

result_id = db.add_test_result(run_id, test_result)

# Update run when complete
db.update_test_run(run_id,
    status=TestStatus.PASSED,
    finished_at=datetime.now(timezone.utc),
    total_tests=150,
    passed_tests=148,
    failed_tests=2,
    duration_seconds=45.2
)
```

### Advanced Queries

```python
from test_dashboard.queries import QueryOptimizer

optimizer = QueryOptimizer(db._get_connection)

# Get performance metrics for a run
performance = optimizer.get_test_run_performance_metrics(run_id)

# Analyze test failures
failures = optimizer.get_failure_analysis(run_id)

# Compare with historical data
comparison = optimizer.get_historical_comparison(run_id, comparison_days=14)

# Identify flaky tests
flaky_tests = optimizer.get_flaky_tests(days=30, min_runs=10)

# Get test suite health
health = optimizer.get_test_suite_health()
```

### Coverage Data Management

```python
from test_dashboard import CoverageData

# Add coverage information
coverage = CoverageData(
    file_path="src/django_ollama/models.py",
    total_lines=120,
    covered_lines=108,
    missing_lines=[45, 67, 89],
    coverage_percentage=90.0,
    branch_total=25,
    branch_covered=23
)

db.add_coverage_data(run_id, coverage)

# Get coverage summary
summary = db.get_coverage_summary(run_id)
```

## Performance Optimization

### Indexing Strategy

The database uses strategic indexing for common query patterns:

- **Primary Indexes**: Status, timestamps, run relationships
- **Composite Indexes**: Multi-column indexes for complex queries
- **Coverage Indexes**: File path and percentage-based searches

### Query Optimization

- **Connection Pooling**: Thread-local connections with optimization
- **Transaction Management**: Proper ACID compliance with rollback
- **WAL Mode**: Write-Ahead Logging for concurrent access
- **Memory Settings**: Optimized cache and temp storage configuration

### Data Retention

```python
# Automatic cleanup of old data
deleted_count = db.cleanup_old_data()

# Get dashboard summary with recent statistics
summary = db.get_dashboard_summary()
```

## Migration Management

### Schema Versioning

```python
from test_dashboard.migrations import MigrationManager

# Initialize migration manager
migrator = MigrationManager("dashboard.db")

# Apply all pending migrations
success = migrator.migrate()

# Get migration status
status = migrator.get_migration_status()

# Validate current schema
is_valid = migrator.validate_schema()
```

### Creating New Migrations

1. Create a new SQL file: `migrations/002_add_new_feature.sql`
2. Include version tracking and description comments
3. Apply with migration manager

## Dashboard Integration

### Real-time Updates

The database supports efficient real-time dashboard updates:

```python
# Get recent test runs with status filtering
recent_runs = db.get_recent_test_runs(limit=20, status=TestStatus.RUNNING)

# Get test results with pagination
results = db.get_test_results(run_id, limit=50, offset=0)

# Dashboard summary for live metrics
dashboard_data = db.get_dashboard_summary()
```

### Historical Analysis

```python
# Trend data for charts
trends = db.get_trend_data(days=30)

# Coverage trends over time
coverage_trends = optimizer.get_coverage_trends(days=30)

# Performance comparisons
comparison = optimizer.get_historical_comparison(run_id)
```

## Configuration

### Database Settings

The database automatically applies SQLite optimizations:

- **Journal Mode**: WAL (Write-Ahead Logging)
- **Synchronous**: NORMAL for performance
- **Cache Size**: 10,000 pages (40MB)
- **Memory Mapping**: 256MB for large databases
- **Foreign Keys**: Enabled for data integrity

### Retention Policy

Configure data retention to manage storage:

```python
# 30-day retention (default)
db = create_database(retention_days=30)

# Extended retention for important projects
db = create_database(retention_days=90)

# Manual cleanup
db.cleanup_old_data()
```

## Error Handling

The database layer provides comprehensive error handling:

```python
from test_dashboard import DatabaseError

try:
    db.create_test_run(test_command="pytest")
except DatabaseError as e:
    logger.error(f"Database operation failed: {e}")
```

## Performance Monitoring

### Health Metrics

Monitor database and test suite health:

```python
# Overall health assessment
health = optimizer.get_test_suite_health()

# Flaky test identification
flaky = optimizer.get_flaky_tests()

# Performance bottleneck analysis
performance = optimizer.get_test_run_performance_metrics(run_id)
```

### Recommendations

The system provides automated recommendations:

- Success rate improvements
- Performance optimization suggestions
- Flaky test identification
- Coverage improvement targets

## Production Deployment

### Database Location

For production, consider database placement:

```python
# Local development
db = create_database("test_dashboard.db")

# Shared development
db = create_database("/shared/test_data/dashboard.db")

# Production with backup path
db = create_database("/var/lib/test_dashboard/dashboard.db")
```

### Backup Strategy

Regular backups are recommended:

```bash
# SQLite backup
sqlite3 dashboard.db ".backup backup_$(date +%Y%m%d).db"

# With compression
sqlite3 dashboard.db ".backup" | gzip > "backup_$(date +%Y%m%d).db.gz"
```

### Monitoring

Monitor database performance:

```python
# Database size monitoring
import os
db_size = os.path.getsize("dashboard.db")

# Query performance tracking
import time
start = time.time()
results = db.get_recent_test_runs()
query_time = time.time() - start
```

This database layer provides a solid foundation for the django-ollama test dashboard with excellent performance, reliability, and comprehensive feature coverage.