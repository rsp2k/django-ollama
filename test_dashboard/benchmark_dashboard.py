#!/usr/bin/env python3
"""
Django-Ollama Test Dashboard Performance Benchmark Suite

Comprehensive performance testing and validation for the test dashboard system.
Tests database operations, API endpoints, WebSocket performance, and system limits.

Usage:
    python benchmark_dashboard.py
    python benchmark_dashboard.py --quick
    python benchmark_dashboard.py --stress
    python benchmark_dashboard.py --profile
"""

import argparse
import asyncio
import json
import multiprocessing
import os
import statistics
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import uuid

import requests
import websockets
from tabulate import tabulate

# Add test_dashboard to path
sys.path.insert(0, str(Path(__file__).parent))

from database import TestDashboardDB
from models import TestResult, TestStatus, TestType, CoverageData


class BenchmarkTimer:
    """Context manager for timing operations."""

    def __init__(self, description: str = ""):
        self.description = description
        self.start_time = None
        self.end_time = None
        self.duration = None

    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.perf_counter()
        self.duration = self.end_time - self.start_time

    def __str__(self):
        return f"{self.description}: {self.duration:.4f}s"


class PerformanceMetrics:
    """Collect and analyze performance metrics."""

    def __init__(self):
        self.metrics = {}
        self.timings = []

    def add_timing(self, operation: str, duration: float, success: bool = True):
        """Add a timing measurement."""
        if operation not in self.metrics:
            self.metrics[operation] = {
                'timings': [],
                'successes': 0,
                'failures': 0
            }

        self.metrics[operation]['timings'].append(duration)
        if success:
            self.metrics[operation]['successes'] += 1
        else:
            self.metrics[operation]['failures'] += 1

    def get_stats(self, operation: str) -> Dict:
        """Get statistics for an operation."""
        if operation not in self.metrics:
            return {}

        timings = self.metrics[operation]['timings']
        if not timings:
            return {}

        return {
            'count': len(timings),
            'mean': statistics.mean(timings),
            'median': statistics.median(timings),
            'min': min(timings),
            'max': max(timings),
            'stdev': statistics.stdev(timings) if len(timings) > 1 else 0,
            'p95': self.percentile(timings, 0.95),
            'p99': self.percentile(timings, 0.99),
            'successes': self.metrics[operation]['successes'],
            'failures': self.metrics[operation]['failures'],
            'success_rate': self.metrics[operation]['successes'] / len(timings) * 100
        }

    @staticmethod
    def percentile(data: List[float], p: float) -> float:
        """Calculate percentile."""
        sorted_data = sorted(data)
        index = p * (len(sorted_data) - 1)
        if index.is_integer():
            return sorted_data[int(index)]
        else:
            lower = sorted_data[int(index)]
            upper = sorted_data[int(index) + 1]
            return lower + (upper - lower) * (index - int(index))

    def print_summary(self):
        """Print performance summary."""
        headers = ['Operation', 'Count', 'Mean', 'Median', 'Min', 'Max', 'P95', 'P99', 'Success%']
        rows = []

        for operation in sorted(self.metrics.keys()):
            stats = self.get_stats(operation)
            if stats:
                rows.append([
                    operation,
                    stats['count'],
                    f"{stats['mean']:.4f}s",
                    f"{stats['median']:.4f}s",
                    f"{stats['min']:.4f}s",
                    f"{stats['max']:.4f}s",
                    f"{stats['p95']:.4f}s",
                    f"{stats['p99']:.4f}s",
                    f"{stats['success_rate']:.1f}%"
                ])

        print("\n" + "="*80)
        print("PERFORMANCE SUMMARY")
        print("="*80)
        print(tabulate(rows, headers=headers, tablefmt="grid"))


class DatabaseBenchmark:
    """Database performance benchmarks."""

    def __init__(self, metrics: PerformanceMetrics):
        self.metrics = metrics

    def benchmark_create_test_runs(self, db: TestDashboardDB, count: int = 1000) -> List[str]:
        """Benchmark test run creation."""
        print(f"📊 Creating {count} test runs...")

        run_ids = []
        for i in range(count):
            with BenchmarkTimer() as timer:
                try:
                    run_id = db.create_test_run(
                        test_command=f"pytest test_{i}",
                        git_commit=f"commit_{i}",
                        git_branch="benchmark",
                        environment_info={
                            "python": "3.11.0",
                            "django": "4.2.0",
                            "test_id": i
                        }
                    )
                    run_ids.append(run_id)
                    success = True
                except Exception as e:
                    print(f"Error creating test run {i}: {e}")
                    success = False

            self.metrics.add_timing('create_test_run', timer.duration, success)

        return run_ids

    def benchmark_add_test_results(self, db: TestDashboardDB, run_ids: List[str], results_per_run: int = 50):
        """Benchmark adding test results."""
        total_results = len(run_ids) * results_per_run
        print(f"📊 Adding {total_results} test results ({results_per_run} per run)...")

        for run_id in run_ids:
            for i in range(results_per_run):
                with BenchmarkTimer() as timer:
                    try:
                        result = TestResult(
                            test_name=f"test_method_{i}",
                            test_file=f"tests/test_{i}.py",
                            test_method=f"test_method_{i}",
                            test_type=TestType.UNIT if i % 4 != 0 else TestType.INTEGRATION,
                            status=TestStatus.PASSED if i % 5 != 0 else TestStatus.FAILED,
                            duration_seconds=0.1 + (i * 0.01),
                            error_message="Test failed" if i % 5 == 0 else None,
                            started_at=datetime.now(timezone.utc),
                            finished_at=datetime.now(timezone.utc)
                        )

                        db.add_test_result(run_id, result)
                        success = True
                    except Exception as e:
                        print(f"Error adding test result: {e}")
                        success = False

                self.metrics.add_timing('add_test_result', timer.duration, success)

    def benchmark_queries(self, db: TestDashboardDB, run_ids: List[str]):
        """Benchmark various database queries."""
        print("📊 Benchmarking database queries...")

        # Test recent runs query
        for i in range(100):
            with BenchmarkTimer() as timer:
                try:
                    runs = db.get_recent_test_runs(limit=50)
                    success = len(runs) >= 0
                except Exception as e:
                    print(f"Error in recent runs query: {e}")
                    success = False

            self.metrics.add_timing('query_recent_runs', timer.duration, success)

        # Test individual run queries
        for run_id in run_ids[:20]:  # Test first 20 runs
            with BenchmarkTimer() as timer:
                try:
                    run = db.get_test_run(run_id)
                    success = run is not None
                except Exception as e:
                    print(f"Error querying run {run_id}: {e}")
                    success = False

            self.metrics.add_timing('query_single_run', timer.duration, success)

            # Test results query
            with BenchmarkTimer() as timer:
                try:
                    results = db.get_test_results(run_id, limit=10)
                    success = len(results) >= 0
                except Exception as e:
                    print(f"Error querying results for {run_id}: {e}")
                    success = False

            self.metrics.add_timing('query_test_results', timer.duration, success)

        # Test dashboard summary
        for i in range(50):
            with BenchmarkTimer() as timer:
                try:
                    summary = db.get_dashboard_summary()
                    success = 'recent_24h' in summary
                except Exception as e:
                    print(f"Error in dashboard summary: {e}")
                    success = False

            self.metrics.add_timing('query_dashboard_summary', timer.duration, success)

        # Test trend data
        for days in [7, 30, 90]:
            with BenchmarkTimer() as timer:
                try:
                    trends = db.get_trend_data(days=days)
                    success = isinstance(trends, list)
                except Exception as e:
                    print(f"Error in trend data query: {e}")
                    success = False

            self.metrics.add_timing(f'query_trends_{days}d', timer.duration, success)

    def benchmark_concurrent_access(self, db_path: str, num_workers: int = 5, operations_per_worker: int = 100):
        """Benchmark concurrent database access."""
        print(f"📊 Testing concurrent access ({num_workers} workers, {operations_per_worker} ops each)...")

        def worker(worker_id: int, results: Dict):
            """Worker function for concurrent testing."""
            timings = []
            errors = 0

            try:
                worker_db = TestDashboardDB(db_path)

                for i in range(operations_per_worker):
                    # Mix of operations
                    operation = i % 4

                    start_time = time.perf_counter()

                    if operation == 0:  # Create run
                        try:
                            run_id = worker_db.create_test_run(f"worker_{worker_id}_run_{i}")
                            success = True
                        except Exception:
                            success = False
                            errors += 1

                    elif operation == 1:  # Query recent runs
                        try:
                            runs = worker_db.get_recent_test_runs(limit=10)
                            success = True
                        except Exception:
                            success = False
                            errors += 1

                    elif operation == 2:  # Query dashboard summary
                        try:
                            summary = worker_db.get_dashboard_summary()
                            success = True
                        except Exception:
                            success = False
                            errors += 1

                    else:  # Query trends
                        try:
                            trends = worker_db.get_trend_data(days=7)
                            success = True
                        except Exception:
                            success = False
                            errors += 1

                    end_time = time.perf_counter()
                    timings.append(end_time - start_time)

                worker_db.close()

                results[worker_id] = {
                    'timings': timings,
                    'errors': errors,
                    'success': True
                }

            except Exception as e:
                results[worker_id] = {
                    'error': str(e),
                    'success': False
                }

        # Run workers
        workers = []
        results = {}

        start_time = time.perf_counter()

        for i in range(num_workers):
            worker_thread = threading.Thread(target=worker, args=(i, results))
            workers.append(worker_thread)
            worker_thread.start()

        # Wait for completion
        for worker_thread in workers:
            worker_thread.join(timeout=60)

        end_time = time.perf_counter()
        total_time = end_time - start_time

        # Analyze results
        successful_workers = sum(1 for r in results.values() if r.get('success', False))
        total_operations = successful_workers * operations_per_worker

        if total_operations > 0:
            ops_per_second = total_operations / total_time

            all_timings = []
            total_errors = 0

            for result in results.values():
                if result.get('success', False):
                    all_timings.extend(result['timings'])
                    total_errors += result['errors']

            avg_response_time = statistics.mean(all_timings) if all_timings else 0

            print(f"   Workers: {successful_workers}/{num_workers}")
            print(f"   Operations/sec: {ops_per_second:.2f}")
            print(f"   Avg response time: {avg_response_time:.4f}s")
            print(f"   Error rate: {total_errors/len(all_timings)*100:.2f}%" if all_timings else "N/A")

            self.metrics.add_timing('concurrent_ops_per_second', ops_per_second)


class APIBenchmark:
    """API endpoint performance benchmarks."""

    def __init__(self, metrics: PerformanceMetrics, base_url: str = "http://localhost:8080"):
        self.metrics = metrics
        self.base_url = base_url
        self.session = requests.Session()

    def benchmark_endpoints(self, requests_per_endpoint: int = 100):
        """Benchmark various API endpoints."""
        print(f"📊 Benchmarking API endpoints ({requests_per_endpoint} requests each)...")

        endpoints = [
            ("/api/health", "health_check"),
            ("/api/dashboard/summary", "dashboard_summary"),
            ("/api/dashboard/recent-runs", "recent_runs"),
            ("/api/dashboard/trends?days=7", "trends_7d"),
            ("/api/dashboard/trends?days=30", "trends_30d"),
            ("/api/stats", "system_stats"),
            ("/api/websocket/status", "websocket_status")
        ]

        for endpoint, metric_name in endpoints:
            print(f"   Testing {endpoint}...")

            for i in range(requests_per_endpoint):
                with BenchmarkTimer() as timer:
                    try:
                        response = self.session.get(
                            f"{self.base_url}{endpoint}",
                            timeout=10
                        )
                        success = response.status_code == 200
                    except Exception as e:
                        success = False

                self.metrics.add_timing(f'api_{metric_name}', timer.duration, success)

    def benchmark_concurrent_requests(self, num_threads: int = 10, requests_per_thread: int = 50):
        """Benchmark concurrent API requests."""
        print(f"📊 Testing concurrent API requests ({num_threads} threads, {requests_per_thread} requests each)...")

        def make_requests(thread_id: int, results: Dict):
            """Make multiple requests from a single thread."""
            timings = []
            errors = 0

            endpoints = [
                "/api/health",
                "/api/dashboard/summary",
                "/api/dashboard/recent-runs",
                "/api/stats"
            ]

            try:
                session = requests.Session()

                for i in range(requests_per_thread):
                    endpoint = endpoints[i % len(endpoints)]

                    start_time = time.perf_counter()
                    try:
                        response = session.get(f"{self.base_url}{endpoint}", timeout=10)
                        success = response.status_code == 200
                    except Exception:
                        success = False
                        errors += 1

                    end_time = time.perf_counter()
                    timings.append(end_time - start_time)

                session.close()

                results[thread_id] = {
                    'timings': timings,
                    'errors': errors,
                    'success': True
                }

            except Exception as e:
                results[thread_id] = {
                    'error': str(e),
                    'success': False
                }

        # Run concurrent requests
        threads = []
        results = {}

        start_time = time.perf_counter()

        for i in range(num_threads):
            thread = threading.Thread(target=make_requests, args=(i, results))
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join(timeout=120)

        end_time = time.perf_counter()
        total_time = end_time - start_time

        # Analyze results
        successful_threads = sum(1 for r in results.values() if r.get('success', False))
        total_requests = successful_threads * requests_per_thread

        if total_requests > 0:
            requests_per_second = total_requests / total_time

            all_timings = []
            total_errors = 0

            for result in results.values():
                if result.get('success', False):
                    all_timings.extend(result['timings'])
                    total_errors += result['errors']

            avg_response_time = statistics.mean(all_timings) if all_timings else 0

            print(f"   Threads: {successful_threads}/{num_threads}")
            print(f"   Requests/sec: {requests_per_second:.2f}")
            print(f"   Avg response time: {avg_response_time:.4f}s")
            print(f"   Error rate: {total_errors/len(all_timings)*100:.2f}%" if all_timings else "N/A")

            self.metrics.add_timing('api_requests_per_second', requests_per_second)


class WebSocketBenchmark:
    """WebSocket performance benchmarks."""

    def __init__(self, metrics: PerformanceMetrics, websocket_url: str = "ws://localhost:8080/ws"):
        self.metrics = metrics
        self.websocket_url = websocket_url

    async def benchmark_connection_time(self, num_connections: int = 50):
        """Benchmark WebSocket connection establishment time."""
        print(f"📊 Benchmarking WebSocket connections ({num_connections} connections)...")

        for i in range(num_connections):
            start_time = time.perf_counter()
            try:
                async with websockets.connect(self.websocket_url) as websocket:
                    # Wait for connection established message
                    message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    data = json.loads(message)

                    end_time = time.perf_counter()
                    connection_time = end_time - start_time

                    success = data.get("type") == "connection_established"
                    self.metrics.add_timing('websocket_connection', connection_time, success)

            except Exception as e:
                end_time = time.perf_counter()
                connection_time = end_time - start_time
                self.metrics.add_timing('websocket_connection', connection_time, False)

    async def benchmark_message_throughput(self, num_messages: int = 1000):
        """Benchmark WebSocket message throughput."""
        print(f"📊 Benchmarking WebSocket message throughput ({num_messages} messages)...")

        try:
            async with websockets.connect(self.websocket_url) as websocket:
                # Skip connection message
                await websocket.recv()

                # Send ping messages and measure response time
                for i in range(num_messages):
                    start_time = time.perf_counter()

                    ping_message = {"type": "ping", "id": i}
                    await websocket.send(json.dumps(ping_message))

                    # Wait for pong response
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    data = json.loads(response)

                    end_time = time.perf_counter()
                    round_trip_time = end_time - start_time

                    success = data.get("type") == "pong"
                    self.metrics.add_timing('websocket_ping_pong', round_trip_time, success)

                    # Small delay to avoid overwhelming the server
                    if i % 100 == 0:
                        await asyncio.sleep(0.01)

        except Exception as e:
            print(f"WebSocket throughput test failed: {e}")

    async def benchmark_concurrent_connections(self, num_connections: int = 20):
        """Benchmark multiple concurrent WebSocket connections."""
        print(f"📊 Testing concurrent WebSocket connections ({num_connections} connections)...")

        async def single_connection(connection_id: int):
            """Handle a single WebSocket connection."""
            try:
                start_time = time.perf_counter()
                async with websockets.connect(self.websocket_url) as websocket:
                    # Receive connection message
                    await websocket.recv()

                    connection_time = time.perf_counter() - start_time

                    # Send a few messages
                    for i in range(10):
                        await websocket.send(json.dumps({"type": "ping"}))
                        await websocket.recv()  # Receive pong

                    # Connection successful
                    self.metrics.add_timing('websocket_concurrent_connection', connection_time, True)

            except Exception as e:
                connection_time = time.perf_counter() - start_time
                self.metrics.add_timing('websocket_concurrent_connection', connection_time, False)

        # Create concurrent connections
        tasks = []
        for i in range(num_connections):
            task = asyncio.create_task(single_connection(i))
            tasks.append(task)

        # Wait for all connections to complete
        await asyncio.gather(*tasks, return_exceptions=True)

    def run_benchmarks(self):
        """Run all WebSocket benchmarks."""
        async def run_async_benchmarks():
            try:
                await self.benchmark_connection_time(50)
                await self.benchmark_message_throughput(500)
                await self.benchmark_concurrent_connections(10)
            except Exception as e:
                print(f"WebSocket benchmarks skipped: {e}")

        # Run async benchmarks
        try:
            asyncio.run(run_async_benchmarks())
        except Exception as e:
            print(f"WebSocket benchmarks failed: {e}")


class SystemBenchmark:
    """System-level performance benchmarks."""

    def __init__(self, metrics: PerformanceMetrics):
        self.metrics = metrics

    def benchmark_file_io(self, temp_dir: Path):
        """Benchmark file I/O operations."""
        print("📊 Benchmarking file I/O operations...")

        # Test database file creation
        for i in range(10):
            db_path = temp_dir / f"io_test_{i}.db"

            with BenchmarkTimer() as timer:
                try:
                    db = TestDashboardDB(str(db_path))
                    run_id = db.create_test_run(f"io_test_{i}")
                    db.close()
                    success = True
                except Exception:
                    success = False

            self.metrics.add_timing('file_io_db_creation', timer.duration, success)

            # Clean up
            if db_path.exists():
                db_path.unlink()

        # Test large file operations
        large_file = temp_dir / "large_test.db"
        db = TestDashboardDB(str(large_file))

        # Create large dataset
        with BenchmarkTimer() as timer:
            run_ids = []
            for i in range(100):
                run_id = db.create_test_run(f"large_io_test_{i}")
                run_ids.append(run_id)

                # Add multiple results per run
                for j in range(20):
                    result = TestResult(
                        test_name=f"test_{j}",
                        test_file=f"test_{j}.py",
                        test_method=f"test_method_{j}",
                        test_type=TestType.UNIT,
                        status=TestStatus.PASSED,
                        duration_seconds=0.1,
                        started_at=datetime.now(timezone.utc),
                        finished_at=datetime.now(timezone.utc)
                    )
                    db.add_test_result(run_id, result)

        self.metrics.add_timing('file_io_large_dataset', timer.duration, True)

        db.close()
        if large_file.exists():
            large_file.unlink()

    def benchmark_memory_usage(self):
        """Benchmark memory usage patterns."""
        print("📊 Benchmarking memory usage...")

        try:
            import psutil
            process = psutil.Process()

            # Initial memory
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB

            # Create temporary database with large dataset
            with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
                db_path = f.name

            try:
                db = TestDashboardDB(db_path)

                # Add progressively more data and measure memory
                for batch in range(10):
                    batch_start_memory = process.memory_info().rss / 1024 / 1024

                    # Add a batch of data
                    for i in range(100):
                        run_id = db.create_test_run(f"memory_test_batch_{batch}_run_{i}")

                        for j in range(10):
                            result = TestResult(
                                test_name=f"test_{j}",
                                test_file=f"test_{j}.py",
                                test_method=f"test_method_{j}",
                                test_type=TestType.UNIT,
                                status=TestStatus.PASSED,
                                duration_seconds=0.1,
                                started_at=datetime.now(timezone.utc),
                                finished_at=datetime.now(timezone.utc)
                            )
                            db.add_test_result(run_id, result)

                    batch_end_memory = process.memory_info().rss / 1024 / 1024
                    memory_increase = batch_end_memory - batch_start_memory

                    self.metrics.add_timing(f'memory_usage_batch_{batch}', memory_increase, True)

                db.close()

                final_memory = process.memory_info().rss / 1024 / 1024
                total_increase = final_memory - initial_memory

                print(f"   Initial memory: {initial_memory:.2f} MB")
                print(f"   Final memory: {final_memory:.2f} MB")
                print(f"   Total increase: {total_increase:.2f} MB")

            finally:
                if Path(db_path).exists():
                    Path(db_path).unlink()

        except ImportError:
            print("   psutil not available, skipping memory benchmark")


def run_quick_benchmark() -> PerformanceMetrics:
    """Run a quick benchmark suite."""
    print("🚀 Running Quick Benchmark Suite")
    print("="*50)

    metrics = PerformanceMetrics()

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        db_path = temp_path / "quick_benchmark.db"

        # Database benchmarks
        db_benchmark = DatabaseBenchmark(metrics)
        db = TestDashboardDB(str(db_path))

        # Quick database tests
        run_ids = db_benchmark.benchmark_create_test_runs(db, count=100)
        db_benchmark.benchmark_add_test_results(db, run_ids[:10], results_per_run=10)
        db_benchmark.benchmark_queries(db, run_ids[:5])

        db.close()

        # API benchmarks (if server is running)
        try:
            api_benchmark = APIBenchmark(metrics)
            api_benchmark.benchmark_endpoints(requests_per_endpoint=10)
        except Exception as e:
            print(f"API benchmarks skipped: {e}")

        # WebSocket benchmarks (if server is running)
        try:
            ws_benchmark = WebSocketBenchmark(metrics)
            asyncio.run(ws_benchmark.benchmark_connection_time(5))
        except Exception as e:
            print(f"WebSocket benchmarks skipped: {e}")

    return metrics


def run_comprehensive_benchmark() -> PerformanceMetrics:
    """Run comprehensive benchmark suite."""
    print("🚀 Running Comprehensive Benchmark Suite")
    print("="*60)

    metrics = PerformanceMetrics()

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        db_path = temp_path / "comprehensive_benchmark.db"

        # Database benchmarks
        print("\n📊 DATABASE BENCHMARKS")
        print("-" * 30)

        db_benchmark = DatabaseBenchmark(metrics)
        db = TestDashboardDB(str(db_path))

        run_ids = db_benchmark.benchmark_create_test_runs(db, count=1000)
        db_benchmark.benchmark_add_test_results(db, run_ids[:100], results_per_run=50)
        db_benchmark.benchmark_queries(db, run_ids[:20])
        db_benchmark.benchmark_concurrent_access(str(db_path), num_workers=5, operations_per_worker=100)

        db.close()

        # API benchmarks
        print("\n📊 API BENCHMARKS")
        print("-" * 20)

        try:
            api_benchmark = APIBenchmark(metrics)
            api_benchmark.benchmark_endpoints(requests_per_endpoint=100)
            api_benchmark.benchmark_concurrent_requests(num_threads=10, requests_per_thread=50)
        except Exception as e:
            print(f"API benchmarks skipped: {e}")

        # WebSocket benchmarks
        print("\n📊 WEBSOCKET BENCHMARKS")
        print("-" * 25)

        try:
            ws_benchmark = WebSocketBenchmark(metrics)
            ws_benchmark.run_benchmarks()
        except Exception as e:
            print(f"WebSocket benchmarks skipped: {e}")

        # System benchmarks
        print("\n📊 SYSTEM BENCHMARKS")
        print("-" * 22)

        system_benchmark = SystemBenchmark(metrics)
        system_benchmark.benchmark_file_io(temp_path)
        system_benchmark.benchmark_memory_usage()

    return metrics


def run_stress_test() -> PerformanceMetrics:
    """Run stress test suite."""
    print("🚀 Running Stress Test Suite")
    print("="*40)

    metrics = PerformanceMetrics()

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        db_path = temp_path / "stress_test.db"

        print("\n🔥 STRESS TEST: Large Database Operations")
        print("-" * 50)

        db_benchmark = DatabaseBenchmark(metrics)
        db = TestDashboardDB(str(db_path))

        # Stress test: Create many test runs with many results
        large_run_ids = db_benchmark.benchmark_create_test_runs(db, count=2000)
        db_benchmark.benchmark_add_test_results(db, large_run_ids[:200], results_per_run=100)

        print("\n🔥 STRESS TEST: Heavy Concurrent Access")
        print("-" * 40)

        db_benchmark.benchmark_concurrent_access(str(db_path), num_workers=20, operations_per_worker=200)

        # Stress test queries with large dataset
        print("\n🔥 STRESS TEST: Query Performance with Large Dataset")
        print("-" * 55)

        db_benchmark.benchmark_queries(db, large_run_ids[:50])

        db.close()

        print("\n🔥 STRESS TEST: High-Volume API Requests")
        print("-" * 42)

        try:
            api_benchmark = APIBenchmark(metrics)
            api_benchmark.benchmark_concurrent_requests(num_threads=50, requests_per_thread=100)
        except Exception as e:
            print(f"API stress test skipped: {e}")

        print("\n🔥 STRESS TEST: WebSocket Connection Limits")
        print("-" * 45)

        try:
            ws_benchmark = WebSocketBenchmark(metrics)
            asyncio.run(ws_benchmark.benchmark_concurrent_connections(50))
        except Exception as e:
            print(f"WebSocket stress test skipped: {e}")

    return metrics


def validate_performance_targets(metrics: PerformanceMetrics) -> bool:
    """Validate that performance meets target benchmarks."""
    print("\n🎯 PERFORMANCE VALIDATION")
    print("=" * 35)

    # Define performance targets
    targets = {
        'create_test_run': {'max_mean': 0.1, 'max_p95': 0.2},
        'add_test_result': {'max_mean': 0.05, 'max_p95': 0.1},
        'query_recent_runs': {'max_mean': 0.1, 'max_p95': 0.2},
        'query_dashboard_summary': {'max_mean': 0.2, 'max_p95': 0.5},
        'api_health_check': {'max_mean': 0.1, 'max_p95': 0.2},
        'api_dashboard_summary': {'max_mean': 0.5, 'max_p95': 1.0},
        'websocket_connection': {'max_mean': 1.0, 'max_p95': 2.0},
    }

    passed = 0
    failed = 0
    results = []

    for operation, target in targets.items():
        stats = metrics.get_stats(operation)

        if not stats:
            results.append([operation, "N/A", "N/A", "SKIPPED"])
            continue

        mean_ok = stats['mean'] <= target['max_mean']
        p95_ok = stats['p95'] <= target['max_p95']

        if mean_ok and p95_ok:
            status = "✅ PASS"
            passed += 1
        else:
            status = "❌ FAIL"
            failed += 1

        results.append([
            operation,
            f"{stats['mean']:.4f}s ({'✅' if mean_ok else '❌'} {target['max_mean']}s)",
            f"{stats['p95']:.4f}s ({'✅' if p95_ok else '❌'} {target['max_p95']}s)",
            status
        ])

    # Print validation results
    headers = ['Operation', 'Mean (Target)', 'P95 (Target)', 'Status']
    print(tabulate(results, headers=headers, tablefmt="grid"))

    print(f"\nValidation Results: {passed} passed, {failed} failed")

    return failed == 0


def main():
    """Main benchmark runner."""
    parser = argparse.ArgumentParser(description="Django-Ollama Test Dashboard Benchmark Suite")
    parser.add_argument("--quick", action="store_true", help="Run quick benchmark suite")
    parser.add_argument("--stress", action="store_true", help="Run stress test suite")
    parser.add_argument("--profile", action="store_true", help="Enable detailed profiling")
    parser.add_argument("--validate", action="store_true", help="Validate performance targets")
    parser.add_argument("--output", help="Output file for results (JSON format)")

    args = parser.parse_args()

    # Default to comprehensive if no specific mode selected
    if not any([args.quick, args.stress]):
        args.quick = True

    print("🧪 Django-Ollama Test Dashboard Benchmark Suite")
    print("=" * 60)
    print(f"Python: {sys.version}")
    print(f"CPUs: {multiprocessing.cpu_count()}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Run benchmarks
    if args.quick:
        metrics = run_quick_benchmark()
    elif args.stress:
        metrics = run_stress_test()
    else:
        metrics = run_comprehensive_benchmark()

    # Print results
    metrics.print_summary()

    # Validate performance if requested
    if args.validate:
        validation_passed = validate_performance_targets(metrics)
        if not validation_passed:
            print("\n❌ Performance validation FAILED")
            sys.exit(1)
        else:
            print("\n✅ Performance validation PASSED")

    # Save results to file if requested
    if args.output:
        results = {}
        for operation in metrics.metrics.keys():
            results[operation] = metrics.get_stats(operation)

        with open(args.output, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'system_info': {
                    'python_version': sys.version,
                    'cpu_count': multiprocessing.cpu_count(),
                },
                'results': results
            }, f, indent=2)

        print(f"\n📄 Results saved to {args.output}")

    print("\n🎉 Benchmark suite completed successfully!")


if __name__ == "__main__":
    main()