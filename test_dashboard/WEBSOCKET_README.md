# WebSocket Real-Time Dashboard System

## Overview

The Django-Ollama Test Dashboard now features a robust WebSocket system that provides real-time updates during test execution. This system allows developers to monitor test progress live, see immediate results, and track coverage updates as tests run.

## Architecture

### Core Components

1. **FastAPI WebSocket Server** (`server.py`)
   - Integrated WebSocket endpoint at `/ws`
   - Connection management with auto-reconnection
   - Message broadcasting to multiple clients
   - Event-driven architecture

2. **WebSocket Client** (`static/js/websocket-dashboard.js`)
   - Modern ES6+ JavaScript client
   - Automatic reconnection with exponential backoff
   - Event-based message handling
   - Real-time UI updates

3. **Pytest Plugin Integration** (`plugins/pytest_dashboard.py`)
   - Seamless integration with pytest execution
   - Automatic event broadcasting during tests
   - Coverage data streaming

4. **Real-time Broadcaster** (`plugins/realtime.py`)
   - Flexible broadcasting system
   - Support for multiple connection types
   - Fallback mechanisms

## Features

### ✨ Real-Time Test Execution Monitoring

- **Live Test Progress**: See tests executing in real-time with progress bars
- **Individual Test Status**: Monitor each test as it starts, runs, and completes
- **Error Notifications**: Immediate alerts when tests fail with error details
- **Coverage Updates**: Real-time coverage percentage updates per file

### 🔄 Robust Connection Management

- **Auto-Reconnection**: Automatic reconnection with exponential backoff
- **Connection Health**: Heartbeat mechanism to ensure connection stability
- **Multiple Clients**: Support for multiple dashboard viewers simultaneously
- **Graceful Degradation**: Falls back to polling if WebSocket unavailable

### 📊 Enhanced User Experience

- **Live Execution Panel**: Appears automatically when tests start running
- **Toast Notifications**: Non-intrusive notifications for important events
- **Connection Status**: Clear indication of connection state in status bar
- **Theme Support**: Real-time updates work with both light and dark themes

## Message Types

### Client → Server Messages

```json
{
  "type": "ping",
  "timestamp": "2024-01-20T10:30:00Z"
}

{
  "type": "request_status"
}

{
  "type": "subscribe_run",
  "run_id": "test-run-123"
}
```

### Server → Client Messages

#### Test Execution Events

```json
{
  "type": "test_run_start",
  "run_id": "test-run-123",
  "test_command": "pytest tests/",
  "total_tests": 25,
  "timestamp": "2024-01-20T10:30:00Z"
}

{
  "type": "test_start",
  "run_id": "test-run-123",
  "test_name": "test_user_authentication",
  "test_file": "tests/test_auth.py",
  "timestamp": "2024-01-20T10:30:01Z"
}

{
  "type": "test_end",
  "run_id": "test-run-123",
  "test_name": "test_user_authentication",
  "status": "PASSED",
  "duration": 1.245,
  "error_message": null,
  "timestamp": "2024-01-20T10:30:02Z"
}

{
  "type": "test_progress",
  "run_id": "test-run-123",
  "completed": 15,
  "total": 25,
  "progress_percent": 60.0,
  "current_test": "test_data_validation",
  "timestamp": "2024-01-20T10:30:15Z"
}

{
  "type": "test_run_end",
  "run_id": "test-run-123",
  "duration": 45.2,
  "stats": {
    "total": 25,
    "passed": 22,
    "failed": 2,
    "skipped": 1
  },
  "timestamp": "2024-01-20T10:30:45Z"
}
```

#### System Events

```json
{
  "type": "connection_established",
  "connection_id": "client-1",
  "message": "Connected to Django-Ollama Test Dashboard",
  "timestamp": "2024-01-20T10:30:00Z"
}

{
  "type": "server_status",
  "status": "healthy",
  "summary": { /* dashboard summary data */ },
  "recent_runs": [ /* recent test runs */ ],
  "active_connections": 3,
  "timestamp": "2024-01-20T10:30:00Z"
}

{
  "type": "heartbeat",
  "connections": 3,
  "timestamp": "2024-01-20T10:30:30Z"
}
```

## Usage

### Running Tests with Real-Time Updates

1. **Start the Dashboard Server**
   ```bash
   cd test_dashboard
   python server.py --port 8080
   ```

2. **Open Dashboard in Browser**
   ```
   http://localhost:8080
   ```

3. **Run Tests with WebSocket Broadcasting**
   ```bash
   pytest --dashboard --dashboard-websocket tests/
   ```

4. **Watch Live Updates**
   - The dashboard will automatically show the live execution panel
   - Progress bars update in real-time
   - Individual test results appear immediately
   - Notifications show important events

### Testing WebSocket Functionality

Run the comprehensive WebSocket test suite:

```bash
cd test_dashboard
python websocket_test.py
```

This will test:
- Server availability
- WebSocket connection establishment
- Event broadcasting
- Message handling
- Connection recovery

## API Endpoints

### WebSocket Endpoint
- **URL**: `/ws`
- **Protocol**: WebSocket
- **Purpose**: Real-time bidirectional communication

### REST Endpoints
- **GET** `/api/websocket/status` - Get WebSocket connection status
- **POST** `/api/test/simulate-event` - Trigger test events (for testing)

## Configuration

### Environment Variables

```bash
# Server configuration
DASHBOARD_HOST=0.0.0.0
DASHBOARD_PORT=8080

# WebSocket configuration
WEBSOCKET_PING_INTERVAL=25
WEBSOCKET_PING_TIMEOUT=10
WEBSOCKET_CLOSE_TIMEOUT=10
```

### Pytest Configuration

Add to `pytest.ini`:

```ini
[tool:pytest]
addopts = --dashboard --dashboard-websocket
markers =
    dashboard_track: Mark test for dashboard tracking
    dashboard_ignore: Mark test to ignore in dashboard
```

## Client-Side Integration

### Basic Usage

```javascript
// Initialize WebSocket client
const wsClient = new WebSocketDashboardClient();

// Add custom event handlers
wsClient.addEventListener('test_start', (message) => {
    console.log(`Test started: ${message.test_name}`);
});

wsClient.addEventListener('test_end', (message) => {
    console.log(`Test ${message.status}: ${message.test_name} (${message.duration}s)`);
});

// Get connection info
const info = wsClient.getConnectionInfo();
console.log('Connected:', info.isConnected);
```

### Custom Event Handling

```javascript
// Listen for specific test runs
wsClient.send({
    type: 'subscribe_run',
    run_id: 'my-test-run-123'
});

// Handle coverage updates
wsClient.addEventListener('coverage_update', (message) => {
    updateCoverageDisplay(message.file_path, message.coverage_percent);
});
```

## Security Considerations

- **CORS**: Properly configured for cross-origin requests
- **Input Validation**: All WebSocket messages are validated
- **Rate Limiting**: Connection limits prevent abuse
- **Authentication**: Can be extended to require authentication

## Performance

### Optimizations

- **Message Batching**: Multiple events batched when possible
- **Connection Pooling**: Efficient connection management
- **Memory Management**: Automatic cleanup of disconnected clients
- **Compression**: WebSocket compression enabled
- **Throttling**: Event throttling prevents spam

### Monitoring

- Active connection count tracking
- Message throughput monitoring
- Error rate tracking
- Reconnection attempt logging

## Browser Compatibility

- **Modern Browsers**: Full support for Chrome 70+, Firefox 65+, Safari 12+
- **WebSocket Support**: Required (available in all modern browsers)
- **Fallback**: Graceful degradation to polling if WebSocket unavailable

## Troubleshooting

### Common Issues

1. **Connection Failed**
   - Check server is running on correct port
   - Verify firewall settings
   - Check browser console for errors

2. **No Real-Time Updates**
   - Ensure WebSocket is enabled: `--dashboard-websocket`
   - Check WebSocket endpoint: `/api/websocket/status`
   - Verify test markers are configured

3. **Slow Updates**
   - Check network connectivity
   - Monitor server resources
   - Consider reducing message frequency

### Debug Mode

Enable debug logging:

```javascript
// Enable debug mode
document.body.classList.add('debug');

// Check WebSocket client status
console.log(window.webSocketClient.getConnectionInfo());
```

### Logs

Server logs show WebSocket activity:
```
INFO - WebSocket client connected: client-1 (total: 1)
INFO - Broadcasting test_run_start to 1 clients
INFO - WebSocket client disconnected (remaining: 0)
```

## Development

### Adding New Event Types

1. **Define Event Type** (server.py)
   ```python
   async def broadcast_custom_event(self, data):
       message = {
           "type": "custom_event",
           "data": data
       }
       await self.broadcast(message)
   ```

2. **Handle in Client** (websocket-dashboard.js)
   ```javascript
   case 'custom_event':
       this.handleCustomEvent(message);
       break;
   ```

3. **Update Documentation**
   - Add to message types
   - Update API documentation

### Testing New Features

1. **Unit Tests**: Add WebSocket-specific tests
2. **Integration Tests**: Test with actual pytest runs
3. **Load Testing**: Test with multiple connections
4. **Browser Testing**: Verify cross-browser compatibility

## Future Enhancements

- **Authentication**: User-based connection management
- **Room System**: Separate channels for different projects
- **Persistence**: Store and replay test sessions
- **Metrics**: Advanced performance monitoring
- **Mobile**: Mobile-optimized dashboard interface

## Contributing

When contributing to the WebSocket system:

1. **Follow Patterns**: Use existing event patterns
2. **Add Tests**: Include WebSocket tests for new features
3. **Documentation**: Update this README for changes
4. **Backwards Compatibility**: Maintain API compatibility
5. **Performance**: Consider performance impact

## Support

For issues related to the WebSocket system:

1. **Check Logs**: Server and browser console logs
2. **Test Script**: Run `websocket_test.py` for diagnostics
3. **Status Endpoint**: Check `/api/websocket/status`
4. **GitHub Issues**: Report bugs with full details

---

**Made with ❤️ for the Django-Ollama community**

*Real-time test monitoring that makes watching tests as exciting as watching live sports!*