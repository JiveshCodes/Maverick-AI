"""
app/tools.py
------------
Defines the tool execution engine for Level 4 (Tool Integration & Web Research).
Provides standard tools (Web Search, Web Fetch, Calculator, Weather, System Info)
and a ToolRegistry for dynamic tool discovery, execution, and system prompt formatting.
"""

import os
import re
import ast
import json
import math
import datetime
import platform
import urllib.request
import urllib.parse
from typing import Callable, Dict, Any, List, Optional, Tuple


class Tool:
    """Represents an executable tool that Maverick can invoke."""

    def __init__(
        self,
        name: str,
        description: str,
        parameters: Dict[str, str],
        func: Callable[..., str],
    ):
        self.name = name
        self.description = description
        self.parameters = parameters  # param_name -> description
        self.func = func

    def execute(self, **kwargs) -> str:
        """Executes the tool with provided keyword arguments."""
        try:
            return str(self.func(**kwargs))
        except Exception as e:
            return f"[Tool Error] {self.name} failed: {e}"


# --- Tool Implementations ---


def search_web(query: str) -> str:
    """
    Performs a live web search using DuckDuckGo (API or HTML scraper fallback).
    Requires no API keys.
    """
    clean_query = query.strip().strip("'\"")
    if not clean_query:
        return "[Search Error] Query cannot be empty."

    # Method 1: Try duckduckgo_search library if available
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(clean_query, max_results=4))
            if results:
                formatted = []
                for i, r in enumerate(results, 1):
                    formatted.append(f"{i}. [{r.get('title', 'No Title')}]({r.get('href', '#')})\n   {r.get('body', '')}")
                return "\n\n".join(formatted)
    except Exception:
        pass  # Fall through to HTML scraping fallback

    # Method 2: Fallback HTML scraper via urllib
    try:
        encoded_query = urllib.parse.quote_plus(clean_query)
        url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            },
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            html = resp.read().decode("utf-8", errors="ignore")

        # Extract title and snippet elements
        snippets = re.findall(r'<a class="result__snippet[^"]*"[^>]*>(.*?)</a>', html, re.DOTALL)
        titles = re.findall(r'<a class="result__url[^"]*"[^>]*>(.*?)</a>', html, re.DOTALL)

        if not snippets:
            # Fallback regex for titles & snippets
            snippets = re.findall(r'class="result__snippet">(.*?)</span>', html, re.DOTALL)

        if snippets:
            results_str = []
            for i, snippet in enumerate(snippets[:4], 1):
                clean_snippet = re.sub(r"<[^>]+>", "", snippet).strip()
                title_str = re.sub(r"<[^>]+>", "", titles[i - 1]).strip() if i - 1 < len(titles) else "Result"
                results_str.append(f"{i}. {title_str}\n   {clean_snippet}")
            return "\n\n".join(results_str)

        return f"No detailed search results found for '{clean_query}'."
    except Exception as e:
        return f"[Search Error] Web search request failed: {e}"


def fetch_url(url: str) -> str:
    """
    Downloads webpage content from a URL and extracts clean readable text.
    """
    clean_url = url.strip().strip("'\"")
    if not clean_url.startswith(("http://", "https://")):
        clean_url = "https://" + clean_url

    try:
        req = urllib.request.Request(
            clean_url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            },
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            content_type = resp.headers.get("Content-Type", "")
            raw_bytes = resp.read(100000)  # Limit to ~100KB
            text = raw_bytes.decode("utf-8", errors="ignore")

        # Strip HTML script and style tags
        text = re.sub(r"<script.*?>.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<style.*?>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
        # Strip all HTML tags
        clean_text = re.sub(r"<[^>]+>", " ", text)
        # Normalize whitespace
        clean_text = re.sub(r"\s+", " ", clean_text).strip()

        # Limit return length to 2500 characters
        if len(clean_text) > 2500:
            return clean_text[:2500] + "... [Content Truncated]"
        return clean_text if clean_text else "Page downloaded but contained no readable text."
    except Exception as e:
        return f"[Fetch Error] Could not retrieve URL {clean_url}: {e}"


def calculate(expression: str) -> str:
    """
    Evaluates mathematical expressions safely using Python AST and math module.
    """
    clean_expr = expression.strip().strip("'\"")
    if not clean_expr:
        return "[Calc Error] Expression is empty."

    # Allowed AST nodes for safe math evaluation
    allowed_nodes = (
        ast.Expression,
        ast.BinOp,
        ast.UnaryOp,
        ast.Constant,
        ast.Num,
        ast.Add,
        ast.Sub,
        ast.Mult,
        ast.Div,
        ast.FloorDiv,
        ast.Mod,
        ast.Pow,
        ast.USub,
        ast.UAdd,
        ast.Call,
        ast.Name,
        ast.Load,
    )

    allowed_names = {
        "abs": abs,
        "round": round,
        "min": min,
        "max": max,
        "sum": sum,
        "pow": math.pow,
        "sqrt": math.sqrt,
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        "pi": math.pi,
        "e": math.e,
        "log": math.log,
        "log10": math.log10,
        "ceil": math.ceil,
        "floor": math.floor,
        "factorial": math.factorial,
    }

    try:
        parsed = ast.parse(clean_expr, mode="eval")

        for node in ast.walk(parsed):
            if not isinstance(node, allowed_nodes):
                return f"[Calc Error] Unsupported or unsafe operation: {type(node).__name__}"
            if isinstance(node, ast.Name) and node.id not in allowed_names:
                return f"[Calc Error] Unknown variable/function: {node.id}"

        # Evaluate code safely with restricted globals/locals
        result = eval(compile(parsed, "<string>", "eval"), {"__builtins__": {}}, allowed_names)
        return f"{clean_expr} = {result}"
    except Exception as e:
        return f"[Calc Error] Invalid expression '{clean_expr}': {e}"


def get_weather(city: str) -> str:
    """
    Fetches live weather summary for a specified city using wttr.in format.
    """
    clean_city = city.strip().strip("'\"")
    if not clean_city:
        return "[Weather Error] City name required."

    try:
        encoded_city = urllib.parse.quote(clean_city)
        # Use wttr.in simple text format 3 (e.g., "London: ⛅️ +15°C ↙12km/h")
        url = f"https://wttr.in/{encoded_city}?format=3"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "curl/7.68.0"},
        )
        with urllib.request.urlopen(req, timeout=6) as resp:
            text = resp.read().decode("utf-8", errors="ignore").strip()
            if text and "Unknown location" not in text and "404" not in text:
                return f"Live Weather for {text}"
            
        # Fallback format if format=3 fails
        url2 = f"https://wttr.in/{encoded_city}?format=%C+%t+%w+%h"
        req2 = urllib.request.Request(url2, headers={"User-Agent": "curl/7.68.0"})
        with urllib.request.urlopen(req2, timeout=6) as resp2:
            text2 = resp2.read().decode("utf-8", errors="ignore").strip()
            if text2:
                return f"Live Weather in {clean_city}: {text2}"

        return f"Could not find weather data for '{clean_city}'."
    except Exception as e:
        return f"[Weather Error] Weather fetch failed for {clean_city}: {e}"


def get_system_info() -> str:
    """
    Returns current local date, time, operating system, and Python version details.
    """
    now = datetime.datetime.now()
    date_str = now.strftime("%A, %B %d, %Y")
    time_str = now.strftime("%I:%M:%S %p")
    sys_name = platform.system()
    sys_rel = platform.release()
    py_ver = platform.python_version()

    return (
        f"Current Date: {date_str}\n"
        f"Current Time: {time_str}\n"
        f"OS Platform: {sys_name} {sys_rel}\n"
        f"Python Version: {py_ver}"
    )


def save_memory(key: str, value: str) -> str:
    """
    Saves a fact, preference, or detail about the user into long-term persistent memory.
    """
    clean_key = key.strip().strip("'\"").title()
    clean_val = value.strip().strip("'\"")
    if not clean_key or not clean_val:
        return "[Memory Error] Key and value cannot be empty."

    try:
        from app.memory import MemoryEngine
        mem = MemoryEngine()
        mem.add_memory(key=clean_key, value=clean_val, category="user_fact")
        return f"[Memory Saved 💾] Saved to long-term memory: '{clean_key}: {clean_val}'"
    except Exception as e:
        return f"[Memory Error] Could not save memory: {e}"


# --- Tool Registry ---


class ToolRegistry:
    """
    Manages registration, discovery, formatting, and execution of tools.
    """

    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        self._register_default_tools()

    def _register_default_tools(self) -> None:
        """Registers default built-in tools for Maverick Level 4."""
        self.register(
            Tool(
                name="search_web",
                description="Performs a live web search for current events, news, or general knowledge.",
                parameters={"query": "The search query string"},
                func=search_web,
            )
        )
        self.register(
            Tool(
                name="fetch_url",
                description="Fetches and extracts plain text content from a specified webpage URL.",
                parameters={"url": "The full HTTP/HTTPS web URL to download"},
                func=fetch_url,
            )
        )
        self.register(
            Tool(
                name="calculate",
                description="Evaluates math expressions (e.g. '2**10', 'sqrt(144)', 'cos(pi/4)').",
                parameters={"expression": "The mathematical expression string"},
                func=calculate,
            )
        )
        self.register(
            Tool(
                name="get_weather",
                description="Retrieves live current weather report for a given city or location.",
                parameters={"city": "City or location name (e.g. 'New York', 'Tokyo')"},
                func=get_weather,
            )
        )
        self.register(
            Tool(
                name="get_system_info",
                description="Returns current system date, time, operating system, and runtime details.",
                parameters={},
                func=get_system_info,
            )
        )
        self.register(
            Tool(
                name="save_memory",
                description="Saves a new fact, preference, or detail about the user into persistent long-term memory.",
                parameters={"key": "Short descriptive topic (e.g. 'Education', 'Role', 'Hobby')", "value": "The fact to remember"},
                func=save_memory,
            )
        )

        # --- Level 5 OS Control Tools ---
        try:
            from app.os_control import (
                create_file,
                read_file,
                list_dir,
                execute_cmd,
                open_app_or_url,
                take_screenshot,
                get_system_status,
            )
            self.register(
                Tool(
                    name="create_file",
                    description="Creates or overwrites a local file with specified text/code content.",
                    parameters={"filepath": "File path (relative or absolute)", "content": "File content string"},
                    func=create_file,
                )
            )
            self.register(
                Tool(
                    name="read_file",
                    description="Reads text content from a local file on disk.",
                    parameters={"filepath": "Path to the file to read"},
                    func=read_file,
                )
            )
            self.register(
                Tool(
                    name="list_dir",
                    description="Lists files and subdirectories inside a specified folder.",
                    parameters={"dirpath": "Directory folder path (default '.')"},
                    func=list_dir,
                )
            )
            self.register(
                Tool(
                    name="execute_cmd",
                    description="Executes a local terminal or PowerShell command safely and returns output.",
                    parameters={"command": "The terminal command line string to run"},
                    func=execute_cmd,
                )
            )
            self.register(
                Tool(
                    name="open_app_or_url",
                    description="Launches a desktop application (e.g. 'notepad', 'calc') or opens a URL in the web browser.",
                    parameters={"target": "App name (e.g. 'notepad', 'calc') or web URL"},
                    func=open_app_or_url,
                )
            )
            self.register(
                Tool(
                    name="take_screenshot",
                    description="Captures current desktop screen and saves PNG image file to disk.",
                    parameters={"filename": "Optional filename for saved image (e.g. 'desktop.png')"},
                    func=take_screenshot,
                )
            )
            self.register(
                Tool(
                    name="get_system_status",
                    description="Queries real-time hardware status: CPU usage, RAM memory, disk storage, and OS version.",
                    parameters={},
                    func=get_system_status,
                )
            )
        except Exception as e:
            print(f"[System Warning] Could not register OS control tools: {e}")

    def register(self, tool: Tool) -> None:
        """Registers a new tool in the registry."""
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> Optional[Tool]:
        """Returns tool by name or None."""
        return self._tools.get(name)

    def list_tools(self) -> List[Dict[str, Any]]:
        """Returns list of all registered tool metadata dicts."""
        result = []
        for tool in self._tools.values():
            result.append(
                {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                }
            )
        return result

    def get_count(self) -> int:
        """Returns the total number of registered tools."""
        return len(self._tools)

    def execute_tool(self, name: str, kwargs: Dict[str, Any]) -> str:
        """Executes a tool by name with given kwargs."""
        tool = self.get_tool(name)
        if not tool:
            return f"[Registry Error] Tool '{name}' is not registered."
        return tool.execute(**kwargs)

    def get_system_prompt_snippet(self) -> str:
        """
        Generates system prompt instructions detailing available tools and invocation syntax.
        """
        lines = [
            "\n--- EXTERNAL TOOLS AVAILABLE ---",
            "You have access to real-time external tools. Use them when you need current info, calculations, weather, system time, or web content.",
            "To execute a tool, write a tool call command on its own line using this exact format:",
            '  [TOOL: tool_name(param1="value1", param2="value2")]',
            "",
            "Available tools:",
        ]

        for tool in self._tools.values():
            params_str = ", ".join([f'{k}="<{v}>"' for k, v in tool.parameters.items()])
            lines.append(f"- {tool.name}({params_str}): {tool.description}")

        lines.extend([
            "",
            "RULES FOR TOOLS:",
            "1. Only call tools when necessary to answer the user accurately.",
            "2. Output the [TOOL: ...] block immediately when you need tool data.",
            "3. Do not fake or invent search/weather results — use the tools!",
            "--------------------------------\n",
        ])

        return "\n".join(lines)

    @staticmethod
    def parse_tool_calls(text: str) -> List[Tuple[str, Dict[str, Any]]]:
        """
        Parses text for tool call tags like:
          [TOOL: search_web(query="Python 3.12")]
          [TOOL: calculate(expression="100 * 5")]
          [TOOL: get_weather(city="London")]
          [TOOL: get_system_info()]

        Returns a list of (tool_name, kwargs_dict) tuples.
        """
        calls = []
        # Pattern: [TOOL: name(args)]
        matches = re.findall(r"\[TOOL:\s*([a-zA-Z0-9_]+)\((.*?)\)\]", text, re.DOTALL)

        for name, args_raw in matches:
            args_str = args_raw.strip()
            kwargs = {}

            if not args_str:
                calls.append((name, kwargs))
                continue

            # Case A: JSON object string like `{"query": "foo"}`
            if args_str.startswith("{") and args_str.endswith("}"):
                try:
                    kwargs = json.loads(args_str)
                    calls.append((name, kwargs))
                    continue
                except json.JSONDecodeError:
                    pass

            # Case B: Key=Value pairs like `query="Python 3.12", limit=5`
            kv_matches = re.findall(
                r'([a-zA-Z0-9_]+)\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^\s,]+))', args_str
            )
            if kv_matches:
                for key, val1, val2, val3 in kv_matches:
                    val = val1 or val2 or val3
                    kwargs[key] = val
                calls.append((name, kwargs))
                continue

            # Case C: Single raw argument string without key=
            clean_val = args_str.strip("'\"")
            if name == "search_web":
                kwargs = {"query": clean_val}
            elif name == "fetch_url":
                kwargs = {"url": clean_val}
            elif name == "calculate":
                kwargs = {"expression": clean_val}
            elif name == "get_weather":
                kwargs = {"city": clean_val}
            elif name == "open_app_or_url":
                kwargs = {"target": clean_val}
            elif name == "execute_cmd":
                kwargs = {"command": clean_val}
            elif name == "list_dir":
                kwargs = {"dirpath": clean_val}
            elif name == "read_file":
                kwargs = {"filepath": clean_val}
            elif name == "take_screenshot":
                kwargs = {"filename": clean_val}
            else:
                kwargs = {"arg": clean_val}

            calls.append((name, kwargs))

        return calls
