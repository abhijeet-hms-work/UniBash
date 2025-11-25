from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import subprocess
import os
import shlex
import time
import json
from datetime import datetime

# Simple, fast Flask app configuration
app = Flask(__name__)
app.config['SECRET_KEY'] = 'cbash-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Global state - simplified for performance
active_sessions = {}
command_history = []
start_time = time.time()

@app.route('/')
def index():
    return render_template('simple_index.html')

@app.route('/health')
def health_check():
    """Simple health check"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'active_sessions': len(active_sessions),
        'uptime': time.time() - start_time
    })

@app.route('/api/stats')
def get_stats():
    """Get basic stats"""
    return jsonify({
        'active_sessions': len(active_sessions),
        'total_commands': len(command_history),
        'uptime': time.time() - start_time
    })

@socketio.on('connect')
def handle_connect():
    session_id = request.sid
    active_sessions[session_id] = {
        'connected_at': datetime.utcnow(),
        'command_count': 0
    }
    
    # Send initial prompt
    cwd = os.getcwd()
    emit('initial_prompt', f'{cwd} $ ')
    print(f"Client connected: {session_id}")

@socketio.on('disconnect')
def handle_disconnect():
    session_id = request.sid
    if session_id in active_sessions:
        del active_sessions[session_id]
    print(f"Client disconnected: {session_id}")

@socketio.on('command')
def handle_command(data):
    session_id = request.sid
    cmd = data.strip()
    
    # Update session stats
    if session_id in active_sessions:
        active_sessions[session_id]['command_count'] += 1
    
    # Log command
    command_history.append({
        'session_id': session_id,
        'command': cmd,
        'timestamp': datetime.utcnow().isoformat()
    })
    
    # Keep only last 100 commands
    if len(command_history) > 100:
        command_history.pop(0)
    
    output_lines = []
    
    try:
        # Handle built-in commands
        if cmd.startswith('cd'):
            parts = cmd.split(maxsplit=1)
            try:
                if len(parts) == 1:
                    os.chdir(os.path.expanduser("~"))
                else:
                    os.chdir(os.path.expanduser(parts[1]))
                output_lines.append('')
            except Exception as e:
                output_lines.append(f"cd: {e}")
                
        elif cmd.strip() == 'clear':
            cwd = os.getcwd()
            emit('clear_terminal', {'cwd': cwd})
            return
            
        elif cmd.startswith('cbash '):
            # Custom CBash commands
            handle_cbash_command(cmd[6:], session_id)
            return
            
        else:
            # Execute command
            if cmd.strip():
                try:
                    # Use shell=True for pipes and redirects, otherwise use shlex
                    if any(char in cmd for char in ['|', '>', '<', '&', ';']):
                        result = subprocess.run(
                            cmd,
                            shell=True,
                            capture_output=True,
                            text=True,
                            cwd=os.getcwd(),
                            timeout=15
                        )
                    else:
                        result = subprocess.run(
                            shlex.split(cmd),
                            capture_output=True,
                            text=True,
                            cwd=os.getcwd(),
                            timeout=15
                        )
                    
                    if result.stdout:
                        output_lines.append(result.stdout.rstrip())
                    if result.stderr:
                        output_lines.append(result.stderr.rstrip())
                        
                except subprocess.TimeoutExpired:
                    output_lines.append("Error: Command timed out (15s limit)")
                except FileNotFoundError:
                    output_lines.append(f"Command not found: {cmd.split()[0]}")
                except Exception as e:
                    output_lines.append(f"Error: {e}")
    
    except Exception as e:
        output_lines.append(f"System error: {e}")
    
    # Send response
    output = '\n'.join(output_lines) if output_lines else ''
    cwd = os.getcwd()
    
    # Send clean response
    if output:
        emit('response', output + f'\n{cwd} $ ')
    else:
        emit('response', f'{cwd} $ ')

def handle_cbash_command(cmd, session_id):
    """Handle custom CBash commands"""
    parts = cmd.split()
    command = parts[0] if parts else ''
    
    if command == 'status':
        session_info = active_sessions.get(session_id, {})
        status = {
            'session_id': session_id[:8] + '...',
            'uptime': time.time() - start_time,
            'commands_executed': session_info.get('command_count', 0),
            'total_sessions': len(active_sessions)
        }
        emit('response', json.dumps(status, indent=2) + f'\n{os.getcwd()} $ ')
        
    elif command == 'history':
        limit = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 10
        recent_commands = command_history[-limit:]
        output = '\n'.join([f"{i+1}: {cmd['command']}" for i, cmd in enumerate(recent_commands)])
        emit('response', output + f'\n{os.getcwd()} $ ')
        
    elif command == 'help':
        help_text = """CBash Commands:
  cbash status    - Show session status
  cbash history [n] - Show command history (default: 10)
  cbash help      - Show this help
  clear          - Clear terminal
  cd <dir>       - Change directory"""
        emit('response', help_text + f'\n{os.getcwd()} $ ')
        
    else:
        emit('response', 'Available CBash commands: status, history [n], help\n' + f'{os.getcwd()} $ ')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    
    print("=" * 50)
    print("🚀 CBash - Fast Web Terminal")
    print("=" * 50)
    print(f"🌐 Server: http://localhost:{port}")
    print(f"🏥 Health: http://localhost:{port}/health")
    print(f"📊 Stats:  http://localhost:{port}/api/stats")
    print("=" * 50)
    
    socketio.run(app, host='0.0.0.0', port=port, debug=False, allow_unsafe_werkzeug=True)
