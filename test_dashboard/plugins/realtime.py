"""
Real-time WebSocket integration for live dashboard updates.

This module provides WebSocket broadcasting capabilities to update
the dashboard UI in real-time as tests are executed.
"""

import json
import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import threading
import queue
from pathlib import Path

# Optional WebSocket imports
try:
    import websockets
    import websockets.server
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    logging.warning("WebSockets not available. Install 'websockets' package for real-time features.")


class RealTimeBroadcaster:
    """
    WebSocket broadcaster for real-time test dashboard updates.

    Manages WebSocket connections and broadcasts test events to connected
    dashboard clients for live monitoring.
    """

    def __init__(self, port: int = 8765):
        self.port = port
        self.clients: set = set()
        self.server = None
        self.event_queue = queue.Queue()
        self.running = False
        self.thread = None
        self.websockets_available = WEBSOCKETS_AVAILABLE

        # Message types
        self.MESSAGE_TYPES = {
            'TEST_RUN_START': 'test_run_start',
            'TEST_RUN_END': 'test_run_end',
            'TEST_START': 'test_start',
            'TEST_END': 'test_end',
            'TEST_PROGRESS': 'test_progress',
            'COVERAGE_UPDATE': 'coverage_update',
            'STATUS_UPDATE': 'status_update'
        }

        self.logger = logging.getLogger(__name__)

        if not self.websockets_available:
            self.logger.warning("WebSockets not available - real-time features disabled")

    async def register_client(self, websocket, path):
        """Register a new WebSocket client."""
        self.clients.add(websocket)
        self.logger.info(f"Dashboard client connected: {websocket.remote_address}")

        try:
            # Send welcome message with current status
            welcome_msg = {
                'type': 'connection_established',
                'timestamp': datetime.now().isoformat(),
                'message': 'Connected to test dashboard'
            }
            await websocket.send(json.dumps(welcome_msg))

            # Keep connection alive
            await websocket.wait_closed()

        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.clients.discard(websocket)
            self.logger.info(f"Dashboard client disconnected: {websocket.remote_address}")

    async def broadcast_message(self, message: Dict[str, Any]):
        """Broadcast a message to all connected clients."""
        if not self.clients:
            return

        # Add timestamp if not present
        if 'timestamp' not in message:
            message['timestamp'] = datetime.now().isoformat()

        message_json = json.dumps(message)
        disconnected_clients = set()

        for client in self.clients:
            try:
                await client.send(message_json)
            except websockets.exceptions.ConnectionClosed:
                disconnected_clients.add(client)

        # Remove disconnected clients
        self.clients -= disconnected_clients

    def start_server(self):
        """Start the WebSocket server in a background thread."""
        if self.running or not self.websockets_available:
            if not self.websockets_available:
                self.logger.info("WebSocket server not started - websockets package not available")
            return

        self.running = True
        self.thread = threading.Thread(target=self._run_server, daemon=True)
        self.thread.start()
        self.logger.info(f"Real-time broadcaster starting on port {self.port}")

    def stop_server(self):
        """Stop the WebSocket server."""
        self.running = False
        if self.server:
            self.server.close()

    def _run_server(self):
        """Run the WebSocket server event loop."""
        async def run():
            self.server = await websockets.server.serve(
                self.register_client,
                "localhost",
                self.port,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=10
            )
            self.logger.info(f"Real-time broadcaster listening on ws://localhost:{self.port}")

            # Process event queue
            while self.running:
                try:
                    # Check for events to broadcast
                    while not self.event_queue.empty():
                        try:
                            event = self.event_queue.get_nowait()
                            await self.broadcast_message(event)
                        except queue.Empty:
                            break

                    await asyncio.sleep(0.1)
                except Exception as e:
                    self.logger.error(f"Error in broadcaster loop: {e}")

        try:
            asyncio.run(run())
        except Exception as e:
            self.logger.error(f"WebSocket server error: {e}")

    def queue_event(self, event: Dict[str, Any]):
        """Queue an event for broadcasting."""
        try:
            self.event_queue.put(event, block=False)
        except queue.Full:
            self.logger.warning("Event queue full, dropping event")

    # Event broadcasting methods
    def broadcast_test_run_start(self, run_id: str, test_command: str, total_tests: int = 0):
        """Broadcast test run start event."""
        event = {
            'type': self.MESSAGE_TYPES['TEST_RUN_START'],
            'run_id': run_id,
            'test_command': test_command,
            'total_tests': total_tests,
        }
        self.queue_event(event)

    def broadcast_test_run_end(self, run_id: str, duration: float, stats: Dict[str, int]):
        """Broadcast test run end event."""
        event = {
            'type': self.MESSAGE_TYPES['TEST_RUN_END'],
            'run_id': run_id,
            'duration': duration,
            'stats': stats
        }
        self.queue_event(event)

    def broadcast_test_start(self, run_id: str, test_name: str, test_file: str):
        """Broadcast individual test start event."""
        event = {
            'type': self.MESSAGE_TYPES['TEST_START'],
            'run_id': run_id,
            'test_name': test_name,
            'test_file': test_file
        }
        self.queue_event(event)

    def broadcast_test_end(self, run_id: str, test_name: str, status: str,
                          duration: float, error_message: str = None):
        """Broadcast individual test end event."""
        event = {
            'type': self.MESSAGE_TYPES['TEST_END'],
            'run_id': run_id,
            'test_name': test_name,
            'status': status,
            'duration': duration
        }
        if error_message:
            event['error_message'] = error_message
        self.queue_event(event)

    def broadcast_progress_update(self, run_id: str, completed: int, total: int,
                                 current_test: str = None):
        """Broadcast test progress update."""
        event = {
            'type': self.MESSAGE_TYPES['TEST_PROGRESS'],
            'run_id': run_id,
            'completed': completed,
            'total': total,
            'progress_percent': (completed / total * 100) if total > 0 else 0
        }
        if current_test:
            event['current_test'] = current_test
        self.queue_event(event)

    def broadcast_coverage_update(self, run_id: str, file_path: str, coverage_percent: float):
        """Broadcast coverage update event."""
        event = {
            'type': self.MESSAGE_TYPES['COVERAGE_UPDATE'],
            'run_id': run_id,
            'file_path': file_path,
            'coverage_percent': coverage_percent
        }
        self.queue_event(event)


class DashboardWebSocketMixin:
    """
    Mixin for pytest plugin to add real-time WebSocket broadcasting.

    This mixin can be added to the main pytest plugin to enable
    real-time dashboard updates via the FastAPI WebSocket server.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.broadcaster: Optional[RealTimeBroadcaster] = None
        self.websocket_enabled = False
        self.fastapi_websocket_manager = None

    def setup_realtime_broadcasting(self, port: int = 8765):
        """Setup real-time WebSocket broadcasting."""
        try:
            # Try to use FastAPI WebSocket manager if available
            if self._connect_to_fastapi_websocket():
                self.websocket_enabled = True
                logging.info("Real-time dashboard broadcasting enabled via FastAPI WebSocket")
            else:
                # Fallback to standalone WebSocket server
                self.broadcaster = RealTimeBroadcaster(port)
                self.broadcaster.start_server()
                self.websocket_enabled = True
                logging.info("Real-time dashboard broadcasting enabled via standalone server")
        except Exception as e:
            logging.warning(f"Failed to setup real-time broadcasting: {e}")
            self.websocket_enabled = False

    def _connect_to_fastapi_websocket(self):
        """Attempt to connect to FastAPI WebSocket manager."""
        try:
            import httpx
            import asyncio

            # Check if FastAPI server is running
            response = httpx.get('http://localhost:8080/api/websocket/status', timeout=2.0)
            if response.status_code == 200:
                # FastAPI server is available, we can use HTTP calls to trigger broadcasts
                self.fastapi_websocket_manager = 'http://localhost:8080'
                return True
        except Exception:
            pass

        return False

    def cleanup_realtime_broadcasting(self):
        """Cleanup WebSocket broadcasting."""
        if self.broadcaster:
            self.broadcaster.stop_server()
        self.websocket_enabled = False
        self.fastapi_websocket_manager = None

    # Broadcasting helper methods
    def _broadcast_if_enabled(self, method_name: str, *args, **kwargs):
        """Helper to broadcast events if WebSocket is enabled."""
        if not self.websocket_enabled:
            return

        if self.fastapi_websocket_manager:
            # Use FastAPI WebSocket manager via HTTP API
            try:
                self._trigger_fastapi_broadcast(method_name, *args, **kwargs)
            except Exception as e:
                logging.warning(f"Failed to broadcast via FastAPI: {e}")
        elif self.broadcaster:
            # Use standalone broadcaster
            method = getattr(self.broadcaster, method_name)
            method(*args, **kwargs)

    def _trigger_fastapi_broadcast(self, method_name: str, *args, **kwargs):
        """Trigger broadcast via FastAPI WebSocket manager."""
        import httpx
        import asyncio

        # Map method names to event types
        event_mapping = {
            'broadcast_test_run_start': 'test_run_start',
            'broadcast_test_run_end': 'test_run_end',
            'broadcast_test_start': 'test_start',
            'broadcast_test_end': 'test_end',
            'broadcast_progress_update': 'test_progress',
            'broadcast_coverage_update': 'coverage_update'
        }

        event_type = event_mapping.get(method_name)
        if not event_type:
            return

        # Create event data based on method and arguments
        event_data = {'type': event_type}

        if method_name == 'broadcast_test_run_start':
            event_data.update({
                'run_id': args[0] if args else 'unknown',
                'test_command': args[1] if len(args) > 1 else '',
                'total_tests': args[2] if len(args) > 2 else 0
            })
        elif method_name == 'broadcast_test_run_end':
            event_data.update({
                'run_id': args[0] if args else 'unknown',
                'duration': args[1] if len(args) > 1 else 0,
                'stats': args[2] if len(args) > 2 else {}
            })
        elif method_name == 'broadcast_test_start':
            event_data.update({
                'run_id': args[0] if args else 'unknown',
                'test_name': args[1] if len(args) > 1 else '',
                'test_file': args[2] if len(args) > 2 else ''
            })
        elif method_name == 'broadcast_test_end':
            event_data.update({
                'run_id': args[0] if args else 'unknown',
                'test_name': args[1] if len(args) > 1 else '',
                'status': args[2] if len(args) > 2 else 'UNKNOWN',
                'duration': args[3] if len(args) > 3 else 0,
                'error_message': args[4] if len(args) > 4 else None
            })
        elif method_name == 'broadcast_progress_update':
            event_data.update({
                'run_id': args[0] if args else 'unknown',
                'completed': args[1] if len(args) > 1 else 0,
                'total': args[2] if len(args) > 2 else 0,
                'current_test': args[3] if len(args) > 3 else None
            })
        elif method_name == 'broadcast_coverage_update':
            event_data.update({
                'run_id': args[0] if args else 'unknown',
                'file_path': args[1] if len(args) > 1 else '',
                'coverage_percent': args[2] if len(args) > 2 else 0
            })

        # Send to FastAPI server to trigger broadcast
        try:
            response = httpx.post(
                f'{self.fastapi_websocket_manager}/api/test/simulate-event',
                json=event_data,
                timeout=1.0
            )
            if response.status_code != 200:
                logging.warning(f"FastAPI broadcast failed: {response.status_code}")
        except Exception as e:
            logging.warning(f"Failed to send broadcast to FastAPI: {e}")


# Global broadcaster instance for easy access
_global_broadcaster: Optional[RealTimeBroadcaster] = None


def get_global_broadcaster() -> Optional[RealTimeBroadcaster]:
    """Get the global broadcaster instance."""
    return _global_broadcaster


def setup_global_broadcaster(port: int = 8765) -> RealTimeBroadcaster:
    """Setup and return the global broadcaster instance."""
    global _global_broadcaster

    if _global_broadcaster is None:
        _global_broadcaster = RealTimeBroadcaster(port)
        _global_broadcaster.start_server()

    return _global_broadcaster


def cleanup_global_broadcaster():
    """Cleanup the global broadcaster instance."""
    global _global_broadcaster

    if _global_broadcaster:
        _global_broadcaster.stop_server()
        _global_broadcaster = None