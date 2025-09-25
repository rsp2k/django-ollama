#!/usr/bin/env python3
"""
WebSocket Dashboard Demo Script

This script demonstrates the real-time WebSocket functionality by simulating
a realistic test run scenario with multiple tests, failures, and coverage updates.
"""

import asyncio
import json
import requests
import time
import random
from datetime import datetime


class WebSocketDemo:
    """Demonstrate WebSocket functionality with realistic test scenarios."""

    def __init__(self, server_url="http://localhost:8080"):
        self.server_url = server_url
        self.run_id = f"demo-run-{int(time.time())}"

    def send_event(self, event_data):
        """Send an event via the HTTP API."""
        try:
            response = requests.post(
                f"{self.server_url}/api/test/simulate-event",
                json=event_data,
                timeout=5.0
            )
            if response.status_code == 200:
                return True
            else:
                print(f"⚠️  Event send warning: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Failed to send event: {e}")
            return False

    async def simulate_django_test_suite(self):
        """Simulate a comprehensive Django test suite with realistic timing."""
        print("🎬 Starting Django-Ollama Test Suite Demo")
        print(f"📋 Run ID: {self.run_id}")
        print("=" * 60)

        # Define realistic test scenarios
        test_scenarios = [
            {
                "name": "test_user_model_creation",
                "file": "tests/test_models.py",
                "duration": 0.8,
                "status": "PASSED"
            },
            {
                "name": "test_user_authentication",
                "file": "tests/test_auth.py",
                "duration": 1.2,
                "status": "PASSED"
            },
            {
                "name": "test_ollama_api_connection",
                "file": "tests/test_api.py",
                "duration": 2.5,
                "status": "PASSED"
            },
            {
                "name": "test_model_training_integration",
                "file": "tests/test_integration.py",
                "duration": 5.1,
                "status": "PASSED"
            },
            {
                "name": "test_invalid_model_parameters",
                "file": "tests/test_validation.py",
                "duration": 0.9,
                "status": "FAILED",
                "error": "ValidationError: Model parameters are invalid"
            },
            {
                "name": "test_database_migrations",
                "file": "tests/test_migrations.py",
                "duration": 3.2,
                "status": "PASSED"
            },
            {
                "name": "test_api_rate_limiting",
                "file": "tests/test_api.py",
                "duration": 4.8,
                "status": "PASSED"
            },
            {
                "name": "test_concurrent_model_requests",
                "file": "tests/test_concurrency.py",
                "duration": 8.5,
                "status": "PASSED"
            },
            {
                "name": "test_memory_usage_optimization",
                "file": "tests/test_performance.py",
                "duration": 6.3,
                "status": "PASSED"
            },
            {
                "name": "test_model_response_formatting",
                "file": "tests/test_formatting.py",
                "duration": 1.1,
                "status": "FAILED",
                "error": "AssertionError: Expected JSON format, got plain text"
            },
            {
                "name": "test_websocket_connection",
                "file": "tests/test_websocket.py",
                "duration": 2.0,
                "status": "PASSED"
            },
            {
                "name": "test_dashboard_rendering",
                "file": "tests/test_dashboard.py",
                "duration": 1.7,
                "status": "PASSED"
            }
        ]

        total_tests = len(test_scenarios)

        # 1. Start test run
        print("🚀 Starting test run...")
        self.send_event({
            "type": "test_run_start",
            "run_id": self.run_id,
            "test_command": "pytest tests/ --dashboard --dashboard-websocket -v",
            "total_tests": total_tests
        })

        await asyncio.sleep(1)

        # 2. Execute tests with realistic timing
        for i, test in enumerate(test_scenarios, 1):
            print(f"🧪 Running test {i}/{total_tests}: {test['name']}")

            # Test start
            self.send_event({
                "type": "test_start",
                "run_id": self.run_id,
                "test_name": test['name'],
                "test_file": test['file']
            })

            # Simulate test execution time
            await asyncio.sleep(min(test['duration'], 2.0))  # Cap at 2s for demo

            # Test end
            event_data = {
                "type": "test_end",
                "run_id": self.run_id,
                "test_name": test['name'],
                "status": test['status'],
                "duration": test['duration']
            }

            if test.get('error'):
                event_data['error_message'] = test['error']

            self.send_event(event_data)

            # Progress update
            self.send_event({
                "type": "test_progress",
                "run_id": self.run_id,
                "completed": i,
                "total": total_tests,
                "current_test": test_scenarios[i]['name'] if i < total_tests else None
            })

            # Simulate coverage updates for some tests
            if random.random() < 0.4:  # 40% chance
                coverage_percent = random.uniform(75, 95)
                self.send_event({
                    "type": "coverage_update",
                    "run_id": self.run_id,
                    "file_path": test['file'],
                    "coverage_percent": coverage_percent
                })

            await asyncio.sleep(0.5)  # Brief pause between tests

        # 3. Calculate final stats
        passed_tests = sum(1 for t in test_scenarios if t['status'] == 'PASSED')
        failed_tests = sum(1 for t in test_scenarios if t['status'] == 'FAILED')
        total_duration = sum(t['duration'] for t in test_scenarios)

        # 4. End test run
        print(f"✅ Test run completed: {passed_tests}/{total_tests} passed")
        self.send_event({
            "type": "test_run_end",
            "run_id": self.run_id,
            "duration": total_duration,
            "stats": {
                "total": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "skipped": 0,
                "error": 0
            }
        })

        print("\n🎉 Demo completed! Check the dashboard for real-time updates.")
        print(f"📊 Final Results: {passed_tests} passed, {failed_tests} failed")
        print(f"⏱️  Total Duration: {total_duration:.1f} seconds")

    async def simulate_quick_test(self):
        """Simulate a quick test for rapid demonstration."""
        print("⚡ Running quick test demo...")

        quick_run_id = f"quick-{int(time.time())}"

        # Quick test sequence
        events = [
            {
                "type": "test_run_start",
                "run_id": quick_run_id,
                "test_command": "pytest tests/test_quick.py",
                "total_tests": 3
            },
            {
                "type": "test_start",
                "run_id": quick_run_id,
                "test_name": "test_basic_functionality",
                "test_file": "tests/test_quick.py"
            },
            {
                "type": "test_end",
                "run_id": quick_run_id,
                "test_name": "test_basic_functionality",
                "status": "PASSED",
                "duration": 0.5
            },
            {
                "type": "test_progress",
                "run_id": quick_run_id,
                "completed": 1,
                "total": 3
            },
            {
                "type": "test_start",
                "run_id": quick_run_id,
                "test_name": "test_edge_cases",
                "test_file": "tests/test_quick.py"
            },
            {
                "type": "test_end",
                "run_id": quick_run_id,
                "test_name": "test_edge_cases",
                "status": "PASSED",
                "duration": 0.8
            },
            {
                "type": "test_progress",
                "run_id": quick_run_id,
                "completed": 2,
                "total": 3
            },
            {
                "type": "test_start",
                "run_id": quick_run_id,
                "test_name": "test_performance",
                "test_file": "tests/test_quick.py"
            },
            {
                "type": "test_end",
                "run_id": quick_run_id,
                "test_name": "test_performance",
                "status": "PASSED",
                "duration": 1.2
            },
            {
                "type": "test_run_end",
                "run_id": quick_run_id,
                "duration": 2.5,
                "stats": {
                    "total": 3,
                    "passed": 3,
                    "failed": 0,
                    "skipped": 0
                }
            }
        ]

        for event in events:
            self.send_event(event)
            await asyncio.sleep(0.8)

        print("✅ Quick test demo completed!")

    async def simulate_failing_tests(self):
        """Simulate a test run with multiple failures for error handling demo."""
        print("💥 Running failing tests demo...")

        failing_run_id = f"failing-{int(time.time())}"

        # Test run with failures
        self.send_event({
            "type": "test_run_start",
            "run_id": failing_run_id,
            "test_command": "pytest tests/test_failures.py",
            "total_tests": 4
        })

        await asyncio.sleep(1)

        failing_tests = [
            {
                "name": "test_connection_timeout",
                "status": "FAILED",
                "error": "ConnectionTimeoutError: Failed to connect to Ollama server after 30s"
            },
            {
                "name": "test_invalid_response",
                "status": "FAILED",
                "error": "JSONDecodeError: Expecting value: line 1 column 1 (char 0)"
            },
            {
                "name": "test_memory_overflow",
                "status": "FAILED",
                "error": "MemoryError: Unable to allocate 8.5 GB for model loading"
            },
            {
                "name": "test_cleanup_success",
                "status": "PASSED",
                "error": None
            }
        ]

        for i, test in enumerate(failing_tests, 1):
            # Test start
            self.send_event({
                "type": "test_start",
                "run_id": failing_run_id,
                "test_name": test['name'],
                "test_file": "tests/test_failures.py"
            })

            await asyncio.sleep(1.5)

            # Test end with error
            event_data = {
                "type": "test_end",
                "run_id": failing_run_id,
                "test_name": test['name'],
                "status": test['status'],
                "duration": random.uniform(0.5, 2.0)
            }

            if test['error']:
                event_data['error_message'] = test['error']

            self.send_event(event_data)

            # Progress
            self.send_event({
                "type": "test_progress",
                "run_id": failing_run_id,
                "completed": i,
                "total": 4
            })

            await asyncio.sleep(0.5)

        # End with mostly failures
        self.send_event({
            "type": "test_run_end",
            "run_id": failing_run_id,
            "duration": 8.0,
            "stats": {
                "total": 4,
                "passed": 1,
                "failed": 3,
                "skipped": 0
            }
        })

        print("❌ Failing tests demo completed!")

    def check_server_status(self):
        """Check if the dashboard server is running."""
        try:
            response = requests.get(f"{self.server_url}/api/health", timeout=5.0)
            if response.status_code == 200:
                print("✅ Dashboard server is running and healthy")
                return True
            else:
                print(f"⚠️  Server responded with status {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Cannot connect to dashboard server: {e}")
            print(f"   Make sure the server is running on {self.server_url}")
            return False

    async def run_demo(self, demo_type="full"):
        """Run the selected demo type."""
        print("🎭 Django-Ollama WebSocket Dashboard Demo")
        print("=" * 50)

        if not self.check_server_status():
            print("\n💡 To start the dashboard server:")
            print("   cd test_dashboard")
            print("   python server.py --port 8080")
            print("   Then open http://localhost:8080 in your browser")
            return False

        print(f"\n🌐 Dashboard URL: {self.server_url}")
        print("👀 Open the dashboard in your browser to see live updates!")
        print("\nStarting demo in 3 seconds...")
        await asyncio.sleep(3)

        if demo_type == "full":
            await self.simulate_django_test_suite()
        elif demo_type == "quick":
            await self.simulate_quick_test()
        elif demo_type == "failing":
            await self.simulate_failing_tests()
        elif demo_type == "all":
            await self.simulate_quick_test()
            await asyncio.sleep(2)
            await self.simulate_failing_tests()
            await asyncio.sleep(2)
            await self.simulate_django_test_suite()

        return True


async def main():
    """Main demo function."""
    import sys

    demo_types = {
        "full": "Complete Django test suite simulation",
        "quick": "Quick 3-test demonstration",
        "failing": "Tests with failures and errors",
        "all": "All demo types in sequence"
    }

    if len(sys.argv) > 1 and sys.argv[1] in demo_types:
        demo_type = sys.argv[1]
    else:
        print("🎯 Available demo types:")
        for key, desc in demo_types.items():
            print(f"   {key:8} - {desc}")
        print(f"\nUsage: python {sys.argv[0]} [demo_type]")
        print("Default: full")
        demo_type = "full"

    demo = WebSocketDemo()
    success = await demo.run_demo(demo_type)

    if success:
        print("\n🎉 Demo completed successfully!")
        print("The WebSocket system is working and broadcasting events.")
    else:
        print("\n❌ Demo failed to complete.")

    return 0 if success else 1


if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))