<div align="center">

# 🖥️ CBash - Web-Based Unix Terminal

[![GitHub Stars](https://img.shields.io/github/stars/SohaFarhana05/CBash?style=for-the-badge&logo=github&color=yellow)](https://github.com/SohaFarhana05/CBash/stargazers)
[![GitHub Forks](https://img.shields.io/github/forks/SohaFarhana05/CBash?style=for-the-badge&logo=github&color=blue)](https://github.com/SohaFarhana05/CBash/network)
[![GitHub Issues](https://img.shields.io/github/issues/SohaFarhana05/CBash?style=for-the-badge&logo=github&color=red)](https://github.com/SohaFarhana05/CBash/issues)
[![GitHub License](https://img.shields.io/github/license/SohaFarhana05/CBash?style=for-the-badge&color=green)](https://github.com/SohaFarhana05/CBash/blob/main/LICENSE)

<!-- Visitor Analytics -->
![Visitor Count](https://komarev.com/ghpvc/?username=SohaFarhana05&repo=CBash&label=Repository%20views&color=0e75b6&style=for-the-badge)
![Hits](https://hits.seeyoufarm.com/api/count/incr/badge.svg?url=https%3A%2F%2Fgithub.com%2FSohaFarhana05%2FCBash&count_bg=%23007EC6&title_bg=%23555555&icon=terminal.svg&icon_color=%23E7E7E7&title=Project+Views&edge_flat=false)

<p align="center">
  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white" alt="Flask" />
  <img src="https://img.shields.io/badge/Socket.IO-010101?style=for-the-badge&logo=socketdotio&logoColor=white" alt="Socket.IO" />
  <img src="https://img.shields.io/badge/C-A8B9CC?style=for-the-badge&logo=c&logoColor=black" alt="C" />
  <img src="https://img.shields.io/badge/JavaScript-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black" alt="JavaScript" />
</p>

*A full-featured web-based Unix terminal with real-time command execution*

[🚀 Live Demo](https://gitpod.io/#https://github.com/SohaFarhana05/CBash) • [📖 Documentation](#documentation) • [🐛 Report Bug](https://github.com/SohaFarhana05/CBash/issues) • [✨ Request Feature](https://github.com/SohaFarhana05/CBash/issues)

</div>

---

## 🌟 Overview

CBash is a sophisticated web-based Unix terminal that brings the power of command-line interface to your browser. Built with Flask and Socket.IO for real-time communication, it features a custom C shell implementation that provides an authentic Unix experience with modern web technologies.

### ✨ Key Features

- 🖥️ **Interactive Terminal**: Full terminal experience in your browser
- ⚡ **Real-time Communication**: WebSocket-based command execution
- 🛠️ **Custom Shell**: Built with C for authentic Unix experience  
- 🎨 **Modern UI**: Clean terminal interface powered by xterm.js
- 📚 **Command History**: Navigate through previous commands with arrow keys
- 🔄 **Live Updates**: Real-time output display with proper formatting
- 🌐 **Cloud Ready**: Deployable on Gitpod, Heroku, and other platforms

### 🎯 Supported Commands

| Category | Commands |
|----------|----------|
| **File Operations** | `ls`, `cat`, `touch`, `rm`, `cp`, `mv` |
| **Directory Navigation** | `cd`, `pwd`, `mkdir`, `rmdir` |
| **Text Processing** | `grep`, `sort`, `head`, `tail`, `wc` |
| **System Info** | `date`, `whoami`, `uname`, `ps` |
| **Utilities** | `clear`, `history`, `echo`, `which` |

## 🚀 Quick Start

### Option 1: Gitpod (Recommended)
Click the button below to launch a ready-to-use development environment:

[![Open in Gitpod](https://gitpod.io/button/open-in-gitpod.svg)](https://gitpod.io/#https://github.com/SohaFarhana05/CBash)

### Option 2: Local Development

```bash
# Clone the repository
git clone https://github.com/SohaFarhana05/CBash.git
cd CBash

# Install dependencies
pip install -r requirements.txt

# Compile the C shell
gcc -o mysh main.c

# Run the application
python server.py
```

Visit `http://localhost:8000` to access the terminal.

## 🏗️ Architecture

```
CBash/
├── 🖥️ server.py           # Flask application with Socket.IO
├── 🔧 main.c              # Custom C shell implementation  
├── 📁 templates/
│   └── 🎨 index.html      # Frontend terminal interface
├── 📋 requirements.txt    # Python dependencies
├── ⚙️ .gitpod.yml         # Gitpod configuration
└── 🚀 Procfile           # Deployment configuration
```

## 🛠️ Technologies

<div align="center">

| Backend | Frontend | Shell | Deployment |
|---------|----------|-------|------------|
| ![Python](https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white) | ![HTML5](https://img.shields.io/badge/HTML5-E34F26?style=flat&logo=html5&logoColor=white) | ![C](https://img.shields.io/badge/C-A8B9CC?style=flat&logo=c&logoColor=black) | ![Gitpod](https://img.shields.io/badge/Gitpod-FFAE33?style=flat&logo=gitpod&logoColor=black) |
| ![Flask](https://img.shields.io/badge/Flask-000000?style=flat&logo=flask&logoColor=white) | ![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=flat&logo=javascript&logoColor=black) | ![Linux](https://img.shields.io/badge/Linux-FCC624?style=flat&logo=linux&logoColor=black) | ![Heroku](https://img.shields.io/badge/Heroku-430098?style=flat&logo=heroku&logoColor=white) |
| ![Socket.IO](https://img.shields.io/badge/Socket.IO-010101?style=flat&logo=socketdotio&logoColor=white) | ![xterm.js](https://img.shields.io/badge/xterm.js-000000?style=flat&logo=terminal&logoColor=white) | | ![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat&logo=docker&logoColor=white) |

</div>

## 📊 Project Analytics

<div align="center">

### 📈 Repository Statistics
![GitHub repo size](https://img.shields.io/github/repo-size/SohaFarhana05/CBash?style=for-the-badge&color=blue)
![GitHub code size](https://img.shields.io/github/languages/code-size/SohaFarhana05/CBash?style=for-the-badge&color=green)
![GitHub last commit](https://img.shields.io/github/last-commit/SohaFarhana05/CBash?style=for-the-badge&color=orange)


</div>

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.


---

<div align="center">

**⭐ Star this repository if you found it helpful!**

*Built with ❤️ and lots of ☕*

</div>
