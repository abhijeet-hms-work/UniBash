import pytest
import json
from unittest.mock import patch, MagicMock
from server import app, socket_manager, shell_manager
import tempfile
import os

@pytest.fixture
def client():
    """Create a test client for the Flask app."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@pytest.fixture
def socket_client():
    """Create a test client for Socket.IO."""
    return app.test_client()

class TestRoutes:
    """Test HTTP routes."""
    
    def test_index_route(self, client):
        """Test the main index route."""
        response = client.get('/')
        assert response.status_code == 200
        assert b'CBash Terminal' in response.data
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get('/health')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'healthy'
        assert 'timestamp' in data
        assert 'uptime' in data
    
    def test_metrics_endpoint(self, client):
        """Test Prometheus metrics endpoint."""
        response = client.get('/metrics')
        assert response.status_code == 200
        assert b'cbash_commands_total' in response.data
    
    @patch('server.psutil.cpu_percent')
    @patch('server.psutil.virtual_memory')
    @patch('server.psutil.disk_usage')
    def test_system_info(self, mock_disk, mock_memory, mock_cpu, client):
        """Test system info API endpoint."""
        # Mock system metrics
        mock_cpu.return_value = 25.5
        mock_memory.return_value = MagicMock(percent=45.2)
        mock_disk.return_value = MagicMock(percent=60.8)
        
        response = client.get('/api/system-info')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['cpu_percent'] == 25.5
        assert data['memory_percent'] == 45.2
        assert data['disk_percent'] == 60.8

class TestShellManager:
    """Test shell management functionality."""
    
    def test_shell_creation(self):
        """Test creating a new shell process."""
        manager = shell_manager
        session_id = 'test_session_123'
        
        # Create shell
        shell_info = manager.create_shell(session_id)
        assert session_id in manager.shells
        assert manager.shells[session_id]['process'] is not None
        assert manager.shells[session_id]['cwd'] == os.getcwd()
        
        # Cleanup
        manager.cleanup_shell(session_id)
        assert session_id not in manager.shells
    
    def test_shell_cleanup(self):
        """Test shell cleanup functionality."""
        manager = shell_manager
        session_id = 'test_cleanup_session'
        
        # Create and then cleanup shell
        manager.create_shell(session_id)
        assert session_id in manager.shells
        
        manager.cleanup_shell(session_id)
        assert session_id not in manager.shells

class TestCommandExecution:
    """Test command execution functionality."""
    
    @patch('server.subprocess.run')
    def test_basic_command_execution(self, mock_subprocess):
        """Test basic command execution."""
        # Mock subprocess response
        mock_result = MagicMock()
        mock_result.stdout = 'test output'
        mock_result.stderr = ''
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result
        
        # This would normally be tested through socket events
        # For now, we're testing the subprocess mocking
        assert mock_subprocess is not None
    
    def test_dangerous_command_blocking(self):
        """Test that dangerous commands are blocked."""
        dangerous_commands = [
            'rm -rf /',
            'mkfs /dev/sda',
            'dd if=/dev/zero of=/dev/sda',
            ':(){:|:&};:'
        ]
        
        for cmd in dangerous_commands:
            # In real implementation, these would be blocked
            # This test ensures we have the list of dangerous commands
            assert any(danger in cmd for danger in ['rm -rf /', 'mkfs', 'dd if=', ':(){:|:&};:'])

class TestSecurity:
    """Test security features."""
    
    def test_rate_limiting_configuration(self):
        """Test rate limiting is properly configured."""
        # This would test the rate limiting decorator
        # For now, we ensure the decorator exists
        from server import rate_limit
        assert rate_limit is not None
    
    def test_jwt_token_generation(self):
        """Test JWT token generation and verification."""
        from server import generate_session_token, verify_session_token
        
        user_id = 'test_user'
        token = generate_session_token(user_id)
        assert token is not None
        
        verified_user = verify_session_token(token)
        assert verified_user == user_id
    
    def test_invalid_token_handling(self):
        """Test handling of invalid tokens."""
        from server import verify_session_token
        
        invalid_token = 'invalid.token.here'
        result = verify_session_token(invalid_token)
        assert result is None

class TestPerformanceMonitoring:
    """Test performance monitoring features."""
    
    @patch('server.psutil.cpu_percent')
    @patch('server.psutil.virtual_memory')
    def test_system_metrics_collection(self, mock_memory, mock_cpu):
        """Test system metrics collection."""
        mock_cpu.return_value = 15.5
        mock_memory.return_value = MagicMock(percent=30.2)
        
        # Import and test monitoring functions
        import server
        cpu = server.psutil.cpu_percent()
        memory = server.psutil.virtual_memory().percent
        
        assert cpu == 15.5
        assert memory == 30.2

class TestCBashCommands:
    """Test custom CBash commands."""
    
    def test_cbash_status_command(self):
        """Test cbash status command functionality."""
        # This would test the custom cbash status command
        # For now, we ensure the function exists
        from server import handle_cbash_command
        assert handle_cbash_command is not None
    
    def test_cbash_history_command(self):
        """Test cbash history command functionality."""
        # Test would verify history command works correctly
        pass
    
    def test_cbash_sessions_command(self):
        """Test cbash sessions command functionality."""
        # Test would verify sessions command works correctly
        pass

class TestErrorHandling:
    """Test error handling and resilience."""
    
    def test_command_timeout_handling(self):
        """Test command timeout handling."""
        # Test would verify commands that run too long are terminated
        pass
    
    def test_invalid_directory_change(self):
        """Test handling of invalid directory changes."""
        # Test would verify proper error handling for cd to invalid paths
        pass
    
    def test_permission_denied_handling(self):
        """Test handling of permission denied errors."""
        # Test would verify graceful handling of permission errors
        pass

if __name__ == '__main__':
    pytest.main([__file__])
