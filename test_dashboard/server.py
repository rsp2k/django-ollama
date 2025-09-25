#!/usr/bin/env python3
"""
Django-Ollama Test Dashboard Web Server

A simple FastAPI-based web server that serves the HTML dashboard
and provides REST API endpoints for test data.
"""

import json
import logging
import os
import sys
import asyncio
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Set

import uvicorn
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent))

from database import TestDashboardDB
from models import TestStatus, TestType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Django-Ollama Test Dashboard",
    description="Real-time test results and coverage analytics dashboard",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database connection
DB_PATH = Path(__file__).parent / "demo_dashboard.db"
db = TestDashboardDB(str(DB_PATH))

# Static files and templates directories
STATIC_DIR = Path(__file__).parent / "static"
TEMPLATES_DIR = Path(__file__).parent / "templates"

# Mount static files
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


class WebSocketConnectionManager:
    """
    WebSocket connection manager for real-time dashboard updates.

    Manages active WebSocket connections and broadcasts events to all connected clients.
    """

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.connection_count = 0
        self.logger = logging.getLogger(f"{__name__}.WebSocketManager")

    async def connect(self, websocket: WebSocket) -> str:
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.add(websocket)
        self.connection_count += 1
        connection_id = f"client-{self.connection_count}"

        self.logger.info(f"WebSocket client connected: {connection_id} (total: {len(self.active_connections)})")

        # Send welcome message
        welcome_message = {
            "type": "connection_established",
            "connection_id": connection_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": "Connected to Django-Ollama Test Dashboard"
        }
        await self._send_to_connection(websocket, welcome_message)

        return connection_id

    def disconnect(self, websocket: WebSocket):
        """Unregister a WebSocket connection."""
        if websocket in self.active_connections:
            self.active_connections.discard(websocket)
            self.logger.info(f"WebSocket client disconnected (remaining: {len(self.active_connections)})")

    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast a message to all connected clients."""
        if not self.active_connections:
            self.logger.debug("No active connections to broadcast to")
            return

        # Add timestamp if not present
        if 'timestamp' not in message:
            message['timestamp'] = datetime.now(timezone.utc).isoformat()

        disconnected_clients = set()
        message_json = json.dumps(message)

        for connection in self.active_connections:
            try:
                await connection.send_text(message_json)
            except Exception as e:
                self.logger.warning(f"Failed to send message to client: {e}")
                disconnected_clients.add(connection)

        # Clean up disconnected clients
        self.active_connections -= disconnected_clients

        if disconnected_clients:
            self.logger.info(f"Cleaned up {len(disconnected_clients)} disconnected clients")

    async def _send_to_connection(self, websocket: WebSocket, message: Dict[str, Any]):
        """Send a message to a specific connection."""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            self.logger.warning(f"Failed to send message to connection: {e}")
            self.disconnect(websocket)

    async def send_server_status(self):
        """Send server status to all connected clients."""
        try:
            summary = db.get_dashboard_summary()
            recent_runs = db.get_recent_test_runs(limit=5)

            status_message = {
                "type": "server_status",
                "status": "healthy",
                "summary": summary,
                "recent_runs": [dashboard_server.format_test_run_for_api(run) for run in recent_runs],
                "active_connections": len(self.active_connections)
            }

            await self.broadcast(status_message)

        except Exception as e:
            self.logger.error(f"Failed to send server status: {e}")

    # Test Event Broadcasting Methods
    async def broadcast_test_run_start(self, run_id: str, test_command: str, total_tests: int = 0):
        """Broadcast test run start event."""
        message = {
            "type": "test_run_start",
            "run_id": run_id,
            "test_command": test_command,
            "total_tests": total_tests,
        }
        await self.broadcast(message)

    async def broadcast_test_run_end(self, run_id: str, duration: float, stats: Dict[str, int]):
        """Broadcast test run end event."""
        message = {
            "type": "test_run_end",
            "run_id": run_id,
            "duration": duration,
            "stats": stats
        }
        await self.broadcast(message)

    async def broadcast_test_start(self, run_id: str, test_name: str, test_file: str):
        """Broadcast individual test start event."""
        message = {
            "type": "test_start",
            "run_id": run_id,
            "test_name": test_name,
            "test_file": test_file
        }
        await self.broadcast(message)

    async def broadcast_test_end(self, run_id: str, test_name: str, status: str,
                                duration: float, error_message: str = None):
        """Broadcast individual test end event."""
        message = {
            "type": "test_end",
            "run_id": run_id,
            "test_name": test_name,
            "status": status,
            "duration": duration
        }
        if error_message:
            message['error_message'] = error_message
        await self.broadcast(message)

    async def broadcast_progress_update(self, run_id: str, completed: int, total: int,
                                       current_test: str = None):
        """Broadcast test progress update."""
        message = {
            "type": "test_progress",
            "run_id": run_id,
            "completed": completed,
            "total": total,
            "progress_percent": (completed / total * 100) if total > 0 else 0
        }
        if current_test:
            message['current_test'] = current_test
        await self.broadcast(message)

    async def broadcast_coverage_update(self, run_id: str, file_path: str, coverage_percent: float):
        """Broadcast coverage update event."""
        message = {
            "type": "coverage_update",
            "run_id": run_id,
            "file_path": file_path,
            "coverage_percent": coverage_percent
        }
        await self.broadcast(message)


class DashboardServer:
    """Main dashboard server class."""

    def __init__(self, database: TestDashboardDB):
        self.db = database

    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get complete dashboard data."""
        try:
            summary = self.db.get_dashboard_summary()
            recent_runs = self.db.get_recent_test_runs(limit=10)
            trend_data = self.db.get_trend_data(days=30)

            return {
                "summary": summary,
                "recent_runs": [run.to_dict() for run in recent_runs],
                "trends": trend_data,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to get dashboard data: {e}")
            return {
                "summary": {},
                "recent_runs": [],
                "trends": [],
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    def format_test_run_for_api(self, run) -> Dict[str, Any]:
        """Format test run for API response."""
        if run is None:
            return {}

        return {
            "id": run.id,
            "run_id": run.run_id,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "finished_at": run.finished_at.isoformat() if run.finished_at else None,
            "status": run.status.value,
            "total_tests": run.total_tests,
            "passed_tests": run.passed_tests,
            "failed_tests": run.failed_tests,
            "skipped_tests": run.skipped_tests,
            "error_tests": run.error_tests,
            "duration_seconds": run.duration_seconds,
            "success_rate": run.success_rate,
            "test_command": run.test_command,
            "environment_info": run.environment_info,
            "git_commit": run.git_commit,
            "git_branch": run.git_branch,
            "created_at": run.created_at.isoformat() if run.created_at else None
        }


# Initialize dashboard server and WebSocket manager
dashboard_server = DashboardServer(db)
websocket_manager = WebSocketConnectionManager()


@app.get("/", response_class=HTMLResponse)
async def dashboard_home():
    """Serve the main dashboard HTML."""
    try:
        dashboard_file = TEMPLATES_DIR / "dashboard.html"
        if not dashboard_file.exists():
            raise HTTPException(status_code=404, detail="Dashboard template not found")

        with open(dashboard_file, 'r', encoding='utf-8') as f:
            content = f.read()

        return HTMLResponse(content=content)

    except Exception as e:
        logger.error(f"Failed to serve dashboard: {e}")
        raise HTTPException(status_code=500, detail="Failed to load dashboard")


@app.get("/api/dashboard/summary")
async def get_dashboard_summary():
    """Get dashboard summary statistics."""
    try:
        summary = db.get_dashboard_summary()
        return {
            "status": "success",
            "data": summary,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get dashboard summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to get dashboard summary")


@app.get("/api/dashboard/recent-runs")
async def get_recent_runs(limit: int = 20, status: Optional[str] = None):
    """Get recent test runs."""
    try:
        status_filter = None
        if status:
            try:
                status_filter = TestStatus(status.upper())
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

        runs = db.get_recent_test_runs(limit=limit, status=status_filter)
        return {
            "status": "success",
            "data": [dashboard_server.format_test_run_for_api(run) for run in runs],
            "total": len(runs),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get recent runs: {e}")
        raise HTTPException(status_code=500, detail="Failed to get recent runs")


@app.get("/api/dashboard/trends")
async def get_trend_data(days: int = 30):
    """Get trend data for the specified number of days."""
    try:
        if days < 1 or days > 365:
            raise HTTPException(status_code=400, detail="Days must be between 1 and 365")

        trend_data = db.get_trend_data(days=days)
        return {
            "status": "success",
            "data": trend_data,
            "period_days": days,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get trend data: {e}")
        raise HTTPException(status_code=500, detail="Failed to get trend data")


@app.get("/api/dashboard/runs/{run_id}")
async def get_run_details(run_id: str):
    """Get detailed information about a specific test run."""
    try:
        run = db.get_test_run(run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Test run not found")

        return {
            "status": "success",
            "data": dashboard_server.format_test_run_for_api(run),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get run details for {run_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get run details")


@app.get("/api/dashboard/runs/{run_id}/results")
async def get_run_results(run_id: str, limit: Optional[int] = None, offset: int = 0):
    """Get test results for a specific run."""
    try:
        results = db.get_test_results(run_id, limit=limit, offset=offset)

        return {
            "status": "success",
            "data": [result.to_dict() for result in results],
            "total": len(results),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get run results for {run_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get run results")


@app.get("/api/dashboard/runs/{run_id}/coverage")
async def get_run_coverage(run_id: str):
    """Get coverage summary for a specific run."""
    try:
        coverage = db.get_coverage_summary(run_id)

        return {
            "status": "success",
            "data": coverage,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get coverage for {run_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get coverage data")


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Test database connection
        summary = db.get_dashboard_summary()

        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": "1.0.0"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": "1.0.0"
        }


@app.get("/api/stats")
async def get_system_stats():
    """Get system and database statistics."""
    try:
        # Get database file size
        db_size = 0
        if DB_PATH.exists():
            db_size = DB_PATH.stat().st_size

        # Get recent activity
        recent_runs = db.get_recent_test_runs(limit=5)

        return {
            "status": "success",
            "data": {
                "database_size_bytes": db_size,
                "database_size_mb": round(db_size / (1024 * 1024), 2),
                "recent_runs_count": len(recent_runs),
                "uptime_seconds": 0,  # Would need to track this
                "last_activity": recent_runs[0].started_at.isoformat() if recent_runs else None
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get system stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get system statistics")


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Custom 404 handler."""
    return {
        "status": "error",
        "error": "Not found",
        "detail": f"The requested path '{request.url.path}' was not found",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    """Custom 500 handler."""
    return {
        "status": "error",
        "error": "Internal server error",
        "detail": "An unexpected error occurred",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time dashboard updates.

    Provides live updates for:
    - Test execution progress
    - Test results and status changes
    - Coverage updates
    - Server statistics
    """
    connection_id = await websocket_manager.connect(websocket)

    try:
        # Send initial server status
        await websocket_manager.send_server_status()

        while True:
            try:
                # Wait for ping/pong or client messages
                message = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)

                # Handle client messages
                try:
                    data = json.loads(message)
                    message_type = data.get("type")

                    if message_type == "ping":
                        # Respond to ping with pong
                        pong_response = {
                            "type": "pong",
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                        await websocket.send_text(json.dumps(pong_response))

                    elif message_type == "request_status":
                        # Send current dashboard status
                        await websocket_manager.send_server_status()

                    elif message_type == "subscribe_run":
                        # Subscribe to specific test run updates
                        run_id = data.get("run_id")
                        if run_id:
                            # For now, acknowledge subscription
                            # In the future, this could filter broadcasts per run
                            response = {
                                "type": "subscription_confirmed",
                                "run_id": run_id,
                                "message": f"Subscribed to updates for run {run_id}"
                            }
                            await websocket.send_text(json.dumps(response))

                    else:
                        # Unknown message type
                        error_response = {
                            "type": "error",
                            "message": f"Unknown message type: {message_type}"
                        }
                        await websocket.send_text(json.dumps(error_response))

                except json.JSONDecodeError:
                    error_response = {
                        "type": "error",
                        "message": "Invalid JSON received"
                    }
                    await websocket.send_text(json.dumps(error_response))

            except asyncio.TimeoutError:
                # Send periodic heartbeat
                heartbeat = {
                    "type": "heartbeat",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "connections": len(websocket_manager.active_connections)
                }
                await websocket.send_text(json.dumps(heartbeat))

    except WebSocketDisconnect:
        logger.info(f"WebSocket client {connection_id} disconnected normally")
    except Exception as e:
        logger.error(f"WebSocket error for client {connection_id}: {e}")
    finally:
        websocket_manager.disconnect(websocket)


# API endpoint to trigger test events (for testing WebSocket functionality)
@app.post("/api/test/simulate-event")
async def simulate_test_event(event_data: Dict[str, Any]):
    """
    Simulate test events for WebSocket testing.

    This endpoint allows manual triggering of test events to verify
    WebSocket broadcasting functionality.
    """
    try:
        event_type = event_data.get("type")

        if event_type == "test_run_start":
            await websocket_manager.broadcast_test_run_start(
                run_id=event_data.get("run_id", "test-run-123"),
                test_command=event_data.get("test_command", "pytest tests/"),
                total_tests=event_data.get("total_tests", 10)
            )

        elif event_type == "test_start":
            await websocket_manager.broadcast_test_start(
                run_id=event_data.get("run_id", "test-run-123"),
                test_name=event_data.get("test_name", "test_example"),
                test_file=event_data.get("test_file", "tests/test_example.py")
            )

        elif event_type == "test_end":
            await websocket_manager.broadcast_test_end(
                run_id=event_data.get("run_id", "test-run-123"),
                test_name=event_data.get("test_name", "test_example"),
                status=event_data.get("status", "PASSED"),
                duration=event_data.get("duration", 1.5),
                error_message=event_data.get("error_message")
            )

        elif event_type == "test_progress":
            await websocket_manager.broadcast_progress_update(
                run_id=event_data.get("run_id", "test-run-123"),
                completed=event_data.get("completed", 5),
                total=event_data.get("total", 10),
                current_test=event_data.get("current_test", "test_current")
            )

        elif event_type == "test_run_end":
            await websocket_manager.broadcast_test_run_end(
                run_id=event_data.get("run_id", "test-run-123"),
                duration=event_data.get("duration", 30.0),
                stats=event_data.get("stats", {
                    "total": 10, "passed": 8, "failed": 1, "skipped": 1
                })
            )

        else:
            raise HTTPException(status_code=400, detail=f"Unknown event type: {event_type}")

        return {
            "status": "success",
            "message": f"Event {event_type} broadcasted",
            "active_connections": len(websocket_manager.active_connections),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to simulate event: {e}")
        raise HTTPException(status_code=500, detail="Failed to simulate event")


@app.get("/api/websocket/status")
async def websocket_status():
    """Get WebSocket connection status."""
    return {
        "status": "success",
        "data": {
            "active_connections": len(websocket_manager.active_connections),
            "websocket_endpoint": "/ws",
            "supported_events": [
                "test_run_start", "test_run_end", "test_start", "test_end",
                "test_progress", "coverage_update", "server_status"
            ]
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


def main():
    """Main entry point for the dashboard server."""
    import argparse

    parser = argparse.ArgumentParser(description="Django-Ollama Test Dashboard Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8080, help="Port to bind to (default: 8080)")
    parser.add_argument("--db", default=str(DB_PATH), help="Database file path")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    parser.add_argument("--log-level", default="info", choices=["debug", "info", "warning", "error"])

    args = parser.parse_args()

    # Update database path if provided
    global db
    if args.db != str(DB_PATH):
        db = TestDashboardDB(args.db)
        global dashboard_server
        dashboard_server = DashboardServer(db)

    logger.info("🧪 Django-Ollama Test Dashboard Server")
    logger.info(f"📊 Database: {args.db}")
    logger.info(f"🌐 Server: http://{args.host}:{args.port}")
    logger.info(f"📚 API Docs: http://{args.host}:{args.port}/api/docs")
    logger.info("🚀 Starting server...")

    try:
        uvicorn.run(
            "server:app",
            host=args.host,
            port=args.port,
            reload=args.reload,
            log_level=args.log_level.lower(),
            access_log=True
        )
    except KeyboardInterrupt:
        logger.info("👋 Server stopped by user")
    except Exception as e:
        logger.error(f"❌ Server failed to start: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()