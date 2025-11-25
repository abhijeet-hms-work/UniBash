from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit, join_room, leave_room
import subprocess
import os
import re
import shlex
import json
import time
import psutil
import threading
import hashlib
import jwt
from datetime import datetime, timedelta
from functools import wraps
import redis
from prometheus_client import Counter, Histogram, Gauge, generate_latest
import logging
from logging.handlers import RotatingFileHandler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-change-this')
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Redis connection for session management and caching
try:
    redis_client = redis.Redis.from_url(os.environ.get('REDIS_URL', 'redis://localhost:6379'), decode_responses=True)
    redis_client.ping()
    logger.info("Connected to Redis")
except Exception as e:
    logger.warning(f"Redis connection failed: {e}. Using in-memory storage.")
    redis_client = None

# Prometheus metrics
command_counter = Counter('cbash_commands_total', 'Total commands executed', ['command', 'status'])
command_duration = Histogram('cbash_command_duration_seconds', 'Command execution time')
active_sessions = Gauge('cbash_active_sessions', 'Number of active sessions')
system_cpu = Gauge('cbash_system_cpu_percent', 'System CPU usage')
system_memory = Gauge('cbash_system_memory_percent', 'System memory usage')

# Global state
active_sessions_count = 0
user_sessions = {}
command_history = []

# Note: Shell processes are now managed by ShellManager class
# shell_process = subprocess.Popen(['./mysh'],
#                                  stdin=subprocess.PIPE,
#                                  stdout=subprocess.PIPE,
#                                  stderr=subprocess.STDOUT,
#                                  text=True,
#                                  bufsize=1,
#                                  cwd=os.getcwd())

# Security functions
def generate_session_token(user_id):
    """Generate a JWT token for session management"""
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(hours=24),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')

def verify_session_token(token):
    """Verify JWT token"""
    try:
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        return payload['user_id']
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def rate_limit(max_requests=100, window=60):
    """Rate limiting decorator"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
            key = f"rate_limit:{client_ip}"
            
            if redis_client:
                current = redis_client.get(key)
                if current is None:
                    redis_client.setex(key, window, 1)
                elif int(current) >= max_requests:
                    return jsonify({'error': 'Rate limit exceeded'}), 429
                else:
                    redis_client.incr(key)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# System monitoring
def monitor_system():
    """Background thread to monitor system metrics"""
    while True:
        try:
            cpu_percent = psutil.cpu_percent()
            memory_percent = psutil.virtual_memory().percent
            
            system_cpu.set(cpu_percent)
            system_memory.set(memory_percent)
            
            # Store metrics in Redis for historical data
            if redis_client:
                timestamp = int(time.time())
                redis_client.zadd('metrics:cpu', {timestamp: cpu_percent})
                redis_client.zadd('metrics:memory', {timestamp: memory_percent})
                
                # Keep only last 1000 data points
                redis_client.zremrangebyrank('metrics:cpu', 0, -1001)
                redis_client.zremrangebyrank('metrics:memory', 0, -1001)
                
        except Exception as e:
            logger.error(f"System monitoring error: {e}")
        
        time.sleep(10)

# Start monitoring thread
monitoring_thread = threading.Thread(target=monitor_system, daemon=True)
monitoring_thread.start()

# Enhanced shell process management
class ShellManager:
    def __init__(self):
        self.shells = {}
    
    def create_shell(self, session_id):
        """Create a new shell process for a session"""
        try:
            shell_process = subprocess.Popen(
                ['./mysh'],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                cwd=os.getcwd(),
                preexec_fn=os.setsid  # Create new process group
            )
            self.shells[session_id] = {
                'process': shell_process,
                'cwd': os.getcwd(),
                'env': dict(os.environ),
                'history': [],
                'created_at': datetime.utcnow()
            }
            return shell_process
        except Exception as e:
            logger.error(f"Failed to create shell for session {session_id}: {e}")
            return None
    
    def get_shell(self, session_id):
        """Get shell for session, create if doesn't exist"""
        if session_id not in self.shells:
            self.create_shell(session_id)
        return self.shells.get(session_id)
    
    def cleanup_shell(self, session_id):
        """Clean up shell process"""
        if session_id in self.shells:
            try:
                shell_info = self.shells[session_id]
                shell_info['process'].terminate()
                shell_info['process'].wait(timeout=5)
            except Exception as e:
                logger.error(f"Error cleaning up shell {session_id}: {e}")
            finally:
                del self.shells[session_id]

shell_manager = ShellManager()

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/health')
def health_check():
    """Health check endpoint for load balancers"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'active_sessions': active_sessions_count,
        'uptime': time.time() - start_time
    })

@app.route('/metrics')
def metrics():
    """Prometheus metrics endpoint"""
    return generate_latest()

@app.route('/api/system-info')
@rate_limit(max_requests=10, window=60)
def system_info():
    """Get system information"""
    return jsonify({
        'cpu_percent': psutil.cpu_percent(),
        'memory_percent': psutil.virtual_memory().percent,
        'disk_percent': psutil.disk_usage('/').percent,
        'active_sessions': active_sessions_count,
        'uptime': time.time() - start_time
    })

@app.route('/api/command-history')
@rate_limit(max_requests=20, window=60)
def get_command_history():
    """Get command history"""
    if redis_client:
        history = redis_client.lrange('command_history', 0, 99)
        return jsonify([json.loads(cmd) for cmd in history])
    return jsonify(command_history[-100:])

# Socket events
@socketio.on('connect')
def handle_connect():
    global active_sessions_count
    active_sessions_count += 1
    active_sessions.set(active_sessions_count)
    
    session_id = request.sid
    user_sessions[session_id] = {
        'connected_at': datetime.utcnow(),
        'command_count': 0,
        'last_activity': datetime.utcnow()
    }
    
    join_room(session_id)
    
    # Create shell for this session
    shell_manager.create_shell(session_id)
    
    # Send initial prompt with current working directory
    cwd = os.getcwd()
    initial_prompt = f'{cwd} $ '
    logger.info(f"Sending initial prompt to {session_id}: {initial_prompt}")
    emit('initial_prompt', initial_prompt)
    emit('session_info', {
        'session_id': session_id,
        'connected_at': user_sessions[session_id]['connected_at'].isoformat()
    })
    
    logger.info(f"Client connected: {session_id}")

@socketio.on('disconnect')
def handle_disconnect():
    global active_sessions_count
    active_sessions_count = max(0, active_sessions_count - 1)
    active_sessions.set(active_sessions_count)
    
    session_id = request.sid
    
    # Clean up shell process
    shell_manager.cleanup_shell(session_id)
    
    if session_id in user_sessions:
        session_duration = (datetime.utcnow() - user_sessions[session_id]['connected_at']).total_seconds()
        logger.info(f"Client disconnected: {session_id}, duration: {session_duration}s")
        del user_sessions[session_id]
    
    leave_room(session_id)

start_time = time.time()

@socketio.on('command')
def handle_command(data):
    start_time_cmd = time.time()
    session_id = request.sid
    cmd = data.strip()
    
    # Update session activity
    if session_id in user_sessions:
        user_sessions[session_id]['last_activity'] = datetime.utcnow()
        user_sessions[session_id]['command_count'] += 1
    
    # Log command for security audit
    command_log = {
        'session_id': session_id,
        'command': cmd,
        'timestamp': datetime.utcnow().isoformat(),
        'client_ip': request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
    }
    
    # Store in Redis for persistence
    if redis_client:
        redis_client.lpush('command_history', json.dumps(command_log))
        redis_client.ltrim('command_history', 0, 999)  # Keep last 1000 commands
    else:
        command_history.append(command_log)
        if len(command_history) > 1000:
            command_history.pop(0)
    
    output_lines = []
    
    try:
        # Enhanced command processing
        if cmd.startswith('cd'):
            parts = cmd.split(maxsplit=1)
            try:
                if len(parts) == 1:
                    os.chdir(os.path.expanduser("~"))
                else:
                    os.chdir(os.path.expanduser(parts[1]))
                output_lines.append('')
                command_counter.labels(command='cd', status='success').inc()
            except Exception as e:
                output_lines.append(f"cd: {e}")
                command_counter.labels(command='cd', status='error').inc()
                
        elif cmd.strip() == 'clear':
            cwd = os.getcwd()
            emit('clear_terminal', {'cwd': cwd})
            command_counter.labels(command='clear', status='success').inc()
            return
            
        elif cmd.startswith('cbash '):
            # Custom CBash commands
            handle_cbash_command(cmd[6:], session_id)
            return
            
        else:
            # Execute command with enhanced error handling
            cmd_name = cmd.strip().split()[0] if cmd.strip() else ''
            
            try:
                # Security: Prevent dangerous commands
                dangerous_commands = ['rm -rf /', 'mkfs', 'dd if=', 'format', ':(){:|:&};:']
                if any(danger in cmd for danger in dangerous_commands):
                    output_lines.append("Error: Dangerous command blocked for security")
                    command_counter.labels(command=cmd_name, status='blocked').inc()
                else:
                    # Enhanced command execution with timeout
                    result = subprocess.run(
                        shlex.split(cmd) if not any(char in cmd for char in ['|', '>', '<', '&']) else cmd,
                        shell=any(char in cmd for char in ['|', '>', '<', '&']),
                        capture_output=True,
                        text=True,
                        cwd=os.getcwd(),
                        timeout=30,  # 30 second timeout
                        env=dict(os.environ, COLUMNS='120', LINES='30')  # Set terminal size
                    )
                    
                    if result.stdout:
                        clean_output = result.stdout
                        # Keep proper line breaks and formatting
                        clean_output = clean_output.replace('\r\n', '\n').replace('\r', '\n')
                        # Don't remove control characters that are needed for formatting
                        output_lines.append(clean_output)
                    
                    if result.stderr:
                        error_msg = result.stderr.strip()
                        output_lines.append(error_msg)
                    
                    status = 'success' if result.returncode == 0 else 'error'
                    command_counter.labels(command=cmd_name, status=status).inc()
                    
            except subprocess.TimeoutExpired:
                output_lines.append("Error: Command timed out (30s limit)")
                command_counter.labels(command=cmd_name, status='timeout').inc()
            except Exception as e:
                output_lines.append(f"Error: {e}")
                command_counter.labels(command=cmd_name, status='error').inc()
    
    except Exception as e:
        output_lines.append(f"System error: {e}")
        logger.error(f"Command handling error: {e}")
    
    # Record command execution time
    execution_time = time.time() - start_time_cmd
    command_duration.observe(execution_time)
    
    output = '\n'.join(output_lines)
    cwd = os.getcwd()
    
    # Clean output but preserve formatting
    if output:
        # Only normalize line endings, don't remove other characters
        output = output.replace('\r\n', '\n').replace('\r', '\n')
        # Remove excessive empty lines only
        while '\n\n\n\n' in output:
            output = output.replace('\n\n\n\n', '\n\n\n')
    
    emit('response', {
        'output': output,
        'prompt': f'{cwd} $ ',
        'execution_time': round(execution_time, 3),
        'command': cmd
    })

def handle_cbash_command(cmd, session_id):
    """Handle custom CBash commands"""
    parts = cmd.split()
    command = parts[0] if parts else ''
    
    if command == 'status':
        emit('response', {
            'output': json.dumps({
                'session_id': session_id,
                'uptime': time.time() - start_time,
                'commands_executed': user_sessions.get(session_id, {}).get('command_count', 0),
                'cpu_usage': psutil.cpu_percent(),
                'memory_usage': psutil.virtual_memory().percent
            }, indent=2),
            'prompt': f'{os.getcwd()} $ '
        })
    elif command == 'history':
        limit = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 20
        if redis_client:
            history = redis_client.lrange('command_history', 0, limit-1)
            history_data = [json.loads(cmd) for cmd in history]
        else:
            history_data = command_history[-limit:]
        
        output = '\n'.join([f"{i+1}: {cmd['command']}" for i, cmd in enumerate(history_data)])
        emit('response', {
            'output': output,
            'prompt': f'{os.getcwd()} $ '
        })
    elif command == 'sessions':
        sessions_info = []
        for sid, info in user_sessions.items():
            sessions_info.append({
                'session_id': sid[:8] + '...',
                'connected_at': info['connected_at'].isoformat(),
                'command_count': info['command_count']
            })
        emit('response', {
            'output': json.dumps(sessions_info, indent=2),
            'prompt': f'{os.getcwd()} $ '
        })
    else:
        emit('response', {
            'output': 'Available CBash commands: status, history [n], sessions',
            'prompt': f'{os.getcwd()} $ '
        })

if __name__ == '__main__':
    # Get port from environment variable (for deployment platforms)
    port = int(os.environ.get('PORT', 8000))
    
    print(f"🚀 Starting CBash server on port {port}")
    print(f"📊 Metrics available at: http://localhost:{port}/metrics")
    print(f"🏥 Health check at: http://localhost:{port}/health")
    print(f"🖥️  Web terminal at: http://localhost:{port}/")
    
    # Listen on all IP addresses (0.0.0.0) so others can connect
    socketio.run(app, host='0.0.0.0', port=port, debug=False, allow_unsafe_werkzeug=True)


