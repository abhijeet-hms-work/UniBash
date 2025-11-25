// CBash Advanced Terminal - Main Application JavaScript

// Global variables
let socket;
let terminal;
let currentTheme = 'dark';
let commandHistory = [];
let historyIndex = -1;
let sessionStats = {
  commandCount: 0,
  startTime: Date.now(),
  sessionId: null
};

// Terminal themes
const themes = {
  dark: {
    background: '#0d1117',
    foreground: '#f0f6fc',
    cursor: '#58a6ff',
    selection: '#3d444d',
    black: '#484f58',
    red: '#ff7b72',
    green: '#39d353',
    yellow: '#ffdf5d',
    blue: '#58a6ff',
    magenta: '#bc8cff',
    cyan: '#39c5cf',
    white: '#b1bac4'
  },
  light: {
    background: '#ffffff',
    foreground: '#24292f',
    cursor: '#0969da',
    selection: '#b6d7ff',
    black: '#24292f',
    red: '#cf222e',
    green: '#116329',
    yellow: '#4d2d00',
    blue: '#0969da',
    magenta: '#8250df',
    cyan: '#1b7c83',
    white: '#6e7781'
  },
  hacker: {
    background: '#000000',
    foreground: '#00ff00',
    cursor: '#00ff00',
    selection: '#003300',
    black: '#000000',
    red: '#ff0000',
    green: '#00ff00',
    yellow: '#ffff00',
    blue: '#0000ff',
    magenta: '#ff00ff',
    cyan: '#00ffff',
    white: '#ffffff'
  }
};

// Initialize application
function initializeApp() {
  initializeSocket();
  initializeTerminal();
  initializeUI();
  initializePerformanceMonitoring();
  setupKeyboardShortcuts();
  startStatsUpdater();
  loadSavedSettings();
}

// Socket.IO initialization
function initializeSocket() {
  socket = io();
  
  socket.on('connect', function() {
    updateConnectionStatus('connected');
    showNotification('🟢 Connected to CBash server', 'success');
  });
  
  socket.on('disconnect', function() {
    updateConnectionStatus('disconnected');
    showNotification('🔴 Disconnected from server', 'error');
  });
  
  socket.on('initial_prompt', function(prompt) {
    terminal.write(prompt);
  });
  
  socket.on('response', function(data) {
    if (typeof data === 'object') {
      if (data.output) {
        // Write output with proper formatting
        terminal.write(data.output);
        if (!data.output.endsWith('\n')) {
          terminal.write('\r\n');
        }
      }
      if (data.prompt) {
        terminal.write(data.prompt);
      }
      if (data.execution_time) {
        updateExecutionStats(data.execution_time, data.command);
      }
    } else {
      terminal.write(data);
    }
    sessionStats.commandCount++;
    updateSessionStats();
  });
  
  socket.on('clear_terminal', function(data) {
    terminal.clear();
    if (data.cwd) {
      terminal.write(data.cwd + ' $ ');
    }
  });
  
  socket.on('session_info', function(data) {
    sessionStats.sessionId = data.session_id;
    sessionStats.startTime = new Date(data.connected_at).getTime();
  });
}

// Terminal initialization
function initializeTerminal() {
  terminal = new Terminal({
    cursorBlink: true,
    fontSize: 14,
    fontFamily: 'SF Mono, Monaco, Inconsolata, Roboto Mono, monospace',
    theme: themes[currentTheme],
    scrollback: 1000,
    allowTransparency: true,
    rightClickSelectsWord: true,
    wordSeparator: ' ()[]{}\'",;'
  });
  
  // Add-ons (if available)
  if (typeof FitAddon !== 'undefined') {
    const fitAddon = new FitAddon.FitAddon();
    terminal.loadAddon(fitAddon);
    
    // Fit terminal to container
    setTimeout(() => {
      fitAddon.fit();
    }, 100);
    
    // Resize handler
    window.addEventListener('resize', () => {
      setTimeout(() => fitAddon.fit(), 100);
    });
  }
  
  if (typeof WebLinksAddon !== 'undefined') {
    const webLinksAddon = new WebLinksAddon.WebLinksAddon();
    terminal.loadAddon(webLinksAddon);
  }
  
  terminal.open(document.getElementById('terminal'));
  
  // Handle terminal input
  let currentLine = '';
  terminal.onData(data => {
    if (data === '\r') { // Enter key
      if (currentLine.trim()) {
        commandHistory.push(currentLine);
        historyIndex = commandHistory.length;
        socket.emit('command', currentLine);
        
        // Save command history to localStorage
        saveCommandHistory();
      }
      currentLine = '';
    } else if (data === '\u007F') { // Backspace
      if (currentLine.length > 0) {
        currentLine = currentLine.slice(0, -1);
        terminal.write('\b \b');
      }
    } else if (data === '\u001b[A') { // Up arrow
      if (historyIndex > 0) {
        // Clear current line
        for (let i = 0; i < currentLine.length; i++) {
          terminal.write('\b \b');
        }
        historyIndex--;
        currentLine = commandHistory[historyIndex];
        terminal.write(currentLine);
      }
    } else if (data === '\u001b[B') { // Down arrow
      if (historyIndex < commandHistory.length - 1) {
        // Clear current line
        for (let i = 0; i < currentLine.length; i++) {
          terminal.write('\b \b');
        }
        historyIndex++;
        currentLine = commandHistory[historyIndex];
        terminal.write(currentLine);
      } else if (historyIndex === commandHistory.length - 1) {
        // Clear current line
        for (let i = 0; i < currentLine.length; i++) {
          terminal.write('\b \b');
        }
        historyIndex++;
        currentLine = '';
      }
    } else if (data === '\u0003') { // Ctrl+C
      terminal.write('^C\r\n');
      currentLine = '';
      socket.emit('command', ''); // Send empty command to get new prompt
    } else if (data === '\u0004') { // Ctrl+D
      socket.emit('command', 'exit');
    } else if (data.length === 1 && data.charCodeAt(0) >= 32) { // Printable characters
      currentLine += data;
      terminal.write(data);
    }
  });
  
  // Focus terminal by default
  terminal.focus();
}

// UI initialization
function initializeUI() {
  // Sidebar toggle
  const sidebarToggle = document.getElementById('sidebarToggle');
  const closeSidebar = document.getElementById('closeSidebar');
  
  if (sidebarToggle) {
    sidebarToggle.addEventListener('click', toggleSidebar);
  }
  if (closeSidebar) {
    closeSidebar.addEventListener('click', toggleSidebar);
  }
  
  // Command palette
  const commandPaletteBtn = document.getElementById('commandPaletteBtn');
  if (commandPaletteBtn) {
    commandPaletteBtn.addEventListener('click', toggleCommandPalette);
  }
  
  // Theme toggle
  const themeToggle = document.getElementById('themeToggle');
  if (themeToggle) {
    themeToggle.addEventListener('click', cycleTheme);
  }
  
  // Quick commands
  document.querySelectorAll('.quick-cmd-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const cmd = btn.getAttribute('data-cmd');
      if (cmd && socket) {
        socket.emit('command', cmd);
        commandHistory.push(cmd);
        historyIndex = commandHistory.length;
        saveCommandHistory();
      }
    });
  });
  
  // Theme selection
  document.querySelectorAll('.theme-option').forEach(option => {
    option.addEventListener('click', () => {
      const theme = option.getAttribute('data-theme');
      setTheme(theme);
    });
  });
  
  // Command palette functionality
  const commandInput = document.getElementById('commandInput');
  if (commandInput) {
    commandInput.addEventListener('input', handleCommandPaletteInput);
    commandInput.addEventListener('keydown', handleCommandPaletteKeydown);
  }
  
  // Click outside to close command palette
  document.addEventListener('click', (e) => {
    const commandPalette = document.getElementById('commandPalette');
    if (commandPalette && !commandPalette.contains(e.target) && 
        !document.getElementById('commandPaletteBtn').contains(e.target)) {
      commandPalette.classList.remove('show');
    }
  });
}

// Performance monitoring
function initializePerformanceMonitoring() {
  const canvas = document.getElementById('performanceChart');
  if (!canvas || typeof Chart === 'undefined') {
    console.warn('Chart.js not available or canvas element not found');
    return;
  }
  
  const ctx = canvas.getContext('2d');
  
  window.performanceChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: [],
      datasets: [
        {
          label: 'CPU %',
          data: [],
          borderColor: '#58a6ff',
          backgroundColor: 'rgba(88, 166, 255, 0.1)',
          tension: 0.4,
          pointRadius: 2
        },
        {
          label: 'Memory %',
          data: [],
          borderColor: '#39d353',
          backgroundColor: 'rgba(57, 211, 83, 0.1)',
          tension: 0.4,
          pointRadius: 2
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        intersect: false,
        mode: 'index'
      },
      scales: {
        y: {
          beginAtZero: true,
          max: 100,
          grid: { color: '#30363d' },
          ticks: { 
            color: '#8b949e',
            font: { size: 10 }
          }
        },
        x: {
          grid: { color: '#30363d' },
          ticks: { 
            color: '#8b949e',
            font: { size: 10 },
            maxTicksLimit: 6
          }
        }
      },
      plugins: {
        legend: {
          labels: { 
            color: '#f0f6fc',
            font: { size: 10 }
          }
        }
      }
    }
  });
  
  // Update performance data every 5 seconds
  setInterval(updatePerformanceData, 5000);
}

// Utility functions
function toggleSidebar() {
  const sidebar = document.getElementById('sidebar');
  if (sidebar) {
    sidebar.classList.toggle('collapsed');
    
    // Resize terminal after sidebar toggle
    setTimeout(() => {
      if (terminal && terminal.loadedAddons && terminal.loadedAddons.find(addon => addon.instance.fit)) {
        terminal.loadedAddons.find(addon => addon.instance.fit).instance.fit();
      }
    }, 300);
  }
}

function toggleCommandPalette() {
  const palette = document.getElementById('commandPalette');
  const input = document.getElementById('commandInput');
  
  if (palette) {
    palette.classList.toggle('show');
    if (palette.classList.contains('show') && input) {
      input.focus();
      input.value = '';
      updateCommandPaletteResults('');
    }
  }
}

function handleCommandPaletteInput(e) {
  const query = e.target.value;
  updateCommandPaletteResults(query);
}

function handleCommandPaletteKeydown(e) {
  if (e.key === 'Enter') {
    const query = e.target.value.trim();
    if (query && socket) {
      socket.emit('command', query);
      commandHistory.push(query);
      historyIndex = commandHistory.length;
      saveCommandHistory();
      toggleCommandPalette();
      terminal.focus();
    }
  } else if (e.key === 'Escape') {
    toggleCommandPalette();
    terminal.focus();
  }
}

function updateCommandPaletteResults(query) {
  const results = document.getElementById('commandResults');
  if (!results) return;
  
  const commands = [
    { cmd: 'ls -la', desc: 'List all files with details' },
    { cmd: 'pwd', desc: 'Show current directory' },
    { cmd: 'ps aux', desc: 'Show running processes' },
    { cmd: 'df -h', desc: 'Show disk usage' },
    { cmd: 'top -n 1', desc: 'Show system processes' },
    { cmd: 'cbash status', desc: 'Show CBash system status' },
    { cmd: 'cbash history', desc: 'Show command history' },
    { cmd: 'clear', desc: 'Clear terminal screen' },
    { cmd: 'whoami', desc: 'Show current user' },
    { cmd: 'date', desc: 'Show current date and time' }
  ];
  
  const filtered = query ? 
    commands.filter(c => c.cmd.toLowerCase().includes(query.toLowerCase()) || 
                         c.desc.toLowerCase().includes(query.toLowerCase())) :
    commands.slice(0, 5);
  
  results.innerHTML = filtered.map(c => 
    `<div class="command-item" onclick="executeFromPalette('${c.cmd}')">
      <span class="command-name">${c.cmd}</span>
      <span class="command-description">${c.desc}</span>
    </div>`
  ).join('');
}

function executeFromPalette(cmd) {
  if (socket) {
    socket.emit('command', cmd);
    commandHistory.push(cmd);
    historyIndex = commandHistory.length;
    saveCommandHistory();
    toggleCommandPalette();
    terminal.focus();
  }
}

function cycleTheme() {
  const themeOrder = ['dark', 'light', 'hacker'];
  const currentIndex = themeOrder.indexOf(currentTheme);
  const nextIndex = (currentIndex + 1) % themeOrder.length;
  setTheme(themeOrder[nextIndex]);
}

function setTheme(theme) {
  if (!themes[theme]) return;
  
  currentTheme = theme;
  if (terminal) {
    terminal.setOption('theme', themes[theme]);
  }
  
  localStorage.setItem('cbash-theme', theme);
  
  // Update theme indicators
  document.querySelectorAll('.theme-option').forEach(option => {
    option.classList.toggle('active', option.getAttribute('data-theme') === theme);
  });
  
  // Update CSS custom properties for theme
  const root = document.documentElement;
  if (theme === 'light') {
    root.style.setProperty('--primary-bg', '#ffffff');
    root.style.setProperty('--secondary-bg', '#f6f8fa');
    root.style.setProperty('--text-primary', '#24292f');
    root.style.setProperty('--text-secondary', '#656d76');
  } else if (theme === 'hacker') {
    root.style.setProperty('--primary-bg', '#000000');
    root.style.setProperty('--secondary-bg', '#001100');
    root.style.setProperty('--text-primary', '#00ff00');
    root.style.setProperty('--text-secondary', '#007700');
  } else {
    // Default dark theme
    root.style.setProperty('--primary-bg', '#0d1117');
    root.style.setProperty('--secondary-bg', '#161b22');
    root.style.setProperty('--text-primary', '#f0f6fc');
    root.style.setProperty('--text-secondary', '#8b949e');
  }
}

function updateConnectionStatus(status) {
  const indicator = document.getElementById('statusIndicator');
  const statusText = document.getElementById('connectionStatus');
  
  if (indicator) {
    indicator.className = `status-indicator ${status}`;
  }
  if (statusText) {
    statusText.textContent = status === 'connected' ? 'Connected' : 'Disconnected';
  }
}

function showNotification(message, type = 'info', duration = 3000) {
  const notifications = document.getElementById('notifications');
  if (!notifications) return;
  
  const notification = document.createElement('div');
  notification.className = `notification ${type}`;
  notification.textContent = message;
  
  notifications.appendChild(notification);
  
  setTimeout(() => {
    notification.style.animation = 'slideOut 0.3s ease forwards';
    setTimeout(() => {
      if (notifications.contains(notification)) {
        notifications.removeChild(notification);
      }
    }, 300);
  }, duration);
}

function updateSessionStats() {
  const sessionCountEl = document.getElementById('sessionCount');
  if (sessionCountEl) {
    sessionCountEl.textContent = sessionStats.commandCount;
  }
}

function updateExecutionStats(executionTime, command) {
  if (executionTime > 2) {
    showNotification(`⚠️ Command "${command}" took ${executionTime}s`, 'warning');
  }
}

function startStatsUpdater() {
  setInterval(() => {
    const uptime = Math.floor((Date.now() - sessionStats.startTime) / 1000);
    const uptimeEl = document.getElementById('uptime');
    if (uptimeEl) {
      uptimeEl.textContent = formatUptime(uptime);
    }
  }, 1000);
}

function formatUptime(seconds) {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;
  
  if (hours > 0) {
    return `${hours}h ${minutes}m`;
  } else if (minutes > 0) {
    return `${minutes}m ${secs}s`;
  } else {
    return `${secs}s`;
  }
}

function updatePerformanceData() {
  fetch('/api/system-info')
    .then(response => response.json())
    .then(data => {
      // Update stats display
      const elements = {
        cpuUsage: document.getElementById('cpuUsage'),
        memoryUsage: document.getElementById('memoryUsage'),
        diskUsage: document.getElementById('diskUsage')
      };
      
      if (elements.cpuUsage) elements.cpuUsage.textContent = `${Math.round(data.cpu_percent)}%`;
      if (elements.memoryUsage) elements.memoryUsage.textContent = `${Math.round(data.memory_percent)}%`;
      if (elements.diskUsage) elements.diskUsage.textContent = `${Math.round(data.disk_percent)}%`;
      
      // Update chart
      if (window.performanceChart) {
        const chart = window.performanceChart;
        const now = new Date().toLocaleTimeString('en-US', { 
          hour12: false, 
          hour: '2-digit', 
          minute: '2-digit' 
        });
        
        chart.data.labels.push(now);
        chart.data.datasets[0].data.push(data.cpu_percent);
        chart.data.datasets[1].data.push(data.memory_percent);
        
        // Keep only last 20 data points
        if (chart.data.labels.length > 20) {
          chart.data.labels.shift();
          chart.data.datasets[0].data.shift();
          chart.data.datasets[1].data.shift();
        }
        
        chart.update('none');
      }
    })
    .catch(error => {
      console.error('Failed to fetch system info:', error);
    });
}

function setupKeyboardShortcuts() {
  document.addEventListener('keydown', (e) => {
    // Ctrl+Shift+P - Command Palette
    if (e.ctrlKey && e.shiftKey && e.key === 'P') {
      e.preventDefault();
      toggleCommandPalette();
    }
    
    // Ctrl+` - Toggle Sidebar
    if (e.ctrlKey && e.key === '`') {
      e.preventDefault();
      toggleSidebar();
    }
    
    // Ctrl+Shift+T - Cycle Theme
    if (e.ctrlKey && e.shiftKey && e.key === 'T') {
      e.preventDefault();
      cycleTheme();
    }
    
    // Escape - Close modals
    if (e.key === 'Escape') {
      const commandPalette = document.getElementById('commandPalette');
      if (commandPalette && commandPalette.classList.contains('show')) {
        commandPalette.classList.remove('show');
        if (terminal) terminal.focus();
      }
    }
  });
  
  // Focus terminal when clicking on terminal area
  document.addEventListener('click', (e) => {
    if (e.target.closest('.terminal-wrapper') && terminal) {
      terminal.focus();
    }
  });
}

function saveCommandHistory() {
  try {
    localStorage.setItem('cbash-command-history', JSON.stringify(commandHistory.slice(-100)));
  } catch (e) {
    console.warn('Failed to save command history:', e);
  }
}

function loadCommandHistory() {
  try {
    const saved = localStorage.getItem('cbash-command-history');
    if (saved) {
      commandHistory = JSON.parse(saved);
      historyIndex = commandHistory.length;
    }
  } catch (e) {
    console.warn('Failed to load command history:', e);
  }
}

function loadSavedSettings() {
  // Load theme
  const savedTheme = localStorage.getItem('cbash-theme') || 'dark';
  setTheme(savedTheme);
  
  // Load command history
  loadCommandHistory();
}

// CSS injection for dynamic styling
function injectDynamicStyles() {
  const style = document.createElement('style');
  style.textContent = `
    @keyframes slideOut {
      to {
        transform: translateX(100%);
        opacity: 0;
      }
    }
    
    .btn {
      background: var(--secondary-bg);
      border: 1px solid var(--border-color);
      color: var(--text-primary);
      padding: 0.5rem 1rem;
      border-radius: 4px;
      cursor: pointer;
      font-size: 0.875rem;
      transition: all 0.2s ease;
    }
    
    .btn:hover {
      background: var(--primary-bg);
      border-color: var(--accent-color);
    }
    
    .btn-icon {
      padding: 0.5rem;
      font-size: 1rem;
    }
    
    .btn-sm {
      padding: 0.25rem 0.5rem;
      font-size: 0.75rem;
    }
    
    .btn-xs {
      padding: 0.125rem 0.25rem;
      font-size: 0.625rem;
    }
    
    .quick-cmd-btn {
      display: block;
      width: 100%;
      text-align: left;
      background: var(--primary-bg);
      border: 1px solid var(--border-color);
      color: var(--text-primary);
      padding: 0.5rem;
      margin-bottom: 0.25rem;
      border-radius: 4px;
      cursor: pointer;
      font-size: 0.75rem;
      transition: all 0.2s ease;
    }
    
    .quick-cmd-btn:hover {
      background: var(--secondary-bg);
      border-color: var(--accent-color);
    }
    
    .stat-row {
      display: flex;
      justify-content: space-between;
      margin-bottom: 0.25rem;
      font-size: 0.75rem;
    }
    
    .command-item {
      padding: 0.5rem;
      border-bottom: 1px solid var(--border-color);
      cursor: pointer;
      transition: background 0.2s ease;
    }
    
    .command-item:hover {
      background: var(--primary-bg);
    }
    
    .command-name {
      font-weight: 600;
      color: var(--accent-color);
    }
    
    .command-description {
      display: block;
      font-size: 0.75rem;
      color: var(--text-secondary);
      margin-top: 0.25rem;
    }
  `;
  document.head.appendChild(style);
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  injectDynamicStyles();
  initializeApp();
});

// Export for global access
window.CBash = {
  setTheme,
  toggleSidebar,
  toggleCommandPalette,
  showNotification,
  executeFromPalette
};
