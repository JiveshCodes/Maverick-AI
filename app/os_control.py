"""
app/os_control.py
-----------------
Level 5 Autonomous Execution & OS Control Engine for Maverick AI.
Provides local desktop automation capabilities:
  - File I/O: create_file, read_file, list_dir
  - Terminal Execution: execute_cmd
  - App Launcher: open_app_or_url
  - Screen Capture: take_screenshot
  - Hardware Metrics: get_system_status
"""

import os
import sys
import subprocess
import datetime
import platform
import shutil
import webbrowser
from pathlib import Path
from typing import Dict, Any, Optional

from app.config import Config

# Safe dynamic import for Pillow (ImageGrab screenshot)
try:
    from PIL import ImageGrab
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# Safe dynamic import for psutil (system memory & CPU metrics)
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


def create_file(filepath: str, content: str) -> str:
    """
    Creates or overwrites a local file on disk with specified text/code content.
    """
    clean_path_str = filepath.strip().strip("'\"")
    if not clean_path_str:
        return "[OS Error] Filepath cannot be empty."

    try:
        path = Path(clean_path_str)
        if not path.is_absolute():
            path = Config.BASE_DIR / path

        # Create parent directories if needed
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

        size = path.stat().st_size
        return f"[OS Control 💻] Successfully created file: {path} ({size} bytes)"
    except Exception as e:
        return f"[OS Error] Could not create file '{clean_path_str}': {e}"


def read_file(filepath: str) -> str:
    """
    Reads text content from a local file on disk.
    """
    clean_path_str = filepath.strip().strip("'\"")
    if not clean_path_str:
        return "[OS Error] Filepath cannot be empty."

    try:
        path = Path(clean_path_str)
        if not path.is_absolute():
            path = Config.BASE_DIR / path

        if not path.exists():
            return f"[OS Error] File does not exist: {path}"

        if not path.is_file():
            return f"[OS Error] Path is a directory, not a file: {path}"

        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read(3000)

        if len(content) == 3000:
            return content + "\n... [File Content Truncated at 3000 chars]"
        return content if content else "[File is empty]"
    except Exception as e:
        return f"[OS Error] Could not read file '{clean_path_str}': {e}"


def list_dir(dirpath: str = ".") -> str:
    """
    Lists files and directories inside a target folder path.
    """
    clean_dir = dirpath.strip().strip("'\"") or "."
    try:
        path = Path(clean_dir)
        if not path.is_absolute():
            path = Config.BASE_DIR / path

        if not path.exists():
            return f"[OS Error] Directory does not exist: {path}"

        items = list(path.iterdir())
        if not items:
            return f"[OS Control 💻] Directory '{path}' is empty."

        formatted = [f"Contents of {path}:"]
        for item in sorted(items, key=lambda x: (not x.is_dir(), x.name.lower())):
            if item.is_dir():
                formatted.append(f" 📁 [DIR]  {item.name}/")
            else:
                size = item.stat().st_size
                formatted.append(f" 📄 [FILE] {item.name} ({size} bytes)")

        return "\n".join(formatted)
    except Exception as e:
        return f"[OS Error] Could not list directory '{clean_dir}': {e}"


def execute_cmd(command: str) -> str:
    """
    Executes a terminal/PowerShell command locally and returns standard output and errors.
    """
    clean_cmd = command.strip().strip("'\"")
    if not clean_cmd:
        return "[OS Error] Command cannot be empty."

    try:
        # Run using powershell on Windows, or default shell on Unix
        shell_cmd = ["powershell", "-Command", clean_cmd] if sys.platform == "win32" else clean_cmd
        res = subprocess.run(
            shell_cmd,
            shell=True if sys.platform != "win32" else False,
            capture_output=True,
            text=True,
            timeout=15,
            cwd=str(Config.BASE_DIR),
        )

        stdout = res.stdout.strip()
        stderr = res.stderr.strip()

        output_parts = []
        if stdout:
            output_parts.append(f"STDOUT:\n{stdout}")
        if stderr:
            output_parts.append(f"STDERR:\n{stderr}")

        result_text = "\n".join(output_parts) if output_parts else "Command executed cleanly with no output."

        if res.returncode != 0:
            return f"[OS Command Exit Code {res.returncode}]\n{result_text}"
        return f"[OS Control 💻] Executed: '{clean_cmd}'\n{result_text}"

    except subprocess.TimeoutExpired:
        return f"[OS Error] Command '{clean_cmd}' timed out after 15 seconds."
    except Exception as e:
        return f"[OS Error] Could not execute command '{clean_cmd}': {e}"


def open_app_or_url(target: str) -> str:
    """
    Launches a local desktop application (e.g. 'notepad', 'calc') or opens a web URL in the browser.
    """
    clean_target = target.strip().strip("'\"")
    if not clean_target:
        return "[OS Error] Target application or URL cannot be empty."

    try:
        # Check if URL
        if clean_target.startswith(("http://", "https://", "www.")):
            url = clean_target if clean_target.startswith("http") else "https://" + clean_target
            webbrowser.open(url)
            return f"[OS Control 💻] Opened web URL in browser: {url}"

        # Otherwise launch app on Windows
        if sys.platform == "win32":
            try:
                os.startfile(clean_target)
            except Exception:
                subprocess.Popen(clean_target, shell=True)
            return f"[OS Control 💻] Launched application: '{clean_target}'"
        else:
            subprocess.Popen([clean_target])
            return f"[OS Control 💻] Launched application: '{clean_target}'"

    except Exception as e:
        return f"[OS Error] Could not open target '{clean_target}': {e}"


def take_screenshot(filename: str = "") -> str:
    """
    Captures current desktop screen and saves image to disk.
    """
    if not PIL_AVAILABLE:
        return "[OS Error] Screenshot capability requires 'Pillow'. Run 'pip install pillow'."

    try:
        screenshot_dir = Config.get_data_dir() / "screenshots"
        screenshot_dir.mkdir(parents=True, exist_ok=True)

        name = filename.strip().strip("'\"")
        if not name:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            name = f"screenshot_{timestamp}.png"

        if not name.endswith(".png"):
            name += ".png"

        save_path = screenshot_dir / name
        image = ImageGrab.grab()
        image.save(save_path)

        width, height = image.size
        return f"[OS Control 📸] Screenshot captured ({width}x{height} px): {save_path}"
    except Exception as e:
        return f"[OS Error] Failed to take screenshot: {e}"


def get_system_status() -> str:
    """
    Returns current hardware metrics: CPU usage %, Memory RAM utilization, and Disk space.
    """
    lines = ["--- 💻 SYSTEM HARDWARE STATUS ---"]

    # CPU & RAM via psutil
    if PSUTIL_AVAILABLE:
        try:
            cpu_percent = psutil.cpu_percent(interval=0.5)
            cpu_count = psutil.cpu_count(logical=True)
            mem = psutil.virtual_memory()

            lines.append(f"CPU Usage: {cpu_percent}% ({cpu_count} logical cores)")
            lines.append(f"RAM Memory: {mem.percent}% used ({mem.used / (1024**3):.2f} GB / {mem.total / (1024**3):.2f} GB)")
        except Exception as e:
            lines.append(f"CPU/RAM error: {e}")

    # Disk Space via shutil
    try:
        disk = shutil.disk_usage(str(Config.BASE_DIR))
        disk_used_gb = disk.used / (1024**3)
        disk_total_gb = disk.total / (1024**3)
        disk_free_gb = disk.free / (1024**3)
        disk_pct = (disk.used / disk.total) * 100

        lines.append(f"Disk Storage: {disk_pct:.1f}% used ({disk_used_gb:.2f} GB used / {disk_free_gb:.2f} GB free of {disk_total_gb:.2f} GB)")
    except Exception as e:
        lines.append(f"Disk error: {e}")

    lines.append(f"OS Platform: {platform.system()} {platform.release()} ({platform.machine()})")
    lines.append("--------------------------------")

    return "\n".join(lines)
