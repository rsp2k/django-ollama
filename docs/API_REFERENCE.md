# API Reference

Complete reference documentation for the Django-Ollama Test Dashboard REST API and WebSocket interface.

## 📋 API Overview

The Test Dashboard provides a comprehensive REST API for programmatic access to test data and a WebSocket interface for real-time updates.

**Base URL**: `http://localhost:8080/api`
**WebSocket URL**: `ws://localhost:8080/ws`

### Authentication

Currently, the API supports optional authentication. When enabled:

```http
Authorization: Bearer <jwt-token>
# or
X-API-Key: <api-key>
```

### Response Format

All API responses follow this standard format:

```json
{
  "status": "success|error",
  "data": {...},
  "timestamp": "2024-01-01T12:00:00Z",
  "error": "Error message (only on error)",
  "total": 100  // For paginated responses
}
```

## 🔍 Dashboard Endpoints

### Get Dashboard Summary

Get high-level dashboard statistics and metrics.

**Endpoint**: `GET /api/dashboard/summary`

**Response**:
```json
{
  "status": "success",
  "data": {
    "recent_24h": {
      "total_runs": 25,
      "passed_runs": 22,
      "failed_runs": 2,
      "running_runs": 1,
      "avg_duration": 45.6,
      "avg_success_rate": 88.0
    },
    "overall": {
      "total_runs": 1250,
      "last_run_time": "2024-01-01T12:00:00Z",
      "avg_duration": 42.3
    },
    "running_tests": [
      {
        "run_id": "abc-123",
        "started_at": "2024-01-01T12:00:00Z",
        "test_command": "pytest tests/api/"
      }
    ]
  },
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### Get Recent Test Runs

Retrieve recent test runs with optional filtering.

**Endpoint**: `GET /api/dashboard/recent-runs`

**Query Parameters**:
- `limit` (integer, default: 20): Number of runs to return
- `status` (string, optional): Filter by status (PASSED, FAILED, RUNNING, SKIPPED)
- `offset` (integer, default: 0): Pagination offset

**Example Request**:
```http
GET /api/dashboard/recent-runs?limit=10&status=FAILED
```

**Response**:
```json
{
  "status": "success",
  "data": [
    {
      "id": 1,
      "run_id": "abc-123",
      "started_at": "2024-01-01T12:00:00Z",
      "finished_at": "2024-01-01T12:02:30Z",
      "status": "FAILED",
      "total_tests": 150,
      "passed_tests": 145,
      "failed_tests": 3,
      "skipped_tests": 2,
      "error_tests": 0,
      "duration_seconds": 150.5,
      "success_rate": 96.7,
      "test_command": "pytest tests/",
      "environment_info": {
        "python_version": "3.11.0",
        "django_version": "4.2.0"
      },
      "git_commit": "abc123def456",
      "git_branch": "main",
      "created_at": "2024-01-01T12:00:00Z"
    }
  ],
  "total": 1,
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### Get Trend Data

Get historical trend data for dashboard charts.

**Endpoint**: `GET /api/dashboard/trends`

**Query Parameters**:
- `days` (integer, default: 30): Number of days to include (1-365)

**Example Request**:
```http
GET /api/dashboard/trends?days=7
```

**Response**:
```json
{
  "status": "success",
  "data": [
    {
      "date": "2024-01-01",
      "total_runs": 12,
      "passed_runs": 10,
      "failed_runs": 2,
      "avg_duration": 45.2,
      "avg_success_rate": 83.3,
      "total_tests": 1800
    },
    {
      "date": "2023-12-31",
      "total_runs": 8,
      "passed_runs": 8,
      "failed_runs": 0,
      "avg_duration": 38.7,
      "avg_success_rate": 100.0,
      "total_tests": 1200
    }
  ],
  "period_days": 7,
  "timestamp": "2024-01-01T12:00:00Z"
}
```

## 🧪 Test Run Endpoints

### Get Test Run Details

Get detailed information about a specific test run.

**Endpoint**: `GET /api/dashboard/runs/{run_id}`

**Path Parameters**:
- `run_id` (string): Unique test run identifier

**Response**:
```json
{
  "status": "success",
  "data": {
    "id": 1,
    "run_id": "abc-123",
    "started_at": "2024-01-01T12:00:00Z",
    "finished_at": "2024-01-01T12:02:30Z",
    "status": "PASSED",
    "total_tests": 150,
    "passed_tests": 148,
    "failed_tests": 0,
    "skipped_tests": 2,
    "error_tests": 0,
    "duration_seconds": 150.5,
    "success_rate": 98.7,
    "test_command": "pytest --cov=src tests/",
    "environment_info": {
      "python_version": "3.11.0",
      "platform": "linux",
      "django_version": "4.2.0",
      "pytest_version": "7.4.0"
    },
    "git_commit": "abc123def456",
    "git_branch": "feature/new-api",
    "created_at": "2024-01-01T12:00:00Z"
  },
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### Get Test Results

Get individual test results for a specific run.

**Endpoint**: `GET /api/dashboard/runs/{run_id}/results`

**Path Parameters**:
- `run_id` (string): Unique test run identifier

**Query Parameters**:
- `limit` (integer, optional): Number of results to return
- `offset` (integer, default: 0): Pagination offset
- `status` (string, optional): Filter by test status

**Response**:
```json
{
  "status": "success",
  "data": [
    {
      "id": 1,
      "run_id": 1,
      "test_name": "tests/test_models.py::TestChatSession::test_create_session",
      "test_file": "tests/test_models.py",
      "test_class": "TestChatSession",
      "test_method": "test_create_session",
      "test_type": "UNIT",
      "status": "PASSED",
      "duration_seconds": 0.123,
      "error_message": null,
      "error_traceback": null,
      "setup_duration": 0.001,
      "teardown_duration": 0.002,
      "assertions_count": 3,
      "started_at": "2024-01-01T12:00:01Z",
      "finished_at": "2024-01-01T12:00:01.123Z",
      "created_at": "2024-01-01T12:00:01.125Z"
    }
  ],
  "total": 150,
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### Get Coverage Data

Get code coverage information for a test run.

**Endpoint**: `GET /api/dashboard/runs/{run_id}/coverage`

**Response**:
```json
{
  "status": "success",
  "data": {
    "file_count": 45,
    "total_lines": 2500,
    "covered_lines": 2125,
    "line_coverage": 85.0,
    "average_coverage": 84.2,
    "min_coverage": 45.0,
    "max_coverage": 100.0,
    "files": [
      {
        "file_path": "src/django_ollama/models.py",
        "total_lines": 150,
        "covered_lines": 135,
        "missing_lines": [45, 46, 78, 112, 113],
        "excluded_lines": [1, 2, 3],
        "branch_total": 24,
        "branch_covered": 22,
        "missing_branches": [
          [45, 46],
          [78, 79]
        ],
        "coverage_percentage": 90.0
      }
    ]
  },
  "timestamp": "2024-01-01T12:00:00Z"
}
```

## 🛠️ Management Endpoints

### Health Check

Check the health status of the dashboard service.

**Endpoint**: `GET /api/health`

**Response**:
```json
{
  "status": "healthy",
  "database": "connected",
  "timestamp": "2024-01-01T12:00:00Z",
  "version": "1.0.0",
  "uptime_seconds": 3600,
  "last_test_run": "2024-01-01T11:45:00Z"
}
```

### System Statistics

Get system and database statistics.

**Endpoint**: `GET /api/stats`

**Response**:
```json
{
  "status": "success",
  "data": {
    "database_size_bytes": 5242880,
    "database_size_mb": 5.0,
    "recent_runs_count": 25,
    "uptime_seconds": 7200,
    "last_activity": "2024-01-01T11:55:00Z",
    "memory_usage_mb": 52.3,
    "cpu_percent": 1.2,
    "active_connections": 3,
    "total_test_runs": 1250,
    "total_test_results": 187500
  },
  "timestamp": "2024-01-01T12:00:00Z"
}
```

## 🔧 Testing Endpoints

### Simulate Test Events

Manually trigger test events for WebSocket testing (development only).

**Endpoint**: `POST /api/test/simulate-event`

**Request Body**:
```json
{
  "type": "test_run_start",
  "run_id": "test-123",
  "test_command": "pytest tests/",
  "total_tests": 10
}
```

**Event Types**:
- `test_run_start`: Start a new test run
- `test_start`: Start an individual test
- `test_end`: Complete an individual test
- `test_progress`: Update test progress
- `test_run_end`: Complete a test run

**Response**:
```json
{
  "status": "success",
  "message": "Event test_run_start broadcasted",
  "active_connections": 3,
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### WebSocket Status

Get information about WebSocket connections and supported events.

**Endpoint**: `GET /api/websocket/status`

**Response**:
```json
{
  "status": "success",
  "data": {
    "active_connections": 5,
    "websocket_endpoint": "/ws",
    "supported_events": [
      "test_run_start",
      "test_run_end",
      "test_start",
      "test_end",
      "test_progress",
      "coverage_update",
      "server_status"
    ],
    "connection_stats": {
      "total_connected": 25,
      "total_disconnected": 20,
      "messages_sent": 1500,
      "messages_received": 300
    }
  },
  "timestamp": "2024-01-01T12:00:00Z"
}
```

## 🔌 WebSocket Interface

### Connection

Connect to the WebSocket endpoint for real-time updates:

```javascript
const ws = new WebSocket('ws://localhost:8080/ws');

ws.onopen = function(event) {
    console.log('Connected to dashboard WebSocket');
};

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('Received:', data);
};

ws.onerror = function(error) {
    console.error('WebSocket error:', error);
};

ws.onclose = function(event) {
    console.log('WebSocket closed:', event.code, event.reason);
};
```

### Client → Server Messages

#### Ping/Pong Heartbeat
```json
{
  "type": "ping"
}
```

#### Request Status Update
```json
{
  "type": "request_status"
}
```

#### Subscribe to Test Run
```json
{
  "type": "subscribe_run",
  "run_id": "abc-123"
}
```

### Server → Client Messages

#### Connection Established
```json
{
  "type": "connection_established",
  "connection_id": "client-123",
  "timestamp": "2024-01-01T12:00:00Z",
  "message": "Connected to Django-Ollama Test Dashboard"
}
```

#### Test Run Started
```json
{
  "type": "test_run_start",
  "run_id": "abc-123",
  "test_command": "pytest tests/api/",
  "total_tests": 50,
  "git_branch": "feature/new-api",
  "git_commit": "def456",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

#### Individual Test Started
```json
{
  "type": "test_start",
  "run_id": "abc-123",
  "test_name": "tests/api/test_endpoints.py::test_chat_endpoint",
  "test_file": "tests/api/test_endpoints.py",
  "test_class": "TestChatEndpoint",
  "test_method": "test_chat_endpoint",
  "timestamp": "2024-01-01T12:00:01Z"
}
```

#### Individual Test Completed
```json
{
  "type": "test_end",
  "run_id": "abc-123",
  "test_name": "tests/api/test_endpoints.py::test_chat_endpoint",
  "status": "PASSED",
  "duration": 1.234,
  "error_message": null,
  "timestamp": "2024-01-01T12:00:02Z"
}
```

#### Test Progress Update
```json
{
  "type": "test_progress",
  "run_id": "abc-123",
  "completed": 25,
  "total": 50,
  "progress_percent": 50.0,
  "current_test": "tests/api/test_auth.py::test_login",
  "timestamp": "2024-01-01T12:01:00Z"
}
```

#### Coverage Update
```json
{
  "type": "coverage_update",
  "run_id": "abc-123",
  "file_path": "src/django_ollama/api.py",
  "coverage_percent": 85.5,
  "lines_covered": 171,
  "total_lines": 200,
  "timestamp": "2024-01-01T12:02:00Z"
}
```

#### Test Run Completed
```json
{
  "type": "test_run_end",
  "run_id": "abc-123",
  "duration": 45.6,
  "stats": {
    "total": 50,
    "passed": 45,
    "failed": 3,
    "skipped": 2,
    "error": 0
  },
  "success_rate": 90.0,
  "timestamp": "2024-01-01T12:02:30Z"
}
```

#### Server Status Update
```json
{
  "type": "server_status",
  "status": "healthy",
  "summary": {
    "recent_24h": {
      "total_runs": 25,
      "avg_success_rate": 88.0
    }
  },
  "recent_runs": [...],
  "active_connections": 5,
  "timestamp": "2024-01-01T12:00:00Z"
}
```

#### Heartbeat
```json
{
  "type": "heartbeat",
  "timestamp": "2024-01-01T12:00:00Z",
  "connections": 5,
  "uptime_seconds": 3600
}
```

#### Error Messages
```json
{
  "type": "error",
  "error_code": "INVALID_MESSAGE",
  "message": "Invalid JSON received",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

## 📝 Error Handling

### HTTP Status Codes

- `200 OK`: Successful request
- `201 Created`: Resource created successfully
- `400 Bad Request`: Invalid request parameters
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `422 Unprocessable Entity`: Validation error
- `500 Internal Server Error`: Server error

### Error Response Format

```json
{
  "status": "error",
  "error": "Resource not found",
  "detail": "Test run with ID 'invalid-id' was not found",
  "error_code": "NOT_FOUND",
  "timestamp": "2024-01-01T12:00:00Z",
  "request_id": "req-123-456"
}
```

### Common Error Codes

- `INVALID_PARAMETERS`: Request parameters are invalid
- `NOT_FOUND`: Requested resource does not exist
- `DATABASE_ERROR`: Database operation failed
- `WEBSOCKET_ERROR`: WebSocket connection issue
- `RATE_LIMITED`: Too many requests
- `AUTHENTICATION_FAILED`: Invalid credentials
- `VALIDATION_ERROR`: Data validation failed

## 🔒 Rate Limiting

The API implements rate limiting to prevent abuse:

**Default Limits**:
- API endpoints: 100 requests/minute
- WebSocket messages: 10 messages/second
- Global limit: 1000 requests/hour

**Rate Limit Headers**:
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640995200
X-RateLimit-Window: 60
```

**Rate Limit Exceeded Response**:
```json
{
  "status": "error",
  "error": "Rate limit exceeded",
  "detail": "Too many requests. Try again in 60 seconds.",
  "error_code": "RATE_LIMITED",
  "retry_after": 60,
  "timestamp": "2024-01-01T12:00:00Z"
}
```

## 📊 Usage Examples

### Python Client

```python
import requests
import json

# Dashboard API client
class DashboardAPI:
    def __init__(self, base_url="http://localhost:8080/api"):
        self.base_url = base_url
        self.session = requests.Session()

    def get_summary(self):
        response = self.session.get(f"{self.base_url}/dashboard/summary")
        return response.json()

    def get_recent_runs(self, limit=20, status=None):
        params = {"limit": limit}
        if status:
            params["status"] = status
        response = self.session.get(
            f"{self.base_url}/dashboard/recent-runs",
            params=params
        )
        return response.json()

    def get_test_results(self, run_id, limit=None):
        params = {}
        if limit:
            params["limit"] = limit
        response = self.session.get(
            f"{self.base_url}/dashboard/runs/{run_id}/results",
            params=params
        )
        return response.json()

# Usage
api = DashboardAPI()
summary = api.get_summary()
print(f"Success rate: {summary['data']['recent_24h']['avg_success_rate']}%")

recent_runs = api.get_recent_runs(limit=5, status="FAILED")
for run in recent_runs['data']:
    print(f"Failed run: {run['run_id']} - {run['test_command']}")
```

### JavaScript Client

```javascript
class DashboardAPI {
    constructor(baseUrl = 'http://localhost:8080/api') {
        this.baseUrl = baseUrl;
    }

    async getSummary() {
        const response = await fetch(`${this.baseUrl}/dashboard/summary`);
        return await response.json();
    }

    async getRecentRuns(limit = 20, status = null) {
        const params = new URLSearchParams({ limit: limit.toString() });
        if (status) params.append('status', status);

        const response = await fetch(`${this.baseUrl}/dashboard/recent-runs?${params}`);
        return await response.json();
    }

    async getTestResults(runId, limit = null) {
        const params = new URLSearchParams();
        if (limit) params.append('limit', limit.toString());

        const response = await fetch(`${this.baseUrl}/dashboard/runs/${runId}/results?${params}`);
        return await response.json();
    }

    // WebSocket connection
    connectWebSocket() {
        const ws = new WebSocket('ws://localhost:8080/ws');

        ws.onopen = () => {
            console.log('Connected to dashboard');
            // Send heartbeat every 30 seconds
            setInterval(() => {
                ws.send(JSON.stringify({ type: 'ping' }));
            }, 30000);
        };

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleWebSocketMessage(data);
        };

        return ws;
    }

    handleWebSocketMessage(data) {
        switch (data.type) {
            case 'test_run_start':
                console.log(`Test run started: ${data.run_id}`);
                break;
            case 'test_end':
                console.log(`Test ${data.status}: ${data.test_name}`);
                break;
            case 'test_progress':
                console.log(`Progress: ${data.progress_percent}%`);
                break;
        }
    }
}

// Usage
const api = new DashboardAPI();
const summary = await api.getSummary();
console.log(`Success rate: ${summary.data.recent_24h.avg_success_rate}%`);

const ws = api.connectWebSocket();
```

### curl Examples

```bash
# Get dashboard summary
curl -X GET "http://localhost:8080/api/dashboard/summary" \
     -H "Accept: application/json"

# Get recent failed runs
curl -X GET "http://localhost:8080/api/dashboard/recent-runs?status=FAILED&limit=5" \
     -H "Accept: application/json"

# Get test results for a specific run
curl -X GET "http://localhost:8080/api/dashboard/runs/abc-123/results?limit=10" \
     -H "Accept: application/json"

# Health check
curl -X GET "http://localhost:8080/api/health"

# Simulate test event (development)
curl -X POST "http://localhost:8080/api/test/simulate-event" \
     -H "Content-Type: application/json" \
     -d '{
       "type": "test_run_start",
       "run_id": "test-123",
       "test_command": "pytest tests/",
       "total_tests": 10
     }'
```

---

This API reference provides comprehensive documentation for integrating with the Django-Ollama Test Dashboard. For additional examples and integration guides, see:

- [Integration Guide](INTEGRATION.md)
- [WebSocket Events](WEBSOCKET_EVENTS.md)
- [Client Libraries](CLIENT_LIBRARIES.md)