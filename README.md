# Maverick — Autonomous Execution & OS Control (v0.5) 🧠🎙️💾🛠️💻

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![LLM Provider](https://img.shields.io/badge/LLM-Google%20Gemini%20%2B%20Groq-orange.svg)](https://aistudio.google.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**Maverick** is a personalized autonomous AI assistant software engineering project. Level 5 empowers Maverick with **Autonomous Execution & OS Control**—enabling local file operations, terminal command execution, launching desktop applications, capturing screenshots, and real-time hardware monitoring.

---

## 🎯 Current Version
**Maverick v0.5 — Autonomous Execution & OS Control**
* Status: **COMPLETE**

---

## 🗺️ Roadmap

- [x] **Level 1**: Core Brain (CLI Chat, Session Context, Config & Multi-LLM Error Handling)
- [x] **Level 2**: Voice Interface (Speech-to-Text & Text-to-Speech)
- [x] **Level 3**: Personal Memory & Persistence (SQLite Database, Background Fact Extraction, Persistent Context Injection)
- [x] **Level 4**: Tool Integration & Web Research (Web Search, Web Reader, Calculator, Weather, System Info)
- [x] **Level 5**: Autonomous Execution & OS Control (File I/O, Command Execution, App Launcher, Screenshots, System Metrics)

---

## ✨ Features (v0.5)

* 💻 **Local OS & Desktop Control (`app/os_control.py`)**:
  - `create_file`: Creates/writes text and code files to disk.
  - `read_file`: Reads text content from local files.
  - `list_dir`: Lists directory files and folders.
  - `execute_cmd`: Runs local terminal and PowerShell commands safely.
  - `open_app_or_url`: Launches desktop apps (e.g. `notepad`, `calc`) or web URLs in default browser.
  - `take_screenshot`: Captures desktop screen as PNG.
  - `get_system_status`: Monitors real-time CPU usage, RAM utilization, and disk storage space.
* 🌐 **Live Web Search & Research**: Real-time web search (`search_web`), URL fetcher (`fetch_url`), calculator (`calculate`), weather (`get_weather`).
* 🎙️ **Voice Interface**: Speech-to-Text (`/listen`) and Text-to-Speech (`/voice`).
* 💾 **SQLite Memory Engine**: Fact extraction and persistent long-term memory (`/memory`, `/remember`, `/forget`).
* ⚡ **Multi-LLM Failover**: Google Gemini Primary with instant fallback to Groq API on rate-limiting.

---

## 📁 Project Structure

```text
SELF-AI/
│
├── app/
│   ├── __init__.py      # Package marker
│   ├── config.py        # Configuration, .env handling & system prompts
│   ├── ai.py            # LLM Brain, Groq failover, Memory & Tool execution loop
│   ├── memory.py        # Level 3 SQLite persistent memory storage engine
│   ├── tools.py         # Tool Registry & tool dispatch engine
│   ├── os_control.py    # Level 5 OS Control Engine (File I/O, Commands, Screenshots, Metrics)
│   ├── voice.py         # Level 2 Voice Engine (STT & TTS)
│   └── main.py          # Interactive CLI application loop & command router
│
├── data/
│   ├── memory.db        # Persistent SQLite database storage
│   └── screenshots/     # Saved desktop screenshots
│
├── .env.example         # Environment variables template
├── .env                 # Private API credentials (git-ignored)
├── .gitignore            # Git exclusion rules
├── requirements.txt     # Python dependencies
├── README.md            # Project documentation
└── LICENSE              # MIT License
```

---

## 🏃 Running Maverick

Start the application using Python:

```powershell
python -m app.main
```

### CLI Commands:
- `/tools`: View all 12+ active external and OS control tools.
- `/memory`: View stored long-term memories.
- `/remember <fact>`: Store a new fact into persistent memory.
- `/forget <id/key>`: Remove a memory entry.
- `/voice`: Toggle spoken audio responses on/off.
- `/listen`: Speak into your microphone.
- `/history`: Inspect active session context.
- `/clear`: Reset short-term conversation context.
- `exit` / `quit`: Shut down Maverick.

---

## 📜 License

Distributed under the MIT License. See `LICENSE` for details.
