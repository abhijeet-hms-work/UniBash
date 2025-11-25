from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import subprocess
import os
import shlex

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*")

@app.route('/')
def index():
    return render_template('simple_index.html')

@socketio.on('connect')
def handle_connect():
    # Send initial prompt with current working directory
    cwd = os.getcwd()
    emit('initial_prompt', f'{cwd} $ ')

@socketio.on('command')
def handle_command(data):
    cmd = data.strip()
    
    if not cmd:
        # Empty command, just send new prompt
        cwd = os.getcwd()
        emit('response', f'\n{cwd} $ ')
        return
    
    if cmd.startswith('cd'):
        # Handle cd command
        parts = cmd.split(maxsplit=1)
        try:
            if len(parts) == 1:
                os.chdir(os.path.expanduser("~"))
            else:
                os.chdir(os.path.expanduser(parts[1]))
            cwd = os.getcwd()
            emit('response', f'\n{cwd} $ ')
        except Exception as e:
            cwd = os.getcwd()
            emit('response', f'cd: {e}\n{cwd} $ ')
        return
    
    elif cmd.strip() == 'clear':
        # Handle clear command
        cwd = os.getcwd()
        emit('clear_terminal', {'prompt': f'{cwd} $ '})
        return
    
    # Execute other commands
    try:
        # Use direct subprocess execution for better performance
        result = subprocess.run(
            shlex.split(cmd),
            capture_output=True,
            text=True,
            cwd=os.getcwd(),
            timeout=10  # 10 second timeout
        )
        
        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            output += result.stderr
        
        # Clean output and ensure proper line endings
        output = output.rstrip()
        cwd = os.getcwd()
        
        if output:
            emit('response', f'{output}\n{cwd} $ ')
        else:
            emit('response', f'{cwd} $ ')
            
    except subprocess.TimeoutExpired:
        cwd = os.getcwd()
        emit('response', f'Error: Command timed out\n{cwd} $ ')
    except FileNotFoundError:
        cwd = os.getcwd()
        emit('response', f'bash: {cmd.split()[0]}: command not found\n{cwd} $ ')
    except Exception as e:
        cwd = os.getcwd()
        emit('response', f'Error: {e}\n{cwd} $ ')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    print(f"🚀 Starting CBash Simple Server on port {port}")
    print(f"🖥️  Web terminal at: http://localhost:{port}/")
    socketio.run(app, host='0.0.0.0', port=port, debug=False)
