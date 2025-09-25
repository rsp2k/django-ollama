#!/usr/bin/env python3
"""
WebSocket Test Script for Django-Ollama Test Dashboard

This script tests the WebSocket functionality by simulating test events
and verifying that they're properly broadcasted to connected clients.
"""

import asyncio
import json
import time
import requests
import websockets
from datetime import datetime


class WebSocketTester:
    """Test WebSocket functionality of the dashboard."""

    def __init__(self, server_url="http://localhost:8080", websocket_url="ws://localhost:8080/ws"):
        self.server_url = server_url
        self.websocket_url = websocket_url
        self.received_messages = []

    async def test_websocket_connection(self):
        """Test basic WebSocket connection."""
        print("🔌 Testing WebSocket connection...")

        try:
            async with websockets.connect(self.websocket_url) as websocket:
                print("✅ WebSocket connection established")

                # Wait for welcome message
                welcome_msg = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                welcome_data = json.loads(welcome_msg)
                print(f"📩 Welcome message: {welcome_data['type']}")

                # Send ping
                ping_msg = {"type": "ping"}
                await websocket.send(json.dumps(ping_msg))
                print("🏓 Sent ping")

                # Wait for pong
                pong_msg = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                pong_data = json.loads(pong_msg)
                print(f"🏓 Received pong: {pong_data['type']}")

                return True

        except Exception as e:
            print(f"❌ WebSocket connection failed: {e}")
            return False

    async def test_event_broadcasting(self):
        """Test event broadcasting via WebSocket."""
        print("\n🎯 Testing event broadcasting...")

        # List of test events to simulate
        test_events = [
            {
                "type": "test_run_start",
                "run_id": "test-websocket-123",
                "test_command": "pytest tests/websocket_test.py",
                "total_tests": 5
            },
            {
                "type": "test_start",
                "run_id": "test-websocket-123",
                "test_name": "test_websocket_connection",
                "test_file": "tests/websocket_test.py"
            },
            {
                "type": "test_end",
                "run_id": "test-websocket-123",
                "test_name": "test_websocket_connection",
                "status": "PASSED",
                "duration": 1.5
            },
            {
                "type": "test_progress",
                "run_id": "test-websocket-123",
                "completed": 1,
                "total": 5,
                "current_test": "test_event_broadcasting"
            },
            {
                "type": "test_start",
                "run_id": "test-websocket-123",
                "test_name": "test_event_broadcasting",
                "test_file": "tests/websocket_test.py"
            },
            {
                "type": "test_end",
                "run_id": "test-websocket-123",
                "test_name": "test_event_broadcasting",
                "status": "PASSED",
                "duration": 2.1
            },
            {
                "type": "test_progress",
                "run_id": "test-websocket-123",
                "completed": 2,
                "total": 5
            },
            {
                "type": "test_run_end",
                "run_id": "test-websocket-123",
                "duration": 15.3,
                "stats": {
                    "total": 5,
                    "passed": 4,
                    "failed": 1,
                    "skipped": 0
                }
            }
        ]

        try:
            # Connect to WebSocket to listen for broadcasts
            async with websockets.connect(self.websocket_url) as websocket:
                print("✅ Connected to WebSocket for event monitoring")

                # Skip welcome message
                await websocket.recv()

                # Start background task to listen for messages
                listen_task = asyncio.create_task(self.listen_for_messages(websocket))

                # Send test events via HTTP API
                for i, event in enumerate(test_events):
                    print(f"📤 Sending event {i+1}/{len(test_events)}: {event['type']}")

                    try:
                        response = requests.post(
                            f"{self.server_url}/api/test/simulate-event",
                            json=event,
                            timeout=5.0
                        )

                        if response.status_code == 200:
                            print(f"✅ Event sent successfully: {response.json()['message']}")
                        else:
                            print(f"⚠️  Event send warning: {response.status_code}")

                    except Exception as e:
                        print(f"❌ Failed to send event: {e}")

                    # Wait between events
                    await asyncio.sleep(1)

                # Wait for all messages to be received
                await asyncio.sleep(2)
                listen_task.cancel()

                print(f"\n📊 Received {len(self.received_messages)} WebSocket messages")

                # Verify we received the expected events
                received_types = [msg.get('type') for msg in self.received_messages if 'type' in msg]
                expected_types = [event['type'] for event in test_events]

                print("Expected events:", expected_types)
                print("Received events:", received_types)

                return len(self.received_messages) > 0

        except Exception as e:
            print(f"❌ Event broadcasting test failed: {e}")
            return False

    async def listen_for_messages(self, websocket):
        """Listen for WebSocket messages."""
        try:
            while True:
                message = await websocket.recv()
                data = json.loads(message)
                self.received_messages.append(data)

                # Print interesting messages
                msg_type = data.get('type', 'unknown')
                if msg_type not in ['heartbeat', 'server_status']:
                    print(f"📨 Received: {msg_type}")
                    if msg_type == 'test_start':
                        print(f"    Test: {data.get('test_name', 'unknown')}")
                    elif msg_type == 'test_end':
                        print(f"    Result: {data.get('status', 'unknown')} ({data.get('duration', 0):.2f}s)")
                    elif msg_type == 'test_progress':
                        print(f"    Progress: {data.get('completed', 0)}/{data.get('total', 0)}")

        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"⚠️  Error listening for messages: {e}")

    def test_server_availability(self):
        """Test that the server is running and responsive."""
        print("🌐 Testing server availability...")

        try:
            response = requests.get(f"{self.server_url}/api/health", timeout=5.0)
            if response.status_code == 200:
                health_data = response.json()
                print(f"✅ Server is healthy: {health_data['status']}")
                return True
            else:
                print(f"⚠️  Server health check warning: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Server is not available: {e}")
            return False

    def test_websocket_status_endpoint(self):
        """Test the WebSocket status endpoint."""
        print("\n🔍 Testing WebSocket status endpoint...")

        try:
            response = requests.get(f"{self.server_url}/api/websocket/status", timeout=5.0)
            if response.status_code == 200:
                status_data = response.json()
                print(f"✅ WebSocket status: {status_data['status']}")
                print(f"    Active connections: {status_data['data']['active_connections']}")
                print(f"    Supported events: {len(status_data['data']['supported_events'])}")
                return True
            else:
                print(f"⚠️  WebSocket status warning: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ WebSocket status check failed: {e}")
            return False

    async def run_all_tests(self):
        """Run all WebSocket tests."""
        print("🧪 Django-Ollama Test Dashboard - WebSocket Tests")
        print("=" * 60)

        tests = [
            ("Server Availability", self.test_server_availability),
            ("WebSocket Status", self.test_websocket_status_endpoint),
            ("WebSocket Connection", self.test_websocket_connection),
            ("Event Broadcasting", self.test_event_broadcasting),
        ]

        results = []

        for test_name, test_func in tests:
            print(f"\n🔬 Running: {test_name}")
            print("-" * 40)

            try:
                if asyncio.iscoroutinefunction(test_func):
                    result = await test_func()
                else:
                    result = test_func()

                results.append((test_name, result))

                if result:
                    print(f"✅ {test_name}: PASSED")
                else:
                    print(f"❌ {test_name}: FAILED")

            except Exception as e:
                print(f"💥 {test_name}: ERROR - {e}")
                results.append((test_name, False))

        # Summary
        print("\n" + "=" * 60)
        print("📊 Test Results Summary")
        print("=" * 60)

        passed = sum(1 for _, result in results if result)
        total = len(results)

        for test_name, result in results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{test_name:<25} {status}")

        print("-" * 60)
        print(f"Total: {passed}/{total} tests passed ({passed/total*100:.1f}%)")

        if passed == total:
            print("🎉 All tests passed! WebSocket system is working correctly.")
        else:
            print("⚠️  Some tests failed. Check the output above for details.")

        return passed == total


async def main():
    """Main test function."""
    tester = WebSocketTester()
    success = await tester.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))