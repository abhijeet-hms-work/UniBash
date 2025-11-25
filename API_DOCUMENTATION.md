# CBash API Documentation

## Overview

CBash provides a comprehensive REST API and WebSocket interface for interacting with the web-based Unix terminal.

## Base URL

```
Production: https://cbash-app.herokuapp.com
Development: http://localhost:8000
```

## Authentication

CBash uses JWT tokens for session management. Tokens are automatically generated when connecting via WebSocket.

## REST API Endpoints

### Health Check

**GET** `/health`

Returns the current health status of the application.

#### Response

```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "active_sessions": 15,
  "uptime": 3600
}
```

### System Information

**GET** `/api/system-info`

Returns current system metrics.

#### Rate Limit
- 10 requests per minute per IP

#### Response

```json
{
  "cpu_percent": 25.5,
  "memory_percent": 45.2,
  "disk_percent": 60.8,
  "active_sessions": 15,
  "uptime": 3600
}
```

### Command History

**GET** `/api/command-history`

Returns recent command history.

#### Rate Limit
- 20 requests per minute per IP

#### Response

```json
[
  {
    "session_id": "abc123",
    "command": "ls -la",
    "timestamp": "2024-01-15T10:30:00Z",
    "client_ip": "192.168.1.100"
  }
]
```

### Metrics

**GET** `/metrics`

Returns Prometheus metrics for monitoring.

#### Response

```
# HELP cbash_commands_total Total commands executed
# TYPE cbash_commands_total counter
cbash_commands_total{command="ls",status="success"} 100
```

## WebSocket API

CBash uses Socket.IO for real-time communication.

### Connection

```javascript
const socket = io('http://localhost:8000');
```

### Events

#### Client → Server

##### command

Execute a command in the terminal.

```javascript
socket.emit('command', 'ls -la');
```

##### connect

Triggered when client connects to server.

#### Server → Client

##### initial_prompt

Sent when client first connects.

```javascript
socket.on('initial_prompt', (prompt) => {
  console.log('Prompt:', prompt);
});
```

##### response

Command execution result.

```javascript
socket.on('response', (data) => {
  if (typeof data === 'object') {
    console.log('Output:', data.output);
    console.log('Execution time:', data.execution_time);
  }
});
```

##### clear_terminal

Clear terminal command.

```javascript
socket.on('clear_terminal', (data) => {
  terminal.clear();
});
```

##### session_info

Session information.

```javascript
socket.on('session_info', (data) => {
  console.log('Session ID:', data.session_id);
});
```

## Custom CBash Commands

CBash provides custom commands prefixed with `cbash`:

### cbash status

Returns detailed system and session status.

```bash
cbash status
```

### cbash history [n]

Returns command history (default: 20 commands).

```bash
cbash history 50
```

### cbash sessions

Returns information about active sessions.

```bash
cbash sessions
```

## Error Handling

### HTTP Errors

| Status Code | Description |
|-------------|-------------|
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 429 | Too Many Requests |
| 500 | Internal Server Error |

### WebSocket Errors

Errors are returned as part of the response object:

```json
{
  "error": "Command timed out (30s limit)",
  "command": "sleep 60"
}
```

## Security Features

### Rate Limiting

- API endpoints: 10 requests/minute
- Command execution: 50 requests/minute
- Automatic IP-based throttling

### Command Filtering

Dangerous commands are automatically blocked:

- `rm -rf /`
- `mkfs`
- `dd if=`
- Fork bombs: `:(){:|:&};:`

### Input Sanitization

All user input is sanitized to prevent:
- Command injection
- Path traversal
- XSS attacks

## Performance Metrics

CBash collects the following metrics:

- **cbash_commands_total**: Total commands executed
- **cbash_command_duration_seconds**: Command execution time
- **cbash_active_sessions**: Number of active sessions
- **cbash_system_cpu_percent**: System CPU usage
- **cbash_system_memory_percent**: System memory usage

## WebSocket Connection Example

```javascript
const socket = io();

// Handle connection
socket.on('connect', () => {
  console.log('Connected to CBash');
});

// Handle disconnection
socket.on('disconnect', () => {
  console.log('Disconnected from CBash');
});

// Handle initial prompt
socket.on('initial_prompt', (prompt) => {
  terminal.write(prompt);
});

// Handle command response
socket.on('response', (data) => {
  if (typeof data === 'object') {
    terminal.write(data.output + '\r\n');
    terminal.write(data.prompt);
  } else {
    terminal.write(data);
  }
});

// Execute command
function executeCommand(command) {
  socket.emit('command', command);
}
```

## Deployment

### Docker

```bash
docker build -t cbash .
docker run -p 8000:8000 cbash
```

### Docker Compose

```bash
docker-compose up -d
```

### Heroku

```bash
heroku create cbash-app
git push heroku main
```

## Monitoring

CBash provides comprehensive monitoring through:

- **Prometheus**: Metrics collection
- **Grafana**: Visualization
- **Health checks**: Application status
- **Performance tracking**: Command execution metrics

## Support

For support and questions:

- **GitHub Issues**: [Report bugs and request features](https://github.com/SohaFarhana05/CBash/issues)
- **Documentation**: [Full documentation](https://github.com/SohaFarhana05/CBash/wiki)
- **Email**: sohafarhana@gmail.com
