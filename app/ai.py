"""
app/ai.py
---------
Responsible for communicating with LLM API providers (Google Gemini & Groq Backup).
Abstracts multi-provider complexity, integrates Level 3 Persistent Memory, and
drives Level 4 Tool Execution (Web Research, Calculator, Weather, System Info).

Resilience features:
  - Immediate failover: If Gemini fails (429 rate limit or 404), switches to Groq backup instantly.
  - Groq model auto-discovery: Queries available models dynamically if default model returns 404.
  - Level 4 Tool Loop: Automatically detects and executes tool calls ([TOOL: ...]), feeding output back to the LLM.
"""

import time
import re
from typing import List, Dict, Any, Optional
from google import genai
from google.genai import types
from app.config import Config
from app.memory import MemoryEngine
from app.tools import ToolRegistry

# Safe dynamic import for Groq SDK
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

# Preferred Groq models in priority order (fallback list if configured model is invalid)
GROQ_MODEL_FALLBACKS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "qwen-2.5-32b",
    "deepseek-r1-distill-llama-70b",
    "llama3-70b-8192",
    "llama3-8b-8192",
    "mixtral-8x7b-32768",
    "gemma2-9b-it",
]


class LLMBrain:
    """
    LLMBrain manages interactions with Primary (Google Gemini) and Fallback (Groq) LLMs.
    Provides seamless multi-provider failover, Level 3 Persistent Memory, and Level 4 Tool Execution.
    """

    def __init__(self):
        """Initialize LLM clients, Persistent Memory, and Level 4 Tool Registry."""
        Config.validate()

        # Level 3: Initialize Persistent Memory Engine
        self.memory = MemoryEngine()

        # Level 4: Initialize Tool Registry Engine
        self.tools = ToolRegistry()

        # Primary LLM: Google Gemini
        self.client = genai.Client(api_key=Config.get_api_key())
        self.model_name = Config.get_model_name()

        # Create initial chat session with combined system prompt + memories + tools
        self._init_chat_session()

        # Backup LLM: Groq API
        self.groq_client = None
        self.groq_model = Config.get_groq_model_name()
        groq_key = Config.get_groq_api_key()

        if GROQ_AVAILABLE and groq_key:
            try:
                self.groq_client = Groq(api_key=groq_key)
                self.has_groq_backup = True
                # Auto-discover a valid Groq model at startup
                self._resolve_groq_model()
            except Exception as e:
                print(f"[System Warning] Could not initialize Groq backup client: {e}")
                self.has_groq_backup = False
        else:
            self.has_groq_backup = False

    def _resolve_groq_model(self) -> None:
        """
        Validates the configured Groq model. If set to 'auto' or if the configured model
        is not available, queries the Groq API for active models and picks the best one.
        """
        if not self.groq_client:
            return

        configured = self.groq_model.strip().lower()

        # If not 'auto', assume the user knows what they want
        if configured != "auto":
            return

        # Auto-discover: query Groq API for available models
        try:
            available_models = self.groq_client.models.list()
            available_ids = {m.id for m in available_models.data}

            # Pick the first preferred model that exists on Groq
            for candidate in GROQ_MODEL_FALLBACKS:
                if candidate in available_ids:
                    self.groq_model = candidate
                    print(f"[System] Auto-detected Groq model: {candidate}")
                    return

            # If none of our preferred models match, pick the first valid text-chat model
            excluded_keywords = ["whisper", "guard", "orpheus", "arabic", "canopy", "audio", "embed", "bge", "tts", "stt", "allam"]
            for m in available_models.data:
                m_id_lower = m.id.lower()
                if not any(kw in m_id_lower for kw in excluded_keywords):
                    self.groq_model = m.id
                    print(f"[System] Auto-detected Groq model: {m.id}")
                    return

        except Exception as e:
            print(f"[System Warning] Could not auto-detect Groq model: {e}")

        # Final fallback
        self.groq_model = "llama-3.3-70b-versatile"

    def _build_system_instruction(self, user_query: Optional[str] = None) -> str:
        """
        Combines base system prompt, Level 3 Persistent Memory context,
        and Level 4 Tool Registry instructions.
        """
        base_prompt = Config.get_system_prompt()
        memory_context = self.memory.format_memories_for_prompt(user_query)
        tools_snippet = self.tools.get_system_prompt_snippet()

        parts = [base_prompt]
        if memory_context:
            parts.append(memory_context)
        parts.append(tools_snippet)

        return "\n\n".join(parts)

    def _init_chat_session(self, user_query: Optional[str] = None) -> None:
        """Initializes or refreshes the Gemini chat session with updated system instructions."""
        system_instruction = self._build_system_instruction(user_query)
        self.config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.7,
        )
        self.chat = self.client.chats.create(
            model=self.model_name,
            config=self.config
        )

    def _extract_and_save_facts(self, text: str) -> bool:
        """
        Scans user input for explicit personal statements and saves them to long-term memory.
        Returns True if a new memory item was saved.
        """
        added = False
        clean_text = text.strip()

        # Rule 1: Explicit "remember that <fact>" / "remember this: <fact>" / "remember <fact>"
        rem_match = re.search(r"\bremember (?:that|this[:\s]*)?\s*(.+)", clean_text, re.IGNORECASE)
        if rem_match:
            raw_fact = rem_match.group(1).strip()
            # Clean trailing text like ". remember this in your memory"
            raw_fact = re.sub(r"[\.\s]*(?:remember|save)\s+(?:this|that).*", "", raw_fact, flags=re.IGNORECASE).strip()
            if raw_fact:
                raw_fact_lower = raw_fact.lower()
                if "student" in raw_fact_lower or "study" in raw_fact_lower or "bca" in raw_fact_lower or "lpu" in raw_fact_lower or "university" in raw_fact_lower:
                    key = "Education & Role"
                elif "name" in raw_fact_lower:
                    key = "User Name"
                elif "live" in raw_fact_lower or "from" in raw_fact_lower:
                    key = "Location"
                else:
                    key = "Personal Fact"
                self.memory.add_memory(key=key, value=raw_fact, category="personal")
                added = True

        # Rule 2: "I am a/an <Role/Student/...>"
        role_match = re.search(r"\bi am (?:a|an) ([A-Za-z0-9_\- ]+(?:student|developer|engineer|coder|analyst|programmer)[A-Za-z0-9_\- ]*)\b", clean_text, re.IGNORECASE)
        if role_match:
            self.memory.add_memory(key="Education & Role", value=role_match.group(1).strip(), category="personal")
            added = True

        # Rule 3: "My name is <Name>"
        name_match = re.search(r"\bmy name is ([A-Za-z0-9_\- ]+)\b", clean_text, re.IGNORECASE)
        if name_match:
            self.memory.add_memory(key="User Name", value=name_match.group(1).strip().title(), category="personal")
            added = True

        # Rule 4: "I live in <Location>" / "I am from <Location>"
        loc_match = re.search(r"\bi (?:live in|am from|reside in) ([A-Za-z0-9_\- ,]+)\b", clean_text, re.IGNORECASE)
        if loc_match:
            self.memory.add_memory(key="Location", value=loc_match.group(1).strip().title(), category="personal")
            added = True

        # Rule 5: "My favorite <Item> is <Value>"
        fav_match = re.search(r"\bmy favorite ([A-Za-z0-9_\- ]+) is ([A-Za-z0-9_\- ]+)\b", clean_text, re.IGNORECASE)
        if fav_match:
            item_name = fav_match.group(1).strip().title()
            item_val = fav_match.group(2).strip()
            self.memory.add_memory(key=f"Favorite {item_name}", value=item_val, category="preference")
            added = True

        # Rule 6: "I work as a <Role>"
        work_match = re.search(r"\bi work as (?:a|an) ([A-Za-z0-9_\- ]+)\b", clean_text, re.IGNORECASE)
        if work_match:
            self.memory.add_memory(key="Occupation", value=work_match.group(1).strip().title(), category="personal")
            added = True

        return added

    def _send_to_groq(self, prompt: str) -> str:
        """
        Sends message to Groq backup with automatic model fallback.
        """
        if not self.groq_client:
            raise RuntimeError("Groq backup client is not configured or unavailable.")

        system_prompt = self._build_system_instruction(prompt)
        messages = [{"role": "system", "content": system_prompt}]

        # Append existing conversation history for context continuity
        raw_history = self.get_history()
        for msg in raw_history:
            role = "assistant" if msg["role"].lower() in ["model", "assistant"] else "user"
            messages.append({"role": role, "content": msg["text"]})

        messages.append({"role": "user", "content": prompt})

        models_to_try = [self.groq_model]
        for fallback in GROQ_MODEL_FALLBACKS:
            if fallback not in models_to_try:
                models_to_try.append(fallback)

        last_err = None
        for model_id in models_to_try:
            try:
                print(f"\n[⚡ Failover] Trying Groq model: {model_id}...")
                completion = self.groq_client.chat.completions.create(
                    model=model_id,
                    messages=messages,
                    temperature=0.7,
                )
                if model_id != self.groq_model:
                    print(f"[System] Groq model updated to: {model_id}")
                    self.groq_model = model_id
                return completion.choices[0].message.content
            except Exception as e:
                last_err = e
                err_str = str(e)
                if "404" in err_str or "model_not_found" in err_str or "does not exist" in err_str:
                    continue
                else:
                    raise

        raise RuntimeError(f"All Groq models failed. Last error: {last_err}")

    def _raw_send(self, prompt: str) -> str:
        """Sends a single prompt payload to Gemini Primary or Groq Backup."""
        primary_err_msg = "Unknown error"
        try:
            response = self.chat.send_message(prompt)
            return response.text
        except Exception as primary_err:
            primary_err_msg = str(primary_err)

        if self.has_groq_backup:
            try:
                return self._send_to_groq(prompt)
            except Exception as groq_err:
                raise RuntimeError(
                    f"Gemini: {self._short_error(primary_err_msg)}\n"
                    f"Groq: {self._short_error(str(groq_err))}"
                )

        raise RuntimeError(f"Gemini failed: {self._short_error(primary_err_msg)}")

    def send_message(self, user_message: str) -> str:
        """
        Sends user message to LLM, detects tool calls, executes tools in a loop,
        and returns the final synthesized natural response.
        """
        # Auto-extract personal details in background
        facts_added = self._extract_and_save_facts(user_message)
        if facts_added:
            self._init_chat_session()

        current_prompt = user_message
        max_tool_iterations = 3

        for _ in range(max_tool_iterations):
            # Step 1: Query LLM
            response_text = self._raw_send(current_prompt)

            # Step 2: Check for tool calls
            tool_calls = self.tools.parse_tool_calls(response_text)

            if not tool_calls:
                # No tool call needed — return final LLM answer
                return response_text

            # Step 3: Tool Call Detected -> Execute tool(s)
            tool_results = []
            for tool_name, kwargs in tool_calls:
                print(f"\n[Tool Execution 🛠️] Running {tool_name}({kwargs})...")
                res = self.tools.execute_tool(tool_name, kwargs)
                if tool_name == "save_memory":
                    self._init_chat_session()
                tool_results.append(f"[TOOL OUTPUT: {tool_name}]\n{res}")

            # Step 4: Feed tool results back to LLM for final output
            combined_tool_output = "\n\n".join(tool_results)
            current_prompt = (
                f"Tool execution results:\n{combined_tool_output}\n\n"
                "Please synthesize these results into a clear, direct answer for the user."
            )

        # Fallback if max iterations exceeded
        return response_text

    @staticmethod
    def _short_error(err_str: str) -> str:
        """Extracts a short, user-friendly error message from raw API error strings."""
        msg_match = re.search(r"'message':\s*'([^']+)'", err_str)
        if msg_match:
            msg = msg_match.group(1)
            if len(msg) > 150:
                return msg[:150] + "..."
            return msg
        if len(err_str) > 200:
            return err_str[:200] + "..."
        return err_str

    def reset(self) -> None:
        """Resets active chat session context while preserving long-term memory."""
        self._init_chat_session()

    def get_history(self) -> List[Dict[str, Any]]:
        """Retrieves session conversation history."""
        raw_history = self.chat.get_history()
        formatted_history = []
        for message in raw_history:
            parts_text = " ".join([part.text for part in message.parts if part.text])
            formatted_history.append({
                "role": message.role,
                "text": parts_text
            })
        return formatted_history
